#!/usr/bin/env python3
"""Deterministic write path for sessions/ledger.yaml.

The ONLY sanctioned way to mutate a session ledger. Hand-editing is blocked by
a PreToolUse hook (ledger-write-guard.sh). Every mutation is:
  - serialized by an flock sidecar lock (no lost updates),
  - round-tripped through ruamel.yaml (node edits, preserved formatting, no
    fragile text splicing, duplicate keys rejected on load),
  - journaled (a pre-image snapshot before every write),
  - schema-validated and re-parsed before the atomic os.replace.

Design: ~/.claude/plans/ledger-helper-design.md (v2, post-Codex review).

Exit codes: 0 ok · 2 usage · 65 data/schema error · 70 internal · 75 lock/conflict.
"""
import sys, os, re, json, time, errno, fcntl, argparse, shutil, io
from datetime import datetime, timezone

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.constructor import DuplicateKeyError
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
except ImportError:
    sys.stderr.write("FATAL: ruamel.yaml not installed (python3 -m pip install --user ruamel.yaml)\n")
    sys.exit(70)

EX_USAGE, EX_DATA, EX_INTERNAL, EX_LOCK = 2, 65, 70, 75

ORG_LEDGERS = {
    'klever':    '/Users/gabrielamyot/Developer/grp-beklever-com/project-management/sessions/ledger.yaml',
    'supervisr': '/Users/gabrielamyot/Developer/supervisr-ai/project-management/sessions/ledger.yaml',
    'personal':  '/Users/gabrielamyot/Developer/gabriel-amyot/project-management/sessions/ledger.yaml',
}
SECTIONS = ('sessions', 'handoffs')
KEYFIELD = {'sessions': 'slug', 'handoffs': 'file'}
HANDOFF_STATUS = {'awaiting_initiation', 'initiated', 'completed', 'abandoned', 'close_report'}
SESSION_STATUS = {'active', 'paused', 'closed', 'abandoned'}
LOCK_TIMEOUT_S = 15
JOURNAL_KEEP = 50


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def die(code, msg):
    sys.stderr.write(f"ledger: {msg}\n")
    sys.exit(code)


def _repr_none(representer, data):
    # render None as the literal `null`, not an empty value (keeps diffs clean)
    return representer.represent_scalar('tag:yaml.org,2002:null', 'null')


def make_yaml():
    y = YAML(typ='rt')
    y.preserve_quotes = True
    y.allow_duplicate_keys = False
    y.width = 100000          # never line-wrap long note: values
    y.indent(mapping=2, sequence=4, offset=2)
    y.representer.add_representer(type(None), _repr_none)
    return y


def resolve_path(args):
    if getattr(args, 'org', None):
        if args.org not in ORG_LEDGERS:
            die(EX_USAGE, f"unknown org '{args.org}' (known: {', '.join(ORG_LEDGERS)})")
        return ORG_LEDGERS[args.org]
    if getattr(args, 'ledger', None):
        return os.path.abspath(args.ledger)      # tests / explicit paths only
    die(EX_USAGE, "one of --org or --ledger is required")


# ---------- locking ----------
class Lock:
    def __init__(self, ledger_path):
        self.lock_path = os.path.join(os.path.dirname(ledger_path), '.ledger.lock')
        self.fd = None

    def __enter__(self):
        self.fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.time() + LOCK_TIMEOUT_S
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as e:
                if e.errno not in (errno.EAGAIN, errno.EACCES):
                    raise
                if time.time() >= deadline:
                    os.close(self.fd)
                    die(EX_LOCK, "ledger is busy (lock held by another writer) — retry")
                time.sleep(0.15)

    def __exit__(self, *a):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)


# ---------- journal ----------
def journal(ledger_path, op):
    if not os.path.exists(ledger_path):
        return
    jdir = os.path.join(os.path.dirname(ledger_path), '.ledger-journal')
    os.makedirs(jdir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f')
    shutil.copy2(ledger_path, os.path.join(jdir, f"{ts}-{op}.yaml"))
    snaps = sorted(f for f in os.listdir(jdir) if f.endswith('.yaml'))
    for old in snaps[:-JOURNAL_KEEP]:
        try:
            os.remove(os.path.join(jdir, old))
        except OSError:
            pass


# ---------- load / validate / write ----------
def load(ledger_path):
    y = make_yaml()
    try:
        with open(ledger_path) as f:
            doc = y.load(f)
    except DuplicateKeyError as e:
        die(EX_DATA, f"ledger has a duplicate key (run `ledger validate`): {str(e).splitlines()[0]}")
    except Exception as e:  # ruamel ScannerError/ParserError etc.
        die(EX_DATA, f"ledger does not parse as YAML (corrupt — run `ledger normalize`): {str(e).splitlines()[0]}")
    if doc is None:
        die(EX_DATA, "ledger is empty/unparseable")
    return y, doc


def validate_doc(doc, structural_only=False):
    """Return list of '[sev] msg'. Structural = corruption invariants that BLOCK writes
    (identity keys, no duplicates, correct section, parseable shape). Advisory = soft
    signals reported by `validate` but NOT blocking (status vocabulary is open across
    orgs: shelved, superseded, close_report, ...). structural_only filters to blockers."""
    problems = []
    def struct(m): problems.append(f"[structural] {m}")
    def advise(m): problems.append(f"[advisory] {m}")
    if not isinstance(doc, dict) or 'version' not in doc:
        struct("missing header 'version'")
    for sec in SECTIONS:
        if sec not in doc or not isinstance(doc.get(sec), list):
            struct(f"section '{sec}' missing or not a list"); continue
        kf = KEYFIELD[sec]
        seen = set()
        for i, e in enumerate(doc[sec]):
            if not isinstance(e, dict):
                struct(f"{sec}[{i}] is not a mapping"); continue
            if kf not in e:
                struct(f"{sec}[{i}] missing identity key '{kf}'"); continue
            if e.get('slug' if sec == 'handoffs' else 'file'):
                struct(f"{sec}[{i}] ({e[kf]}) has wrong-section key")
            k = e[kf]
            if k in seen:
                struct(f"{sec} duplicate {kf}: {k}")
            seen.add(k)
            st = e.get('status')
            valid = SESSION_STATUS if sec == 'sessions' else HANDOFF_STATUS
            if st is not None and st not in valid:
                advise(f"{sec} {k}: uncommon status '{st}'")
    if structural_only:
        return [p for p in problems if p.startswith('[structural]')]
    return problems


def atomic_write(y, doc, ledger_path):
    buf = io.StringIO()
    y.dump(doc, buf)
    text = buf.getvalue()
    # re-parse strict before committing — never write something that won't load
    verify = make_yaml()
    try:
        verify.load(text)
    except Exception as e:
        die(EX_INTERNAL, f"refusing to write: dump did not re-parse cleanly: {e}")
    tmp = ledger_path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ledger_path)


def bump_header(doc):
    doc['version'] = int(doc.get('version', 0)) + 1
    doc['modified'] = now_iso()


def commit(y, doc, ledger_path, op, baseline):
    """Block only on problems this mutation INTRODUCES; tolerate pre-existing debt."""
    post = validate_doc(doc, structural_only=True)
    introduced = [p for p in post if p not in baseline]
    if introduced:
        die(EX_DATA, "mutation would introduce schema problems:\n  - " + "\n  - ".join(introduced))
    journal(ledger_path, op)
    atomic_write(y, doc, ledger_path)


def operationalize_gate(ledger_path, slug):
    """Port of session-close-operationalize-guard.sh: a session may not be marked
    closed/abandoned until /operationalize stamped this session's manifest recently.
    The old hook fired on Edit/Write; helper writes bypass it, so the gate lives here.
    FAILS OPEN on any uncertainty (missing manifest, parse error) — never wedge a close."""
    from datetime import datetime, timezone
    pm_root = os.path.dirname(os.path.dirname(os.path.abspath(ledger_path)))
    if os.path.exists(os.path.join(pm_root, 'sessions', '.operationalize-skip')):
        return
    manifest = os.path.join(pm_root, 'sessions', 'active', slug, 'knowledge-manifest.yaml')
    if not os.path.exists(manifest):
        return  # retroactive/legacy close — nothing to gate against; allow
    window = int(os.environ.get('OPERATIONALIZE_GATE_WINDOW_MIN', '15'))
    try:
        y = YAML(typ='safe')
        with open(manifest) as f:
            m = y.load(f) or {}
        last = m.get('last_run')
    except Exception:
        return  # fail open on manifest parse error
    if not last:
        die(EX_DATA, "operationalize gate: /operationalize has not run this session "
                     "(manifest last_run is null). Capture before closing, or create "
                     "sessions/.operationalize-skip.")
    try:
        dt = datetime.fromisoformat(str(last).replace('Z', '+00:00'))
        age = (datetime.now(timezone.utc) - dt).total_seconds() / 60
    except Exception:
        return  # fail open on unparseable timestamp
    if age > window:
        die(EX_DATA, f"operationalize gate: last capture was {int(age)}m ago (> {window}m). "
                     "Re-run /operationalize before closing, or create sessions/.operationalize-skip.")


def _closes_session(section, status_value):
    return section == 'sessions' and status_value in ('closed', 'abandoned')


def coerce(v):
    if v == 'null':
        return None
    if v in ('true', 'false'):
        return v == 'true'
    if re.fullmatch(r'-?\d+', v):
        return int(v)
    return v


def find_entry(doc, section, key):
    kf = KEYFIELD[section]
    for e in doc.get(section, []):
        if isinstance(e, dict) and e.get(kf) == key:
            return e
    return None


def find_all(doc, section, key):
    """Every entry matching key, as (index, entry). Only `rekey` needs this — the
    other commands act on the first match, which is why a duplicate identity key is
    unreachable until it has been renamed."""
    kf = KEYFIELD[section]
    return [(i, e) for i, e in enumerate(doc.get(section, []))
            if isinstance(e, dict) and e.get(kf) == key]


def to_commented_map(d):
    m = CommentedMap()
    for k, v in d.items():
        if isinstance(v, list):
            s = CommentedSeq(); s.extend(v); m[k] = s
        else:
            m[k] = v
    return m


# ---------- subcommands ----------
def cmd_bootstrap(args):
    path = resolve_path(args)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with Lock(path):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            die(EX_DATA, "ledger already exists — bootstrap refuses to overwrite")
        doc = CommentedMap()
        doc['version'] = 1
        doc['modified'] = now_iso()
        doc['created'] = now_iso()
        doc['sessions'] = CommentedSeq()
        doc['handoffs'] = CommentedSeq()
        y = make_yaml()
        buf = io.StringIO(); y.dump(doc, buf)
        os.write(fd, buf.getvalue().encode()); os.close(fd)
    print(f"bootstrapped {path}")


def cmd_append(args):
    path = resolve_path(args)
    entry = json.loads(args.json)
    kf = KEYFIELD[args.section]
    if kf not in entry:
        die(EX_USAGE, f"append to {args.section} requires '{kf}' in --json")
    with Lock(path):
        y, doc = load(path)
        baseline = validate_doc(doc, structural_only=True)
        if find_entry(doc, args.section, entry[kf]):
            die(EX_DATA, f"{args.section} already has {kf}={entry[kf]} (use update)")
        if _closes_session(args.section, entry.get('status')):
            operationalize_gate(path, entry.get('slug'))
        pos = args.position or ('top' if args.section == 'sessions' else 'bottom')
        seq = doc[args.section]
        if pos == 'top':
            seq.insert(0, to_commented_map(entry))
        else:
            seq.append(to_commented_map(entry))
        bump_header(doc)
        commit(y, doc, path, f"append-{args.section}", baseline)
    print(f"appended {kf}={entry[kf]} to {args.section} ({pos})")


def _apply_update(entry, sets, appends, removes, section):
    kf = KEYFIELD[section]
    for pair in sets or []:
        k, _, v = pair.partition('=')
        if k == kf:
            die(EX_DATA, f"cannot change immutable identity key '{kf}' via update")
        entry[k] = coerce(v)
    for pair in appends or []:
        k, _, v = pair.partition('=')
        if k not in entry or entry[k] is None:
            entry[k] = CommentedSeq()
        if not isinstance(entry[k], list):
            die(EX_DATA, f"--append-list target '{k}' is not a list")
        entry[k].append(coerce(v))
    for k in removes or []:
        if k == kf:
            die(EX_DATA, f"cannot remove identity key '{kf}'")
        entry.pop(k, None)


def cmd_update(args):
    path = resolve_path(args)
    with Lock(path):
        y, doc = load(path)
        baseline = validate_doc(doc, structural_only=True)
        entry = find_entry(doc, args.section, args.key)
        if entry is None:
            die(EX_DATA, f"{args.section} has no {KEYFIELD[args.section]}={args.key}")
        for pair in (args.set or []):
            k, _, v = pair.partition('=')
            if k == 'status' and _closes_session(args.section, coerce(v)):
                operationalize_gate(path, args.key)
        _apply_update(entry, args.set, args.append_list, args.remove, args.section)
        if 'version' in entry and args.section == 'handoffs' and not args.no_entry_bump:
            try:
                entry['version'] = int(entry['version']) + 1
            except (TypeError, ValueError):
                pass
        bump_header(doc)
        commit(y, doc, path, f"update-{args.section}", baseline)
    print(f"updated {args.section} {args.key}")


def cmd_claim(args):
    """Locked CAS transition for autopilot/pickup: assert status before claiming."""
    path = resolve_path(args)
    with Lock(path):
        y, doc = load(path)
        baseline = validate_doc(doc, structural_only=True)
        entry = find_entry(doc, 'handoffs', args.key)
        if entry is None:
            die(EX_DATA, f"handoffs has no file={args.key}")
        if entry.get('status') != args.expect_status:
            die(EX_LOCK, f"claim conflict: {args.key} is '{entry.get('status')}', expected '{args.expect_status}'")
        if args.expect_version is not None and int(entry.get('version', -1)) != args.expect_version:
            die(EX_LOCK, f"claim conflict: {args.key} version {entry.get('version')} != {args.expect_version}")
        _apply_update(entry, args.set, None, None, 'handoffs')
        if 'version' in entry:
            entry['version'] = int(entry['version']) + 1
        bump_header(doc)
        commit(y, doc, path, "claim", baseline)
    print(f"claimed {args.key}")


def cmd_batch(args):
    """Multiple entry ops, ONE header bump (pickup/autopilot triage)."""
    path = resolve_path(args)
    ops = json.loads(args.ops)
    with Lock(path):
        y, doc = load(path)
        baseline = validate_doc(doc, structural_only=True)
        for op in ops:
            sec = op['section']; action = op['op']
            if action == 'append':
                e = op['entry']; kf = KEYFIELD[sec]
                if find_entry(doc, sec, e[kf]):
                    die(EX_DATA, f"batch append: {sec} already has {kf}={e[kf]}")
                (doc[sec].insert(0, to_commented_map(e)) if op.get('position', 'top') == 'top'
                 else doc[sec].append(to_commented_map(e)))
            elif action == 'update':
                entry = find_entry(doc, sec, op['key'])
                if entry is None:
                    die(EX_DATA, f"batch update: {sec} has no {KEYFIELD[sec]}={op['key']}")
                for pair in (op.get('set') or []):
                    k, _, v = pair.partition('=')
                    if k == 'status' and _closes_session(sec, coerce(v)):
                        operationalize_gate(path, op['key'])
                _apply_update(entry, op.get('set'), op.get('append_list'), op.get('remove'), sec)
            else:
                die(EX_USAGE, f"batch: unknown op '{action}'")
        bump_header(doc)
        commit(y, doc, path, "batch", baseline)
    print(f"batch applied {len(ops)} ops")


def cmd_rekey(args):
    """Rename an identity key. The ONLY command allowed to touch it.

    `update` refuses identity-key changes on purpose: a slug/file rename during a
    normal status write is always a mistake. Deduplicating a ledger is the one
    legitimate case, so it gets its own explicit verb. A duplicate key is otherwise
    unfixable — find_entry returns the first match, so the second is unreachable."""
    path = resolve_path(args)
    kf = KEYFIELD[args.section]
    with Lock(path):
        y, doc = load(path)
        baseline = validate_doc(doc, structural_only=True)
        matches = find_all(doc, args.section, args.old)
        if not matches:
            die(EX_DATA, f"{args.section} has no {kf}={args.old}")
        if find_all(doc, args.section, args.new):
            die(EX_DATA, f"{args.section} already has {kf}={args.new} — pick another name")
        if len(matches) > 1 and args.occurrence is None:
            lines = [f"  --occurrence {n}: index {i} "
                     f"status={e.get('status')} created={e.get('created')} closed={e.get('closed')}"
                     for n, (i, e) in enumerate(matches, 1)]
            die(EX_USAGE, f"{kf}={args.old} matches {len(matches)} entries — "
                          "pass --occurrence to pick one:\n" + "\n".join(lines))
        n = args.occurrence or 1
        if not 1 <= n <= len(matches):
            die(EX_USAGE, f"--occurrence {n} out of range (1..{len(matches)})")
        idx, entry = matches[n - 1]
        entry[kf] = args.new
        bump_header(doc)
        commit(y, doc, path, f"rekey-{args.section}", baseline)
    print(f"rekeyed {args.section}[{idx}] {kf}: {args.old} -> {args.new}")


def cmd_get(args):
    path = resolve_path(args)
    _, doc = load(path)
    entry = find_entry(doc, args.section, args.key)
    if entry is None:
        die(EX_DATA, f"{args.section} has no {KEYFIELD[args.section]}={args.key}")
    y = make_yaml(); y.dump(entry, sys.stdout)


def cmd_validate(args):
    path = resolve_path(args)
    try:
        _, doc = load(path)
    except SystemExit:
        raise
    problems = validate_doc(doc)
    structural = [p for p in problems if p.startswith('[structural]')]
    advisory = [p for p in problems if p.startswith('[advisory]')]
    for p in problems:
        print(f"  - {p}")
    if structural:
        print(f"INVALID — {len(structural)} structural problem(s)"
              + (f", {len(advisory)} advisory" if advisory else ""))
        print("  Pre-existing debt does NOT block writes: commit() blocks only problems a "
              "mutation INTRODUCES. Fix duplicate identity keys with `rekey`.")
        sys.exit(EX_DATA)
    if advisory:
        print(f"OK (structural) with {len(advisory)} advisory note(s) — "
              f"sessions: {len(doc['sessions'])} · handoffs: {len(doc['handoffs'])} · version {doc.get('version')}")
        return
    print(f"VALID — sessions: {len(doc['sessions'])} · handoffs: {len(doc['handoffs'])} · version {doc.get('version')}")


def main():
    p = argparse.ArgumentParser(prog='ledger', description='Deterministic session-ledger writer')
    p.add_argument('--org', choices=list(ORG_LEDGERS))
    p.add_argument('--ledger', help='explicit path (tests only; prefer --org)')
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('bootstrap')

    ap = sub.add_parser('append')
    ap.add_argument('--section', required=True, choices=SECTIONS)
    ap.add_argument('--json', required=True)
    ap.add_argument('--position', choices=('top', 'bottom'))

    up = sub.add_parser('update')
    up.add_argument('--section', required=True, choices=SECTIONS)
    up.add_argument('--key', required=True)
    up.add_argument('--set', action='append', metavar='k=v')
    up.add_argument('--append-list', action='append', metavar='k=v')
    up.add_argument('--remove', action='append', metavar='k')
    up.add_argument('--no-entry-bump', action='store_true')

    cl = sub.add_parser('claim')
    cl.add_argument('--key', required=True)
    cl.add_argument('--expect-status', default='awaiting_initiation')
    cl.add_argument('--expect-version', type=int)
    cl.add_argument('--set', action='append', metavar='k=v', required=True)

    ba = sub.add_parser('batch')
    ba.add_argument('--ops', required=True, help='JSON array of ops')

    rk = sub.add_parser('rekey')
    rk.add_argument('--section', required=True, choices=SECTIONS)
    rk.add_argument('--old', required=True)
    rk.add_argument('--new', required=True)
    rk.add_argument('--occurrence', type=int, help='1-based, in document order (required when --old is duplicated)')

    g = sub.add_parser('get')
    g.add_argument('--section', required=True, choices=SECTIONS)
    g.add_argument('--key', required=True)

    sub.add_parser('validate')

    args = p.parse_args()
    fn = {
        'bootstrap': cmd_bootstrap, 'append': cmd_append, 'update': cmd_update,
        'claim': cmd_claim, 'batch': cmd_batch, 'rekey': cmd_rekey,
        'get': cmd_get, 'validate': cmd_validate,
    }[args.cmd]
    fn(args)


if __name__ == '__main__':
    main()

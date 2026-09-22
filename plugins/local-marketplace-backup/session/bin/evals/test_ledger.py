#!/usr/bin/env python3
"""Eval suite for ledger.py — proves the safety-critical behaviors.

Run: python3 test_ledger.py   (exit 0 = all pass)
"""
import sys, os, subprocess, tempfile, shutil, io, json

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(os.path.dirname(HERE), 'ledger.py')
sys.path.insert(0, os.path.dirname(HERE))
import ledger  # noqa

REAL = '/Users/gabrielamyot/Developer/grp-beklever-com/project-management/sessions/ledger.yaml'
PASS, FAIL = 0, 0


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {name}")
    else:
        FAIL += 1; print(f"  FAIL  {name}  {detail}")


def run(*args, path):
    return subprocess.run([sys.executable, BIN, '--ledger', path, *args],
                          capture_output=True, text=True)


def canonicalize(src, dst):
    y, doc = ledger.load(src)
    buf = io.StringIO(); y.dump(doc, buf); open(dst, 'w').write(buf.getvalue())


def main():
    tmp = tempfile.mkdtemp(prefix='ledger-eval-')
    canon = os.path.join(tmp, 'ledger.yaml')
    canonicalize(REAL, canon)  # start in helper-canonical form

    # 1. per-write diff is clean once canonical
    work = os.path.join(tmp, 'w1', 'ledger.yaml'); os.makedirs(os.path.dirname(work))
    shutil.copy(canon, work)
    entry = {"file": "2026-07-30-eval.md", "ticket": "none", "theme": "t",
             "status": "awaiting_initiation", "source_session": "eval",
             "target_session": None, "created": "2026-07-30T00:00:00Z",
             "modified": "2026-07-30T00:00:00Z", "version": 1}
    run('append', '--section', 'handoffs', '--json', json.dumps(entry), path=work)
    d = subprocess.run(['diff', canon, work], capture_output=True, text=True).stdout
    changed = [l for l in d.splitlines() if l and l[0] in '<>']
    # expect: header version+modified (2 lines each side) + 10 new-entry lines ~= <=18
    check('per-write diff is clean (canonical form)', len(changed) <= 20,
          f'{len(changed)} changed lines')

    # 2. bootstrap creates + refuses overwrite
    bpath = os.path.join(tmp, 'boot', 'ledger.yaml'); os.makedirs(os.path.dirname(bpath))
    r = subprocess.run([sys.executable, BIN, '--ledger', bpath, 'bootstrap'], capture_output=True, text=True)
    check('bootstrap creates fresh ledger', r.returncode == 0 and os.path.exists(bpath), r.stderr)
    r2 = subprocess.run([sys.executable, BIN, '--ledger', bpath, 'bootstrap'], capture_output=True, text=True)
    check('bootstrap refuses to overwrite existing', r2.returncode != 0, 'should have failed')

    # 3. status vocabulary is OPEN (other orgs use shelved/superseded) — an uncommon
    #    status is advisory, NOT blocked. Structural problems still block (see #5).
    r = run('update', '--section', 'handoffs', '--key', '2026-07-30-eval.md',
            '--set', 'status=shelved', path=work)
    check('allows open-vocabulary status (advisory, not blocked)', r.returncode == 0,
          f'rc={r.returncode} err={r.stderr}')

    # 4. commit TOLERATES pre-existing debt (real ledger has dup slugs) — a normal update succeeds
    r = run('update', '--section', 'handoffs', '--key', '2026-07-30-eval.md',
            '--set', 'status=initiated', path=work)
    check('tolerates pre-existing debt on a valid update', r.returncode == 0, r.stderr)

    # 5. append refuses duplicate identity key
    r = run('append', '--section', 'handoffs', '--json', json.dumps(entry), path=work)
    check('append rejects duplicate file key', r.returncode != 0, 'should reject dup')

    # 6. claim CAS: wrong expected status is rejected
    r = run('claim', '--key', '2026-07-30-eval.md', '--expect-status', 'awaiting_initiation',
            '--set', 'status=initiated', path=work)  # current status is 'initiated', expect mismatch
    check('claim rejects on status mismatch (CAS)', r.returncode != 0, r.stdout)

    # 7. immutable identity key cannot be changed
    r = run('update', '--section', 'handoffs', '--key', '2026-07-30-eval.md',
            '--set', 'file=hacked.md', path=work)
    check('refuses to change immutable identity key', r.returncode != 0, 'should refuse')

    # 8. journal preimage written before mutation
    jdir = os.path.join(os.path.dirname(work), '.ledger-journal')
    check('journal preimage snapshots exist', os.path.isdir(jdir) and len(os.listdir(jdir)) >= 1,
          'no journal dir')

    # 9. validate flags the REAL corruption: MIXED col-2 + col-0 entries in one list (unparseable)
    bad = os.path.join(tmp, 'bad.yaml')
    open(bad, 'w').write("version: 1\nmodified: x\ncreated: y\nsessions:\n"
                         "  - slug: a\n    status: active\n"
                         "- slug: b\n  status: active\n"
                         "handoffs: []\n")
    r = subprocess.run([sys.executable, BIN, '--ledger', bad, 'validate'], capture_output=True, text=True)
    check('validate flags mixed-indent corruption (unparseable)', r.returncode != 0,
          f'rc={r.returncode} out={r.stdout[:80]}')

    # 10. batch applies multiple ops with one header bump
    e2 = dict(entry, file="2026-07-30-eval2.md")
    ops = [{"section": "handoffs", "op": "append", "entry": e2},
           {"section": "handoffs", "op": "update", "key": "2026-07-30-eval.md", "set": ["theme=batched"]}]
    r = run('batch', '--ops', json.dumps(ops), path=work)
    check('batch applies multiple ops', r.returncode == 0, r.stderr)

    # 11. operationalize gate: closing a session with a STALE manifest is blocked
    gtmp = tempfile.mkdtemp(prefix='ledger-gate-')
    sess = os.path.join(gtmp, 'sessions'); os.makedirs(os.path.join(sess, 'active', 'testy-owl'))
    glp = os.path.join(sess, 'ledger.yaml')
    subprocess.run([sys.executable, BIN, '--ledger', glp, 'bootstrap'], capture_output=True)
    run('append', '--section', 'sessions',
        '--json', json.dumps({"slug": "testy-owl", "intent": "x", "org": "klever", "status": "active", "created": "2026-07-30T00:00:00Z"}),
        path=glp)
    open(os.path.join(sess, 'active', 'testy-owl', 'knowledge-manifest.yaml'), 'w').write(
        "session_slug: testy-owl\nlast_run: '2020-01-01T00:00:00Z'\nrun_count: 1\nnuggets: []\nruns: []\n")
    r = run('update', '--section', 'sessions', '--key', 'testy-owl', '--set', 'status=closed', path=glp)
    check('operationalize gate blocks close with stale capture', r.returncode != 0, f'rc={r.returncode}')
    # skip file bypasses the gate
    open(os.path.join(sess, '.operationalize-skip'), 'w').write('test bypass\n')
    r = run('update', '--section', 'sessions', '--key', 'testy-owl', '--set', 'status=closed', path=glp)
    check('operationalize skip-file bypasses the gate', r.returncode == 0, r.stderr)
    shutil.rmtree(gtmp, ignore_errors=True)

    # 12. rekey: the only command that may touch an identity key, and the only way to
    #     reach a duplicate (find_entry always returns the first match).
    dup = os.path.join(tmp, 'dup.yaml')
    open(dup, 'w').write(
        "version: 1\nmodified: x\ncreated: y\nsessions:\n"
        "  - slug: keen-falcon\n    status: closed\n    created: '2026-06-03'\n"
        "  - slug: keen-falcon\n    status: closed\n    created: '2026-06-01'\n"
        "  - slug: solo-owl\n    status: closed\n    created: '2026-06-02'\n"
        "handoffs: []\n")
    r = subprocess.run([sys.executable, BIN, '--ledger', dup, 'validate'], capture_output=True, text=True)
    check('validate flags a duplicate slug', r.returncode != 0, r.stdout)

    r = run('rekey', '--section', 'sessions', '--old', 'keen-falcon', '--new', 'x-1', path=dup)
    check('rekey demands --occurrence when key is duplicated', r.returncode != 0, 'should refuse')

    r = run('rekey', '--section', 'sessions', '--old', 'solo-owl', '--new', 'keen-falcon', path=dup)
    check('rekey refuses a --new that already exists', r.returncode != 0, 'should refuse')

    r = run('rekey', '--section', 'sessions', '--old', 'keen-falcon', '--new', 'keen-falcon-20260601',
            '--occurrence', '2', path=dup)
    check('rekey renames the chosen occurrence', r.returncode == 0, r.stderr)

    r = subprocess.run([sys.executable, BIN, '--ledger', dup, 'validate'], capture_output=True, text=True)
    check('validate is clean after dedup', r.returncode == 0, r.stdout)

    _, ddoc = ledger.load(dup)
    slugs = [e['slug'] for e in ddoc['sessions']]
    check('rekey preserved order and touched exactly one entry',
          slugs == ['keen-falcon', 'keen-falcon-20260601', 'solo-owl'], str(slugs))
    check('rekey kept the renamed entry intact',
          ddoc['sessions'][1]['created'] == '2026-06-01', str(ddoc['sessions'][1]))

    r = run('update', '--section', 'sessions', '--key', 'solo-owl', '--set', 'slug=hacked', path=dup)
    check('update still refuses identity-key changes (rekey is the only path)',
          r.returncode != 0, 'should refuse')

    # 13. a new session can NEVER re-register an existing slug through the helper —
    #     the mechanical half of "slug generation must collide-check the ledger".
    #     Folders get archived and pruned; ledger entries are forever, so a slug that
    #     is free on disk may still be taken here.
    sess_entry = {"slug": "solo-owl", "intent": "collision", "org": "klever",
                  "status": "active", "created": "2026-08-14T00:00:00Z"}
    r = run('append', '--section', 'sessions', '--json', json.dumps(sess_entry), path=dup)
    check('append refuses a slug already in the ledger (closed sessions included)',
          r.returncode != 0, 'should reject dup slug')
    r = run('append', '--section', 'sessions',
            '--json', json.dumps(dict(sess_entry, slug='keen-falcon-20260601')), path=dup)
    check('append refuses a slug taken by a RENAMED entry too', r.returncode != 0,
          'should reject dup slug')

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()

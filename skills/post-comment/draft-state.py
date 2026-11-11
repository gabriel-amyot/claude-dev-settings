#!/usr/bin/env python3
"""Durable state for external drafts that were NOT posted in the same turn.

An unsent draft with no tracked state becomes invisible when the session closes.
This file gives every held draft an owner record, a hard expiry date, and a
reconcile step against the remote platform before it is resurfaced.

States: held -> posted | discarded | superseded
Remote reconcile results: posted | absent | unknown

Commands:
  hold       --draft P --target T --platform X --expires YYYY-MM-DD --reason R [--condition C]
  posted     --draft P [--url U]
  discarded  --draft P --reason R
  superseded --draft P --by P2
  reconcile  --draft P --remote posted|absent|unknown [--url U] [--evidence E] [--target T]
             (an untracked draft found posted gets a posted record; absent/unknown need hold first)
  due        [--today YYYY-MM-DD]         held drafts at or past expiry, with the next action
  scan       --drafts-dir D [--post-log L ...]   drafts with no state and no post-log entry

State file: --state PATH, else <--ticket-dir>/reports/ship/draft-state.json, else the
global file next to this script. Exit codes: 0 ok, 1 scan found untracked drafts,
2 usage or refused input.
"""
import argparse
import fcntl
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
GLOBAL_STATE = os.path.join(HERE, 'global-draft-state.json')
VAGUE = re.compile(r'\b(tbd|later|until we decide|when ready|someday|eventually|when we know)\b',
                   re.IGNORECASE)
RECONCILE_FRESH_HOURS = 24


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fail(msg):
    print(f'REFUSED: {msg}', file=sys.stderr)
    sys.exit(2)


def state_path(a):
    if a.state:
        return a.state
    if getattr(a, 'ticket_dir', None):
        return os.path.join(a.ticket_dir, 'reports', 'ship', 'draft-state.json')
    return GLOBAL_STATE


def load(path):
    if not os.path.exists(path):
        return {'drafts': {}}
    with open(path) as f:
        return json.load(f)


def save(path, doc):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(doc, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, path)


class Locked:
    def __init__(self, path):
        self.lock = os.path.abspath(path) + '.lock'

    def __enter__(self):
        os.makedirs(os.path.dirname(self.lock), exist_ok=True)
        self.fh = open(self.lock, 'w')
        fcntl.flock(self.fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


def key(draft):
    return os.path.abspath(os.path.expanduser(draft))


def mutate(a, fn):
    path = state_path(a)
    with Locked(path):
        doc = load(path)
        fn(doc['drafts'])
        save(path, doc)
    print(f'ok ({path})')


def require_record(drafts, k):
    if k not in drafts:
        fail(f'no held record for {k}: run `hold` first')
    return drafts[k]


def cmd_hold(a):
    try:
        expires = date.fromisoformat(a.expires)
    except (TypeError, ValueError):
        fail('--expires must be a YYYY-MM-DD date. A held draft needs a hard expiry, not an intention.')
    if expires < (date.fromisoformat(a.today) if a.today else date.today()):
        fail(f'--expires {a.expires} is in the past')
    if not a.reason or not a.reason.strip():
        fail('--reason is required: say why the draft is held')
    if a.condition and VAGUE.search(a.condition):
        fail(f'--condition "{a.condition}" is vague. Name the event and who confirms it.')

    def fn(drafts):
        drafts[key(a.draft)] = {'status': 'held', 'target': a.target, 'platform': a.platform,
                                'expires': a.expires, 'condition': a.condition or '',
                                'reason': a.reason, 'held_at': now(), 'history': []}
    mutate(a, fn)


def set_final(a, status, **fields):
    def fn(drafts):
        rec = require_record(drafts, key(a.draft))
        rec['history'].append({'at': now(), 'from': rec['status'], 'to': status})
        rec['status'] = status
        rec.update({k: v for k, v in fields.items() if v})
    mutate(a, fn)


def cmd_reconcile(a):
    def fn(drafts):
        k = key(a.draft)
        if k not in drafts and a.remote == 'posted':
            drafts[k] = {'status': 'untracked', 'target': a.target or '', 'platform': '',
                         'expires': '', 'condition': '', 'reason': 'found by scan, posted without a local log',
                         'held_at': now(), 'history': []}
        rec = require_record(drafts, k)
        rec['last_reconcile'] = {'at': now(), 'remote': a.remote, 'url': a.url or '',
                                 'evidence': a.evidence or ''}
        if a.remote == 'posted':
            rec['history'].append({'at': now(), 'from': rec['status'], 'to': 'posted'})
            rec['status'] = 'posted'
            rec['posted_url'] = a.url or ''
            rec['posted_source'] = 'remote-reconcile'
    mutate(a, fn)


def next_action(rec, now_dt):
    rc = rec.get('last_reconcile')
    if not rc:
        return 'reconcile_first', 'check the remote thread before you resurface it'
    age = now_dt - datetime.fromisoformat(rc['at'])
    if age > timedelta(hours=RECONCILE_FRESH_HOURS):
        return 'reconcile_first', f'last reconcile is older than {RECONCILE_FRESH_HOURS}h'
    if rc['remote'] == 'unknown':
        return 'ambiguous', 'remote state unknown: report it as ambiguous, not as unsent'
    return 'resurface', 'remote checked and absent: ask the human to post, revise, or discard'


def cmd_due(a):
    today = date.fromisoformat(a.today) if a.today else date.today()
    now_dt = (datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc))
    doc = load(state_path(a))
    out = []
    for k, rec in sorted(doc['drafts'].items()):
        if rec['status'] != 'held' or date.fromisoformat(rec['expires']) > today:
            continue
        action, why = next_action(rec, now_dt)
        out.append({'draft': k, 'target': rec['target'], 'expires': rec['expires'],
                    'action': action, 'why': why})
    print(json.dumps(out, indent=2))
    return 0


def post_log_paths(logs):
    paths = set()
    for log in logs or []:
        if not os.path.exists(log):
            continue
        for line in open(log):
            m = re.match(r'\s*draft_path:\s*"?([^"\n]*)"?', line)
            if m and m.group(1):
                paths.add(os.path.basename(m.group(1)))
    return paths


def cmd_scan(a):
    doc = load(state_path(a))
    tracked = {os.path.basename(k) for k in doc['drafts']}
    logged = post_log_paths(a.post_log)
    untracked = []
    for name in sorted(os.listdir(a.drafts_dir)):
        if not name.endswith('.md'):
            continue
        stem = name[:-3]
        if name in tracked or name in logged:
            continue
        if os.path.exists(os.path.join(a.drafts_dir, stem + '.posted')):
            continue
        untracked.append(os.path.join(os.path.abspath(a.drafts_dir), name))
    print(json.dumps({'untracked': untracked}, indent=2))
    return 1 if untracked else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--state')
    p.add_argument('--ticket-dir')
    sub = p.add_subparsers(dest='cmd', required=True)
    h = sub.add_parser('hold')
    for f in ('--draft', '--target', '--platform', '--expires', '--reason'):
        h.add_argument(f, required=True)
    h.add_argument('--condition')
    h.add_argument('--today', help=argparse.SUPPRESS)
    for name in ('posted', 'discarded', 'superseded'):
        s = sub.add_parser(name)
        s.add_argument('--draft', required=True)
        if name == 'posted':
            s.add_argument('--url')
        if name == 'discarded':
            s.add_argument('--reason', required=True)
        if name == 'superseded':
            s.add_argument('--by', required=True)
    r = sub.add_parser('reconcile')
    r.add_argument('--draft', required=True)
    r.add_argument('--remote', required=True, choices=('posted', 'absent', 'unknown'))
    r.add_argument('--url')
    r.add_argument('--evidence')
    r.add_argument('--target', help='target, when the draft has no record yet')
    d = sub.add_parser('due')
    d.add_argument('--today')
    d.add_argument('--now', help=argparse.SUPPRESS)
    sc = sub.add_parser('scan')
    sc.add_argument('--drafts-dir', required=True)
    sc.add_argument('--post-log', action='append')
    a = p.parse_args(argv)

    if a.cmd == 'hold':
        cmd_hold(a)
    elif a.cmd == 'posted':
        set_final(a, 'posted', posted_url=a.url)
    elif a.cmd == 'discarded':
        set_final(a, 'discarded', discard_reason=a.reason)
    elif a.cmd == 'superseded':
        set_final(a, 'superseded', superseded_by=key(a.by))
    elif a.cmd == 'reconcile':
        cmd_reconcile(a)
    elif a.cmd == 'due':
        return cmd_due(a)
    elif a.cmd == 'scan':
        return cmd_scan(a)
    return 0


if __name__ == '__main__':
    sys.exit(main())

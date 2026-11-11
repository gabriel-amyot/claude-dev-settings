#!/usr/bin/env python3
"""Layer A suite for post-comment/draft-state.py (unsent-draft tracking).

All state lives in a temp dir. Run: python3 run_draft_state_evals.py [--script PATH]
Exit 0 = all pass, 1 = a case failed.

Discriminating cases: before this change post-comment kept no state for a held draft,
so case 02 (vague hold), case 05 (resurface without remote reconcile) and case 06
(already posted remotely but missing from the local log) had no guard at all.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SCRIPT = os.path.join(os.path.dirname(HERE), 'draft-state.py')
PASS = FAIL = 0


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  PASS  {name}')
    else:
        FAIL += 1
        print(f'  FAIL  {name}  {detail}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--script', default=DEFAULT_SCRIPT)
    script = ap.parse_args().script
    tmp = tempfile.mkdtemp(prefix='draft-state-eval-')
    state = os.path.join(tmp, 'state', 'draft-state.json')

    def run(*args):
        r = subprocess.run([sys.executable, script, '--state', state, *args], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    def due(today, now=None):
        args = ['due', '--today', today]
        if now:
            args += ['--now', now]
        rc, out, err = run(*args)
        return json.loads(out) if rc == 0 else err

    try:
        drafts = os.path.join(tmp, 'drafts')
        os.makedirs(drafts)
        names = ['a-reply.md', 'b-vague.md', 'c-posted-remote.md', 'd-discarded.md', 'e-superseded.md',
                 'f-untracked.md', 'g-logged.md', 'h-dotposted.md', 'i-unknown.md']
        for n in names:
            open(os.path.join(drafts, n), 'w').write('draft\n')
        open(os.path.join(drafts, 'h-dotposted.posted'), 'w').write('rendered\n')
        p = {n: os.path.join(drafts, n) for n in names}
        future = '2026-11-10'

        # 01 hold with a hard expiry is accepted
        rc, _, err = run('hold', '--draft', p['a-reply.md'], '--target', 'KTP-1', '--platform', 'jira',
                         '--expires', future, '--reason', 'waiting for Mo to confirm the setting', '--today', '2026-11-06')
        check('01 hold with a date is accepted', rc == 0, err)

        # 02 refusals: no date, vague condition, past date
        rc, _, _ = run('hold', '--draft', p['b-vague.md'], '--target', 'KTP-1', '--platform', 'jira',
                       '--expires', 'next week', '--reason', 'x', '--today', '2026-11-06')
        check('02a non-date expiry is refused', rc == 2)
        rc, _, _ = run('hold', '--draft', p['b-vague.md'], '--target', 'KTP-1', '--platform', 'jira',
                       '--expires', future, '--reason', 'x', '--condition', 'hold until we decide', '--today', '2026-11-06')
        check('02b vague condition is refused', rc == 2)
        rc, _, _ = run('hold', '--draft', p['b-vague.md'], '--target', 'KTP-1', '--platform', 'jira',
                       '--expires', '2026-11-01', '--reason', 'x', '--today', '2026-11-06')
        check('02c past expiry is refused', rc == 2)

        # 03 not due before expiry
        check('03 nothing due before expiry', due('2026-11-09') == [])

        # 04 due after expiry, with no reconcile -> reconcile_first (never straight to resurface)
        res = due('2026-11-10')
        check('04 due at expiry asks to reconcile first',
              len(res) == 1 and res[0]['action'] == 'reconcile_first', res)

        # 05 reconcile absent -> resurface; a stale reconcile -> reconcile_first again
        run('reconcile', '--draft', p['a-reply.md'], '--remote', 'absent', '--evidence', 'no matching comment on KTP-1')
        res = due('2026-11-10')
        check('05a fresh absent reconcile -> resurface', res and res[0]['action'] == 'resurface', res)
        later = (datetime.now(timezone.utc) + timedelta(hours=30)).isoformat()
        res = due('2026-11-10', now=later)
        check('05b stale reconcile -> reconcile_first', res and res[0]['action'] == 'reconcile_first', res)

        # 06 held draft that was already posted remotely is NOT resurfaced as unsent
        run('hold', '--draft', p['c-posted-remote.md'], '--target', 'KTP-2', '--platform', 'jira',
            '--expires', future, '--reason', 'r', '--today', '2026-11-06')
        run('reconcile', '--draft', p['c-posted-remote.md'], '--remote', 'posted', '--url', 'https://x/1')
        res = due('2026-11-12')
        check('06 remote-posted draft drops out of the due list',
              all(r['draft'] != p['c-posted-remote.md'] for r in res), res)

        # 07 unknown remote -> ambiguous, not unsent
        run('hold', '--draft', p['i-unknown.md'], '--target', 'KTP-3', '--platform', 'slack',
            '--expires', future, '--reason', 'r', '--today', '2026-11-06')
        run('reconcile', '--draft', p['i-unknown.md'], '--remote', 'unknown', '--evidence', 'Slack search unavailable')
        res = {r['draft']: r for r in due('2026-11-12')}
        check('07 unknown remote -> ambiguous', res.get(p['i-unknown.md'], {}).get('action') == 'ambiguous', res)

        # 08 discarded and superseded drafts are closed, never resurfaced
        for n in ('d-discarded.md', 'e-superseded.md'):
            run('hold', '--draft', p[n], '--target', 'KTP-4', '--platform', 'jira', '--expires', future,
                '--reason', 'r', '--today', '2026-11-06')
        run('discarded', '--draft', p['d-discarded.md'], '--reason', 'question answered in thread')
        run('superseded', '--draft', p['e-superseded.md'], '--by', p['a-reply.md'])
        res = [r['draft'] for r in due('2026-11-12')]
        check('08 discarded and superseded drafts are not due',
              p['d-discarded.md'] not in res and p['e-superseded.md'] not in res, res)

        # 09 scan: only the draft with no state, no post-log entry and no .posted file is untracked
        log = os.path.join(tmp, 'post-log.yaml')
        open(log, 'w').write('- timestamp: "2026-11-01"\n  draft_path: "/elsewhere/g-logged.md"\n')
        r = subprocess.run([sys.executable, script, '--state', state, 'scan', '--drafts-dir', drafts,
                            '--post-log', log], capture_output=True, text=True)
        out = json.loads(r.stdout)['untracked']
        check('09 scan exits 1 when an untracked draft exists', r.returncode == 1, r.stderr)
        check('09 scan lists exactly the untracked drafts',
              sorted(os.path.basename(x) for x in out) == ['b-vague.md', 'f-untracked.md'], out)

        # 10 untracked draft found posted remotely gets a posted record, then scan is clean for it
        rc, _, err = run('reconcile', '--draft', p['f-untracked.md'], '--remote', 'posted',
                         '--url', 'https://x/2', '--target', 'KTP-5')
        check('10a reconcile posted on an untracked draft records it', rc == 0, err)
        rc, _, _ = run('reconcile', '--draft', p['b-vague.md'], '--remote', 'absent')
        check('10b reconcile absent on an untracked draft requires hold first', rc == 2)

        doc = json.load(open(state))
        check('11 state is durable JSON on disk', doc['drafts'][p['a-reply.md']]['status'] == 'held')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

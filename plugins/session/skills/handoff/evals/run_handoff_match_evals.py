#!/usr/bin/env python3
"""Layer A suite for handoff_match.py (umbrella-ticket idempotency).

Builds a temp fixture ledger and session folders. Never reads or writes the real
sessions/ledger.yaml. Run: python3 run_handoff_match_evals.py  (exit 0 = all pass)

Cases that FAIL under the old rule ("match by ticket only, update in place"):
  02, 03 return `update` under the old rule and would overwrite another session's file.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), 'scripts', 'handoff_match.py')
LEDGER_BIN = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'bin', 'ledger.py'))
PASS = FAIL = 0


def python_with_ruamel():
    """ledger.py needs ruamel.yaml. The default python3 on PATH may not have it."""
    for py in (sys.executable, '/usr/bin/python3'):
        if subprocess.run([py, '-c', 'import ruamel.yaml'], capture_output=True).returncode == 0:
            return py
    sys.exit('FATAL: no python3 with ruamel.yaml (python3 -m pip install --user ruamel.yaml)')


PY = python_with_ruamel()


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  PASS  {name}')
    else:
        FAIL += 1
        print(f'  FAIL  {name}  {detail}')


def entry(file, ticket, theme, status, source):
    return {'file': file, 'ticket': ticket, 'theme': theme, 'status': status,
            'source_session': source, 'target_session': None,
            'created': '2026-11-01T00:00:00Z', 'modified': '2026-11-01T00:00:00Z', 'version': 1}


def write_handoff(root, session, file, body):
    d = os.path.join(root, 'active', session, 'prompts')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, file), 'w') as f:
        f.write(body)


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_match(ledger_path, ticket, theme, session):
    r = subprocess.run([PY, SCRIPT, '--ledger', ledger_path, '--ticket', ticket,
                        '--theme', theme, '--session', session], capture_output=True, text=True)
    if r.returncode != 0:
        return {'action': 'ERROR', 'stderr': r.stderr}
    return json.loads(r.stdout)


def old_rule(handoffs, ticket):
    """The pre-change rule, kept only to prove the new cases are discriminating."""
    for h in handoffs:
        if ticket != 'none' and h['ticket'] == ticket and h['status'] == 'awaiting_initiation':
            return 'update'
    return 'create'


def main():
    tmp = tempfile.mkdtemp(prefix='handoff-match-eval-')
    try:
        sessions = os.path.join(tmp, 'sessions')
        os.makedirs(sessions)
        ledger_path = os.path.join(sessions, 'ledger.yaml')
        r = subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'bootstrap'],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print('FATAL: fixture bootstrap failed', r.stderr)
            return 1

        fixtures = [
            ('other', entry('2026-11-01-ktp853-langsmith.md', 'KTP-853', 'langsmith', 'awaiting_initiation', 'other-lynx')),
            ('other', entry('2026-11-02-ktp853-prod-close.md', 'KTP-853', 'proxi', 'awaiting_initiation', 'other-lynx')),
            ('mine', entry('2026-11-03-ktp864-cron.md', 'KTP-864', 'proxi', 'awaiting_initiation', 'mine-otter')),
            ('mine', entry('2026-11-03-ktp900-a.md', 'KTP-900', 'census', 'awaiting_initiation', 'mine-otter')),
            ('mine', entry('2026-11-03-ktp900-b.md', 'KTP-900', 'census', 'awaiting_initiation', 'mine-otter')),
            ('other', entry('2026-11-01-ktp901-live.md', 'KTP-901', 'census', 'initiated', 'other-lynx')),
            ('other', entry('2026-10-01-ktp902-done.md', 'KTP-902', 'census', 'completed', 'other-lynx')),
        ]
        session_dir = {'other': 'other-lynx', 'mine': 'mine-otter'}
        for owner, e in fixtures:
            write_handoff(sessions, session_dir[owner], e['file'], f'# {e["file"]}\n')
            r = subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'append',
                                '--section', 'handoffs', '--json', json.dumps(e)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print('FATAL: fixture append failed', r.stderr)
                return 1
        handoffs = [e for _, e in fixtures]
        other_files = [os.path.join(sessions, 'active', 'other-lynx', 'prompts', e['file'])
                       for o, e in fixtures if o == 'other']
        before = {p: sha(p) for p in other_files}

        # 01: new theme on an umbrella ticket creates and lists siblings
        res = run_match(ledger_path, 'KTP-853', 'census-cron', 'mine-otter')
        check('01 new theme on umbrella ticket -> create', res.get('action') == 'create', res)
        check('01 siblings list both open KTP-853 handoffs',
              sorted(res.get('siblings', [])) == ['2026-11-01-ktp853-langsmith.md', '2026-11-02-ktp853-prod-close.md'], res)

        # 02: same ticket AND theme, but another session owns it -> create, never update
        res = run_match(ledger_path, 'KTP-853', 'proxi', 'mine-otter')
        check('02 same ticket+theme owned by another session -> create', res.get('action') == 'create', res)
        check('02 old rule would have updated in place (discriminating case)',
              old_rule(handoffs, 'KTP-853') == 'update')

        # 03: ticket matches only by ticket (different theme) -> create
        res = run_match(ledger_path, 'KTP-853', 'langsmith-eval', 'mine-otter')
        check('03 ticket-only match -> create', res.get('action') == 'create', res)

        # 04: this session owns the awaiting handoff -> update that file
        res = run_match(ledger_path, 'KTP-864', 'proxi', 'mine-otter')
        check('04 own awaiting same ticket+theme -> update', res.get('action') == 'update'
              and res.get('file') == '2026-11-03-ktp864-cron.md', res)

        # 05: the same request from another session must not update mine
        res = run_match(ledger_path, 'KTP-864', 'proxi', 'third-heron')
        check('05 other session asks on my handoff -> create', res.get('action') == 'create', res)

        # 06: two own matches are ambiguous -> ask
        res = run_match(ledger_path, 'KTP-900', 'census', 'mine-otter')
        check('06 two own awaiting matches -> ask', res.get('action') == 'ask', res)

        # 07: initiated match -> ask (work may be in progress)
        res = run_match(ledger_path, 'KTP-901', 'census', 'mine-otter')
        check('07 initiated same ticket+theme -> ask', res.get('action') == 'ask', res)

        # 07b: completed same ticket+theme is a continuation -> create and cite it
        res = run_match(ledger_path, 'KTP-902', 'census', 'mine-otter')
        check('07b completed same ticket+theme -> create with completed_matches',
              res.get('action') == 'create'
              and res.get('completed_matches') == ['2026-10-01-ktp902-done.md'], res)

        # 08: ticket none -> create, no matching
        res = run_match(ledger_path, 'none', 'harness', 'mine-otter')
        check('08 ticket none -> create', res.get('action') == 'create', res)

        # 09: a create through the helper leaves other sessions' handoffs byte-identical
        new = entry('2026-11-06-ktp853-census-cron.md', 'KTP-853', 'census-cron', 'awaiting_initiation', 'mine-otter')
        write_handoff(sessions, 'mine-otter', new['file'], '# new\n')
        r = subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'append',
                            '--section', 'handoffs', '--json', json.dumps(new)], capture_output=True, text=True)
        check('09 helper append succeeds on fixture ledger', r.returncode == 0, r.stderr)
        check('09 other sessions\' handoff files are byte-identical',
              all(sha(p) == before[p] for p in other_files))
        g = subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'get', '--section',
                            'handoffs', '--key', '2026-11-02-ktp853-prod-close.md'], capture_output=True, text=True)
        check('09 sibling ledger entry is unchanged (version 1)', '"version": 1' in g.stdout
              or 'version: 1' in g.stdout, g.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Layer A suite for pickup's triage_worksheet.py (queue triage scope audit).

Builds a temp fixture ledger plus handoff files. Never reads or writes the real
sessions/ledger.yaml. Run: python3 run_triage_worksheet_evals.py  (exit 0 = all pass)

Discriminating cases: under the old --triage rule ("Jira Done -> completion candidate"),
rows h-blocked, h-prod, h-mismatch and h-programme are all completion candidates. The
new scope audit must HOLD every one of them (the tidy-shrike rescue classes).
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), 'scripts', 'triage_worksheet.py')
LEDGER_BIN = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'bin', 'ledger.py'))
PASS = FAIL = 0


def python_with_ruamel():
    for py in (sys.executable, '/usr/bin/python3'):
        if subprocess.run([py, '-c', 'import ruamel.yaml'], capture_output=True).returncode == 0:
            return py
    sys.exit('FATAL: no python3 with ruamel.yaml')


PY = python_with_ruamel()


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  PASS  {name}')
    else:
        FAIL += 1
        print(f'  FAIL  {name}  {detail}')


def handoff_text(ticket, body):
    return (f'---\ncreated: 2026-10-01T00:00:00Z\nsource_session: fixture\ntype: handoff\n'
            f'status: awaiting_initiation\nrelated_ticket: {ticket}\n---\n\n## Prompt\n{body}\n')


# file, ledger ticket, theme, status, created, frontmatter ticket, body, expected verdict
CASES = [
    ('h-clean-done.md', 'KTP-10', 'alpha', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'KTP-10',
     'Write the unit test for the parser.', 'ARCHIVE_CANDIDATE'),
    ('h-blocked.md', 'KTP-11', 'alpha', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'KTP-11',
     'BLOCKED on vendor key. Then finish the import.', 'HOLD'),
    ('h-prod.md', 'KTP-12', 'alpha', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'KTP-12',
     'Verify the bid write gate on prod before release.', 'HOLD'),
    ('h-mismatch.md', 'KTP-13', 'alpha', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'KTP-99',
     'Close the follow-up.', 'HOLD'),
    ('h-programme.md', 'KTP-14', 'alpha', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'KTP-14',
     'Drive KTP-20, KTP-21 and KTP-22 to dev.', 'HOLD'),
    ('h-none.md', 'none', 'harness', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'none',
     'Refactor the hook.', 'PROBE'),
    ('h-moved.md', 'KTP-15', 'beta', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'KTP-15',
     'Finish the map layer.', 'CHECK_KEY'),
    ('h-live.md', 'KTP-16', 'beta', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'KTP-16',
     'Finish the map legend.', 'KEEP'),
    ('h-older.md', 'KTP-17', 'gamma', 'awaiting_initiation', '2026-09-01T00:00:00Z', 'KTP-17',
     'Draft the cron design.', 'REVIEW'),
    ('h-newer.md', 'KTP-17', 'gamma', 'awaiting_initiation', '2026-10-05T00:00:00Z', 'KTP-17',
     'Add the cron monitor.', 'KEEP'),
    ('h-missing.md', 'KTP-18', 'gamma', 'awaiting_initiation', '2026-10-01T00:00:00Z', None,
     None, 'HOLD'),
    ('h-context-only.md', 'KTP-19', 'delta', 'awaiting_initiation', '2026-10-01T00:00:00Z', 'KTP-19',
     'Write the README section.\n\n## Context\nShipped to prod with KTP-1, KTP-2 and KTP-3.', 'ARCHIVE_CANDIDATE'),
]
JIRA = {'KTP-10': 'Done', 'KTP-11': 'Done', 'KTP-12': 'Done', 'KTP-13': 'Done', 'KTP-14': 'Closed',
        'KTP-16': 'In Progress', 'KTP-17': 'To Do', 'KTP-18': 'Done', 'KTP-19': 'Done'}


def main():
    tmp = tempfile.mkdtemp(prefix='triage-eval-')
    try:
        sessions = os.path.join(tmp, 'sessions')
        prompts = os.path.join(sessions, 'active', 'fixture', 'prompts')
        os.makedirs(prompts)
        ledger_path = os.path.join(sessions, 'ledger.yaml')
        r = subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'bootstrap'], capture_output=True, text=True)
        if r.returncode != 0:
            print('FATAL: bootstrap', r.stderr)
            return 1
        for f, t, th, st, cr, fm, body, _ in CASES:
            if body is not None:
                with open(os.path.join(prompts, f), 'w') as fh:
                    fh.write(handoff_text(fm, body))
            e = {'file': f, 'ticket': t, 'theme': th, 'status': st, 'source_session': 'fixture',
                 'target_session': None, 'created': cr, 'modified': cr, 'version': 1}
            r = subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'append', '--section', 'handoffs',
                                '--json', json.dumps(e), '--position', 'bottom'], capture_output=True, text=True)
            if r.returncode != 0:
                print('FATAL: append', r.stderr)
                return 1
        closed = {'file': 'h-closed.md', 'ticket': 'KTP-10', 'theme': 'alpha', 'status': 'completed',
                  'source_session': 'fixture', 'target_session': None, 'created': '2026-10-02T00:00:00Z',
                  'modified': '2026-10-02T00:00:00Z', 'version': 1}
        subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'append', '--section', 'handoffs',
                        '--json', json.dumps(closed)], capture_output=True, text=True)
        before = open(ledger_path).read()

        jira_path = os.path.join(tmp, 'jira.json')
        with open(jira_path, 'w') as fh:
            json.dump(JIRA, fh)
        out = os.path.join(tmp, 'out', 'worksheet.csv')
        r = subprocess.run([PY, SCRIPT, '--ledger', ledger_path, '--out', out, '--jira-status', jira_path,
                            '--today', '2026-11-06'], capture_output=True, text=True)
        check('script exits 0', r.returncode == 0, r.stderr)
        rows = {row['file']: row for row in csv.DictReader(open(out))}

        check('only awaiting handoffs are rows (completed excluded)', 'h-closed.md' not in rows
              and len(rows) == len(CASES), sorted(rows))
        for f, *_rest, expected in CASES:
            got = rows.get(f, {}).get('verdict')
            check(f'{f} -> {expected}', got == expected, rows.get(f))
        check('h-prod flagged env_named', 'env_named' in rows['h-prod.md']['scope_flags'])
        check('h-mismatch flagged ticket_mismatch', 'ticket_mismatch' in rows['h-mismatch.md']['scope_flags'])
        check('h-missing flagged file_missing', rows['h-missing.md']['scope_flags'] == 'file_missing')
        check('age computed from created', rows['h-clean-done.md']['age_days'] == '36', rows['h-clean-done.md'])
        check('stdout is a one-line summary, not the rows', len(r.stdout.strip().splitlines()) == 1, r.stdout)
        check('ledger is untouched (read-only)', open(ledger_path).read() == before)

        out2 = os.path.join(tmp, 'out', 'nojira.csv')
        subprocess.run([PY, SCRIPT, '--ledger', ledger_path, '--out', out2, '--today', '2026-11-06'],
                       capture_output=True, text=True)
        rows2 = {row['file']: row for row in csv.DictReader(open(out2))}
        check('no Jira join -> UNCHECKED, never ARCHIVE_CANDIDATE',
              rows2['h-clean-done.md']['verdict'] == 'UNCHECKED'
              and not any(v['verdict'] == 'ARCHIVE_CANDIDATE' for v in rows2.values()))

        # Competing writer: another session claims a row after the worksheet was built.
        subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'claim', '--key', 'h-clean-done.md',
                        '--expect-status', 'awaiting_initiation', '--set', 'status=initiated',
                        '--set', 'target_session=other'], capture_output=True, text=True)
        r = subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'claim', '--key', 'h-clean-done.md',
                            '--expect-status', 'awaiting_initiation', '--set', 'status=completed',
                            '--set', 'archived=2026-11-06', '--set', 'archive_reason=KTP-10 Done'],
                           capture_output=True, text=True)
        check('CAS archive write refuses a row another session claimed', r.returncode != 0, r.stdout)
        g = subprocess.run([PY, LEDGER_BIN, '--ledger', ledger_path, 'get', '--section', 'handoffs',
                            '--key', 'h-clean-done.md'], capture_output=True, text=True)
        check('the competing claim is preserved (status initiated)', 'initiated' in g.stdout, g.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

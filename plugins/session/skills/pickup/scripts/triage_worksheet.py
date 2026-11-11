#!/usr/bin/env python3
"""Build the /pickup --triage worksheet on disk. Read-only on the ledger.

One CSV row per `awaiting_initiation` forward handoff. The rows stay on disk; only a
one-line summary goes to stdout. Rule pass and scope audit are deterministic:

  HOLD               a scope flag fired. Never an archive candidate without a human probe.
  PROBE              ticket is `none`. Probe the exact artifact the ask names.
  CHECK_KEY          the ticket is missing from the Jira result (project move or typo).
  ARCHIVE_CANDIDATE  terminal Jira status and no scope flag.
  REVIEW             a newer handoff has the same ticket+theme. On an umbrella ticket
                     that is not proof of supersession: compare the two asks.
  KEEP               live ticket and nothing newer.
  UNCHECKED          no --jira-status file was given.

Scope flags (any one forces HOLD):
  blocked_marker   the handoff file carries a BLOCKED marker anywhere
  env_named        the ask (## Prompt section) names prod / production / uat (confirm that env is covered)
  programme_shaped the ask (## Prompt section) names 3 or more distinct ticket keys
  ticket_mismatch  frontmatter related_ticket disagrees with the ledger ticket
  file_missing     the handoff file is not on disk, so its scope cannot be read

Usage:
  triage_worksheet.py (--org ORG | --ledger PATH) --out CSV
                      [--jira-status JSON] [--today YYYY-MM-DD]
  --jira-status: a JSON object {"KTP-1": "Done", ...} from one batched Jira query.
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime

try:
    import ruamel.yaml  # noqa: F401  (ledger.py needs it)
except ImportError:
    if sys.executable != '/usr/bin/python3' and os.path.exists('/usr/bin/python3'):
        os.execv('/usr/bin/python3', ['/usr/bin/python3', os.path.abspath(__file__), *sys.argv[1:]])

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', '..', 'bin')))
import ledger  # noqa: E402

TERMINAL = {'done', 'closed', "won't do", 'wont do', 'cancelled', 'canceled', 'resolved'}
KEY_RE = re.compile(r'\b[A-Z][A-Z0-9]+-\d+\b')
BLOCKED_RE = re.compile(r'\bBLOCKED\b')
ENV_RE = re.compile(r'\b(prod|production|uat)\b', re.IGNORECASE)
PROMPT_RE = re.compile(r'^## Prompt\s*\n(.*?)(?=^## |\Z)', re.DOTALL | re.MULTILINE)
FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)
COLUMNS = ['file', 'ticket', 'theme', 'source_session', 'created', 'age_days', 'disk_path',
           'superseded_by', 'jira_status', 'frontmatter_ticket', 'scope_flags', 'verdict', 'reason']


def index_markdown(sessions_dir):
    """Map file name -> paths under sessions/. Covers legacy layouts too
    (active/prompts/, active/, archive/{slug}/prompts/, archive/{bucket}/{slug}/prompts/)."""
    idx = {}
    for dirpath, _dirs, files in os.walk(sessions_dir):
        for f in files:
            if f.endswith('.md'):
                idx.setdefault(f, []).append(os.path.join(dirpath, f))
    return idx


def resolve_file(sessions_dir, entry, idx):
    name = entry.get('file', '')
    root = os.path.dirname(sessions_dir)
    if '/' in name:
        p = os.path.join(root, name)
        return p if os.path.isfile(p) else ''
    hits = sorted(idx.get(name, []))
    src = str(entry.get('source_session') or '')
    own = [h for h in hits if src and (os.sep + src + os.sep) in h]
    return (own or hits or [''])[0]


def frontmatter_ticket(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return ''
    for line in m.group(1).splitlines():
        if line.startswith('related_ticket:'):
            return line.split(':', 1)[1].strip().strip('"\'')
    return ''


def ask_text(text):
    """The ask is the ## Prompt section. Context mentions do not name the ask's scope."""
    m = PROMPT_RE.search(text)
    return m.group(1) if m else text


def scope_flags(entry, text, disk_path):
    if not disk_path:
        return ['file_missing']
    flags = []
    ask = ask_text(text)
    if BLOCKED_RE.search(text):
        flags.append('blocked_marker')
    if ENV_RE.search(ask):
        flags.append('env_named')
    if len(set(KEY_RE.findall(ask))) >= 3:
        flags.append('programme_shaped')
    fm = frontmatter_ticket(text)
    lt = str(entry.get('ticket') or 'none')
    if fm and fm.lower() != 'none' and fm != lt:
        flags.append('ticket_mismatch')
    return flags


def age_days(created, today):
    try:
        d = datetime.fromisoformat(str(created).replace('Z', '+00:00')).date()
    except ValueError:
        return ''
    return (today - d).days


def superseded_by(entry, handoffs):
    t, th = entry.get('ticket'), entry.get('theme')
    if not t or t == 'none' or not th:
        return ''
    newer = [h for h in handoffs if h is not entry and h.get('ticket') == t and h.get('theme') == th
             and not h.get('closes') and str(h.get('created', '')) > str(entry.get('created', ''))]
    return newer[-1]['file'] if newer else ''


def verdict(ticket, flags, status, superseder, jira_loaded=True):
    if flags:
        return 'HOLD', 'scope audit: ' + ', '.join(flags)
    if not ticket or ticket == 'none':
        return 'PROBE', 'no ticket: probe the exact artifact the ask names'
    if not jira_loaded:
        return 'UNCHECKED', 'no Jira result given: run the Jira join first'
    if status is None:
        return 'CHECK_KEY', 'ticket missing from the Jira result: check for a project move'
    if status.strip().lower() in TERMINAL:
        return 'ARCHIVE_CANDIDATE', f'{ticket} is {status}'
    if superseder:
        return 'REVIEW', f'newer handoff {superseder} has the same ticket+theme: compare the two asks'
    return 'KEEP', f'{ticket} is {status} and nothing newer supersedes it'


def build_rows(doc, sessions_dir, jira, today):
    handoffs = [h for h in (doc.get('handoffs') or []) if isinstance(h, dict)]
    rows = []
    idx = index_markdown(sessions_dir)
    for e in handoffs:
        if e.get('status') != 'awaiting_initiation' or e.get('closes'):
            continue
        disk = resolve_file(sessions_dir, e, idx)
        text = open(disk).read() if disk else ''
        flags = scope_flags(e, text, disk)
        ticket = str(e.get('ticket') or 'none')
        status = jira.get(ticket) if jira is not None else None
        sup = superseded_by(e, handoffs)
        v, why = verdict(ticket, flags, status, sup, jira is not None)
        rows.append({'file': e.get('file'), 'ticket': ticket, 'theme': e.get('theme') or '',
                     'source_session': e.get('source_session') or '', 'created': e.get('created') or '',
                     'age_days': age_days(e.get('created', ''), today), 'disk_path': disk,
                     'superseded_by': sup, 'jira_status': status or '',
                     'frontmatter_ticket': frontmatter_ticket(text), 'scope_flags': ';'.join(flags),
                     'verdict': v, 'reason': why})
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--org', choices=list(ledger.ORG_LEDGERS))
    p.add_argument('--ledger')
    p.add_argument('--out', required=True)
    p.add_argument('--jira-status', help='JSON file {KEY: status}')
    p.add_argument('--today', help='YYYY-MM-DD (default: today)')
    a = p.parse_args(argv)
    path = a.ledger or (ledger.ORG_LEDGERS.get(a.org) if a.org else None)
    if not path:
        p.error('pass --org or --ledger')
    _, doc = ledger.load(path)
    jira = json.load(open(a.jira_status)) if a.jira_status else None
    today = date.fromisoformat(a.today) if a.today else date.today()
    rows = build_rows(doc, os.path.dirname(os.path.abspath(path)), jira, today)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r['verdict']] = counts.get(r['verdict'], 0) + 1
    print(f"{len(rows)} awaiting -> " + ' · '.join(f'{k} {v}' for k, v in sorted(counts.items()))
          + f'  (worksheet: {a.out})')
    return 0


if __name__ == '__main__':
    sys.exit(main())

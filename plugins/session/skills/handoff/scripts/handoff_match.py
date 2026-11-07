#!/usr/bin/env python3
"""Read-only idempotency decision for /session:handoff.

Decides whether a new handoff updates an existing file or creates a new one.
It never writes the ledger. The caller performs the write with the `ledger` helper.

Identity key: (ticket, theme). The theme must be derived BEFORE this check.
Ownership: a handoff belongs to the current session only when its file is on disk
under sessions/active/{current-session}/prompts/. The `source_session` field is a
label and is never read here.

Decisions (JSON on stdout, exit 0):
  create  : write a new file and append a new ledger entry
  update  : update `file` in place (only a file this session owns, still awaiting)
  ask     : stop and ask the user (initiated match, or several own matches)
`siblings` lists other open handoffs on the same ticket for the new file's Context.
`completed_matches` lists completed handoffs with the same key (a continuation, cite them).

Usage:
  handoff_match.py (--org ORG | --ledger PATH) --ticket KEY --theme TAG --session SLUG
"""
import argparse
import json
import os
import sys

try:
    import ruamel.yaml  # noqa: F401  (ledger.py needs it)
except ImportError:
    if sys.executable != '/usr/bin/python3' and os.path.exists('/usr/bin/python3'):
        os.execv('/usr/bin/python3', ['/usr/bin/python3', os.path.abspath(__file__), *sys.argv[1:]])

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_BIN_DIR = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'bin'))
sys.path.insert(0, LEDGER_BIN_DIR)
import ledger  # noqa: E402  (shared loader and org map; read-only use)

OPEN_STATUSES = ('awaiting_initiation', 'initiated')


def is_owned(sessions_dir, session, filename):
    return os.path.isfile(os.path.join(sessions_dir, 'active', session, 'prompts', filename))


def decide(handoffs, ticket, theme, session, sessions_dir):
    if not ticket or ticket == 'none':
        return {'action': 'create', 'reason': 'ticket is none: no matching', 'siblings': []}
    if not theme:
        return {'action': 'ask', 'reason': 'derive the theme before the idempotency check', 'siblings': []}

    same_ticket = [h for h in handoffs if isinstance(h, dict) and h.get('ticket') == ticket
                   and not h.get('closes')]
    same_key = [h for h in same_ticket if h.get('theme') == theme]

    own_awaiting = [h['file'] for h in same_key
                    if h.get('status') == 'awaiting_initiation'
                    and is_owned(sessions_dir, session, h.get('file', ''))]
    if len(own_awaiting) == 1:
        return {'action': 'update', 'file': own_awaiting[0],
                'reason': 'this session owns an awaiting handoff with the same ticket and theme',
                'siblings': [h['file'] for h in same_ticket
                             if h.get('status') in OPEN_STATUSES and h['file'] != own_awaiting[0]]}
    if len(own_awaiting) > 1:
        return {'action': 'ask', 'files': own_awaiting,
                'reason': 'this session owns several awaiting handoffs with the same ticket and theme',
                'siblings': []}

    siblings = [h['file'] for h in same_ticket if h.get('status') in OPEN_STATUSES]
    in_progress = [h['file'] for h in same_key if h.get('status') == 'initiated']
    if in_progress:
        return {'action': 'ask', 'files': in_progress,
                'reason': 'same ticket and theme is initiated: the work may be in progress elsewhere',
                'siblings': siblings}

    return {'action': 'create',
            'reason': 'no handoff owned by this session matches; other sessions\' handoffs are never updated',
            'siblings': siblings,
            'completed_matches': [h['file'] for h in same_key if h.get('status') == 'completed']}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--org', choices=list(ledger.ORG_LEDGERS))
    p.add_argument('--ledger', help='explicit ledger path (tests and non-default layouts)')
    p.add_argument('--ticket', required=True)
    p.add_argument('--theme', required=True)
    p.add_argument('--session', required=True, help='current session slug')
    a = p.parse_args(argv)
    path = a.ledger or (ledger.ORG_LEDGERS.get(a.org) if a.org else None)
    if not path:
        p.error('pass --org or --ledger')
    _, doc = ledger.load(path)
    sessions_dir = os.path.dirname(os.path.abspath(path))
    result = decide(list(doc.get('handoffs') or []), a.ticket, a.theme, a.session, sessions_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())

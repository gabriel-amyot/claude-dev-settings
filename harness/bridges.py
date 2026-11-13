"""Read-only bridges from existing harness evidence to the shared catalog.

No producer is executed. Raw transcripts and arbitrary tool payloads are never stored.
Only supported structured events count as use; unsupported sources remain visible coverage gaps.
"""
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex

try:
    from .store import stable_id, utc_now
except ImportError:
    from store import stable_id, utc_now

EXCLUDE = {'.git', 'node_modules', '__pycache__', '_archive', 'archive', 'archives',
           'fixtures', 'tests', 'evals', 'synced', 'local-marketplace-backup', 'backups'}
ORG_TOKEN = {'klever': 'grp-beklever-com', 'supervisrai': 'supervisr-ai',
             'supervisr': 'supervisr-ai', 'personal': 'gabriel-amyot'}
MAX_TEXT = 2 * 1024 * 1024
MAX_ACTIVITY_BYTES = 512 * 1024 * 1024


def _text(path, limit=MAX_TEXT):
    if path.stat().st_size > limit:
        raise ValueError(f'source exceeds bounded read ({limit} bytes): {path}')
    return path.read_text(encoding='utf-8', errors='replace')


def _scalar(value):
    value = value.strip()
    if value in ('null', '~'): return None
    if value[:1] == '"':
        try: return json.loads(value)
        except json.JSONDecodeError: return value.strip('"')
    if value[:1] == "'": return value.strip("'").replace("''", "'")
    return re.split(r'\s+#', value, maxsplit=1)[0].strip()


def _fields(text):
    """Safe bounded scalar extraction, not a general YAML interpreter."""
    rows = text.splitlines()
    if rows and rows[0].strip() == '---':
        try: rows = rows[1:rows[1:].index('---') + 1]
        except ValueError: rows = rows[1:]
    out = {}; folded = None
    for line in rows:
        m = re.match(r'^([\w-]+):\s*(.*)$', line)
        if m:
            key, val = m.groups(); folded = key if val in ('>', '|', '>-', '|-') else None
            out[key] = '' if folded else _scalar(val)
        elif folded and line.startswith((' ', '\t')):
            out[folded] += (' ' if out[folded] else '') + line.strip()
        elif line.strip(): folded = None
    return out


def _walk(root, filenames=('SKILL.md',)):
    if not root.is_dir(): return
    visited = set()
    for base, dirs, files in os.walk(root, followlinks=True):
        canonical = Path(base).resolve()
        if canonical in visited:
            dirs[:] = []
            continue
        visited.add(canonical)
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE and 'workspace' not in d
                         and '.before-shared-link-' not in d and not d.startswith('.'))
        for name in sorted(files):
            if name in filenames: yield Path(base) / name


def _fingerprint(path):
    digest = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(65536), b''): digest.update(block)
    return digest.hexdigest()


def _artifact(store, path, kind, summary=''):
    path = path.resolve(); fingerprint = _fingerprint(path)
    ident = stable_id('artifact', str(path), fingerprint)
    # Immutable artifact observation time belongs to its first import, not every refresh.
    if not store.rows('SELECT id FROM artifacts WHERE id=?', (ident,)):
        store.record('artifact', {'id': ident, 'kind': kind, 'source_path': str(path),
            'fingerprint': fingerprint, 'observed_at': utc_now(), 'summary': summary or None}, producer='collector')
    return ident


def _plugin_name(path):
    for parent in list(path.parents)[:5]:
        for file in [parent / '.claude-plugin/plugin.json', parent / 'plugin.json']:
            if file.is_file():
                try: return str(json.loads(_text(file)).get('name') or '')
                except (ValueError, OSError): pass
    return ''


def resolve_capability(store, root, owner):
    rows = store.rows('SELECT id FROM capabilities WHERE name=? ORDER BY active DESC,id', (owner,))
    if len(rows) == 1: return rows[0]['id']
    for folder in (owner, owner.replace(':', '/')):
        file = Path(root) / 'skills' / folder / 'SKILL.md'
        if file.is_file():
            ident = stable_id('capability', str(file.resolve()))
            if store.rows('SELECT id FROM capabilities WHERE id=?', (ident,)): return ident
    ident = stable_id('capability', 'owner:' + owner)
    if not store.rows('SELECT id FROM capabilities WHERE id=?', (ident,)):
        store.record('capability', {'id': ident, 'kind': 'skill', 'name': owner,
            'description': 'Referenced capability; source not resolved by this inventory.',
            'source_path': 'unresolved://' + owner, 'revision': 'unknown',
            'discovered_at': utc_now(), 'group_name': 'unresolved', 'active': False}, producer='collector')
    return ident


class Registry:
    def __init__(self, store, root):
        self.store, self.root, self.aliases = store, Path(root), {}

    def resolve(self, name, source=None):
        names = self.aliases.get(name, set())
        if len(names) == 1: return next(iter(names))
        return resolve_capability(self.store, self.root, name)

    def alias(self, name, ident):
        if name: self.aliases.setdefault(name, set()).add(ident)


def inventory(store, root, home, project_root=None):
    root, home = Path(root), Path(home); registry = Registry(store, root)
    roots = [(root / 'skills', 'claude'), (home / '.claude/skills', 'claude'),
             (root / 'plugins', 'claude'), (home / '.claude/plugins/local-marketplace', 'claude'),
             (home / '.claude/plugins/cache', 'claude'), (home / '.agents/skills', 'codex'),
             (home / '.codex/skills', 'codex'), (home / '.codex/plugins/cache', 'codex')]
    if project_root:
        project_root = Path(project_root)
        roots += [(project_root / '.agents/skills', 'codex'), (project_root / '.claude/skills', 'claude')]
    seen = {}; sources = {}; warnings = []; selected_groups = {}
    manifest = root / 'docs/codex-linked-skills.json'
    if manifest.is_file():
        try:
            for entry in json.loads(_text(manifest)).get('entries', []):
                selected_groups[str((Path(entry['source']) / 'SKILL.md').resolve())] = entry.get('group', 'ungrouped')
        except (KeyError, OSError, ValueError, TypeError) as exc: warnings.append(f'Linked manifest: {exc}')
    for directory, host in roots:
        for alias in _walk(directory):
            canonical = alias.resolve()
            try:
                text = sources.setdefault(canonical, _text(canonical))
                fields = _fields(text); declared = fields.get('name') or canonical.parent.name
                plugin = _plugin_name(canonical) if '/plugins/' in str(canonical) else ''
                name = f'{plugin}:{declared}' if plugin and ':' not in declared else declared
                ident = stable_id('capability', str(canonical))
                if ident not in seen:
                    old = store.rows('SELECT discovered_at FROM capabilities WHERE id=?', (ident,))
                    store.record('capability', {'id': ident, 'kind': 'skill', 'name': name,
                        'description': fields.get('description') or 'No description found.',
                        'source_path': str(canonical), 'revision': hashlib.sha256(text.encode()).hexdigest(),
                        'discovered_at': old[0]['discovered_at'] if old else utc_now(),
                        'group_name': str(selected_groups.get(str(canonical)) or fields.get('bay') or 'ungrouped')}, producer='collector')
                    seen[ident] = canonical
                for value in (name, declared, alias.parent.name, canonical.parent.name): registry.alias(value, ident)
                store.record('availability', {'capability_id': ident, 'host': host, 'role': 'unknown',
                    'path': str(alias), 'status': 'discovered', 'observed_at': utc_now(),
                    'evidence': 'Folder discovered; execution compatibility and active host registration are not certified.'}, producer='collector')
            except (OSError, ValueError) as exc: warnings.append(str(exc))
    # Custom role instructions and hook scripts describe capabilities, not invocation evidence.
    for directory, kind, patterns in [(root / 'agents', 'agent', ('*.md',)),
                                      (home / '.claude/agents', 'agent', ('*.md',)),
                                      (root / 'hooks', 'hook', ('*.sh',))]:
        if not directory.is_dir(): continue
        for pattern in patterns:
            for file in sorted(directory.glob(pattern)):
                canonical = file.resolve(); ident = stable_id('capability', str(canonical))
                if ident in seen: continue
                try: text = _text(canonical)
                except (OSError, ValueError) as exc: warnings.append(str(exc)); continue
                fields = _fields(text) if kind == 'agent' else {}
                name = fields.get('name') or file.stem
                old = store.rows('SELECT discovered_at FROM capabilities WHERE id=?', (ident,))
                store.record('capability', {'id': ident, 'kind': kind, 'name': name,
                    'description': fields.get('description') or f'{kind} instruction/script source.',
                    'source_path': str(canonical), 'revision': hashlib.sha256(text.encode()).hexdigest(),
                    'discovered_at': old[0]['discovered_at'] if old else utc_now(),
                    'group_name': 'roles' if kind == 'agent' else 'hooks'}, producer='collector')
                seen[ident] = canonical; sources[canonical] = text; registry.alias(name, ident)
    for ident, file in seen.items():
        text = sources.get(file, ''); references = []
        for name, candidates in registry.aliases.items():
            if len(candidates) != 1: continue
            target = next(iter(candidates))
            if target == ident: continue
            if re.search(r'(?:/' + re.escape(name) + r'\b|skills/' + re.escape(name) + r'\b|subagent_type\s*[:=]\s*["\']' + re.escape(name) + r'["\'])', text):
                references.append({'target_id': target, 'evidence': str(file) + ' (static reference, not observed execution)'})
        store.replace_references(ident, references)
    # Historical metadata remains queryable, but missing paths must not advertise current availability.
    for previous in store.rows('SELECT * FROM capabilities WHERE active=1'):
        if previous['source_path'].startswith('unresolved://') or Path(previous['source_path']).is_file(): continue
        payload = {k: previous[k] for k in ['id', 'kind', 'name', 'description', 'source_path', 'revision', 'discovered_at', 'group_name']}
        payload['active'] = False
        store.record('capability', payload, producer='collector')
    store.clear_inactive_dependencies()
    for previous in store.rows('SELECT * FROM availability'):
        if Path(previous['path']).exists(): continue
        payload = {k: previous[k] for k in ['capability_id', 'host', 'role', 'path']}
        payload.update(status='unknown', observed_at=utc_now(), evidence='Previously discovered path is now absent. Current availability is unknown.')
        store.record('availability', payload, producer='collector')
    return registry, {'capabilities': len(seen), 'warnings': warnings}


def _date(value):
    if not isinstance(value, str): return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed
    except ValueError: return None


def _in_scope(cwd, org, project_root=None):
    if not cwd: return False
    if org == 'all': return True
    if project_root:
        try:
            if Path(cwd).resolve().is_relative_to(Path(project_root).resolve()): return True
        except (OSError, ValueError): pass
    return ORG_TOKEN.get(org, org) in Path(cwd).parts


def _read_skill_paths(command):
    """Recognize literal simple read commands only; complex shell stays uncounted."""
    if not isinstance(command, str) or re.search(r"[;|&<>`\n]|\$\(", command): return []
    try: tokens = shlex.split(command, comments=True)
    except ValueError: return []
    if not tokens: return []
    executable = Path(tokens[0]).name
    if executable not in {'cat', 'head', 'tail', 'sed'}: return []
    paths = []; skip_next = False; need_script = executable == 'sed'
    for token in tokens[1:]:
        if skip_next: skip_next = False; continue
        if executable == 'sed' and token in {'-e', '--expression', '-f', '--file'}:
            skip_next = True; need_script = False; continue
        if executable in {'head', 'tail'} and token in {'-n', '-c', '--lines', '--bytes'}:
            skip_next = True; continue
        if token.startswith('-'):
            if executable == 'sed' and token.startswith(('-e', '-f')): need_script = False
            continue
        if need_script: need_script = False; continue
        if token.endswith(('/SKILL.md', '/skill.md')): paths.append(token)
    return paths


def _code_mode_commands(code):
    """Read literal exec_command args outside strings/comments, with no code execution.

    Conditional/loop/function-bearing programs are intentionally unsupported: a
    literal call in those programs does not establish that the call executed.
    """
    if not isinstance(code, str): return []
    token_rx = re.compile(r'(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)|(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)|(?P<identifier>[A-Za-z_$][\w$]*)|(?P<punct>\S)')
    tokens = []
    for match in token_rx.finditer(code):
        if match.lastgroup == 'comment': continue
        token = match.group()
        if match.lastgroup == 'string':
            if token.startswith('`'):
                value = None if '${' in token else token[1:-1].replace('\\`', '`')
            else:
                try: value = ast.literal_eval(token)
                except (ValueError, SyntaxError): value = None
            tokens.append(('string', value))
        else: tokens.append((match.lastgroup, token))
    values = [value for kind, value in tokens if kind != 'string']
    if any(v in {'if', 'for', 'while', 'switch', 'function', 'return', '?'} for v in values): return []
    if any(values[i:i+2] in [['=', '>'], ['&', '&'], ['|', '|']] for i in range(len(values)-1)): return []
    commands = []
    for i in range(len(tokens)-7):
        if tokens[i:i+5] != [('identifier', 'tools'), ('punct', '.'), ('identifier', 'exec_command'), ('punct', '('), ('punct', '{')]: continue
        depth = 1
        for j in range(i+5, len(tokens)-2):
            if tokens[j] == ('punct', '{'): depth += 1
            if tokens[j] == ('punct', '}'):
                depth -= 1
                if depth == 0: break
            if depth == 1 and tokens[j][1] == 'cmd' and tokens[j+1] == ('punct', ':') and tokens[j+2][0] == 'string':
                command = tokens[j+2][1]
                complete_literal = j + 3 < len(tokens) and tokens[j+3] in [('punct', ','), ('punct', '}')]
                if isinstance(command, str) and complete_literal: commands.append(command)
                break
    return commands


def _successful_read_receipt(output, expected=1):
    """Require explicit successful process statuses from structured tool receipts.

    Unstructured stdout is not searched for success phrases or exit-code text.
    For code-mode batches every observed process receipt must be successful.
    """
    statuses = []
    def visit(value):
        if isinstance(value, str):
            try: visit(json.loads(value))
            except (ValueError, TypeError): pass
        elif isinstance(value, list):
            for item in value: visit(item)
        elif isinstance(value, dict):
            if value.get('isError') is True or value.get('is_error') is True or value.get('error'):
                statuses.append(None)
            if 'exit_code' in value:
                code = value['exit_code']
                output_text = value.get('output')
                nonempty_read = isinstance(output_text, str) and bool(output_text.strip())
                statuses.append(code if isinstance(code, int) and not isinstance(code, bool) and (code != 0 or nonempty_read) else None)
                return  # Never interpret a command's stdout as another process receipt.
            for key in ['content', 'structuredContent']:
                if key in value: visit(value[key])
            if value.get('type') == 'text': visit(value.get('text'))
    visit(output)
    return len(statuses) >= expected and all(status == 0 for status in statuses)


def collect_activity(store, registry, home, org='klever', project_root=None, days=90):
    home = Path(home); now = dt.datetime.now(dt.timezone.utc); cutoff = now - dt.timedelta(days=days)
    counts = {'claude': 0, 'codex': 0}; warnings = []
    for host, directory in [('claude', home / '.claude/projects'), ('codex', home / '.codex/sessions')]:
        files = []; byte_budget = MAX_ACTIVITY_BYTES
        if directory.is_dir():
            if host == 'claude' and org != 'all':
                token = ORG_TOKEN.get(org, org)
                for project in sorted(directory.iterdir()):
                    if project.is_dir() and token in project.name: files.extend(project.rglob('*.jsonl'))
            else: files = list(directory.rglob('*.jsonl'))
        partial = False; scanned = 0; malformed = 0; skipped = 0; skipped_bytes = 0; scanned_bytes = 0; unverified_reads = 0
        for file in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True):
            # Old file mtime may safely skip immutable history; event dates still decide counting.
            try:
                stat = file.stat()
                if stat.st_mtime < cutoff.timestamp(): continue
                if stat.st_size > 128 * 1024 * 1024 or stat.st_size > byte_budget:
                    partial = True; skipped += 1; skipped_bytes += stat.st_size; continue
                byte_budget -= stat.st_size; scanned_bytes += stat.st_size
                cwd = ''; session_id = file.stem; role = 'unknown'; pending = []; pending_reads = {}
                found = []
                with file.open(encoding='utf-8', errors='replace') as fh:
                    for lineno, line in enumerate(fh, 1):
                        if len(line) > MAX_TEXT: partial = True; continue
                        try: row = json.loads(line)
                        except json.JSONDecodeError: malformed += 1; continue
                        payload = row.get('payload', {})
                        if host == 'codex' and row.get('type') == 'session_meta':
                            cwd = payload.get('cwd', ''); session_id = payload.get('session_id') or payload.get('id') or session_id
                            role = payload.get('agent_path') or payload.get('agent_nickname') or 'main'
                        if row.get('cwd'): cwd = row['cwd']
                        if host == 'codex' and row.get('type') == 'turn_context': cwd = payload.get('cwd') or cwd
                        if not _in_scope(cwd, org, project_root): continue
                        timestamp = row.get('timestamp'); at = _date(timestamp)
                        if at is None or at < cutoff or at > now: continue
                        session_id = row.get('sessionId') or session_id
                        source_ref = row.get('uuid') or row.get('ordinal') or lineno
                        if host == 'claude':
                            role = row.get('agentName') or row.get('agentType') or ('unknown' if row.get('isSidechain') else 'main')
                            message = row.get('message', {})
                            content = message.get('content', [])
                            if row.get('type') == 'user' and not row.get('isMeta') and isinstance(content, str):
                                # Real slash commands only at the start, or native command-name wrappers.
                                found.extend((n, t, ref, r, 'invoked') for n, t, ref, r in pending)
                                pending = []
                                m = re.match(r'^\s*/([\w:-]+)(?:\s|$)', content)
                                if not m and content.lstrip().startswith(('<command-name>', '<command-message>')):
                                    m = re.search(r'<command-name>/?([\w:-]+)</command-name>', content)
                                if m and m.group(1) in registry.aliases:
                                    pending.append((m.group(1), timestamp, source_ref, role))
                            if row.get('type') == 'assistant' and isinstance(content, list):
                                for block in content:
                                    if block.get('type') != 'tool_use' or block.get('name') != 'Skill': continue
                                    name = block.get('input', {}).get('skill')
                                    if not isinstance(name, str): continue
                                    # Prefer actual Skill call to a matching immediately preceding request.
                                    pending = [p for p in pending if registry.resolve(p[0]) != registry.resolve(name)]
                                    found.append((name, timestamp, block.get('id') or source_ref, role, 'invoked'))
                        elif row.get('type') == 'response_item' and payload.get('type') in ('function_call', 'custom_tool_call'):
                            name = str(payload.get('name', '')); raw = payload.get('arguments', '{}')
                            try: args = json.loads(raw) if isinstance(raw, str) else raw
                            except (ValueError, TypeError): continue
                            paths = _read_skill_paths(args.get('cmd', '')) if name.endswith('exec_command') else []
                            expected_receipts = 1
                            if payload.get('type') == 'custom_tool_call' and name in {'exec', 'functions.exec', 'functions__exec'}:
                                commands = _code_mode_commands(payload.get('input'))
                                paths += [p for command in commands for p in _read_skill_paths(command)]
                                expected_receipts = len(commands)
                            if name.endswith(('read_file', 'Read')):
                                candidate = args.get('path') or args.get('file_path')
                                if isinstance(candidate, str) and candidate.endswith('/SKILL.md'): paths.append(candidate)
                            for path in paths:
                                absolute = Path(path.replace('~', str(home), 1))
                                if not absolute.is_absolute(): absolute = Path(cwd) / absolute
                                resolved = absolute.resolve(); ident = stable_id('capability', str(resolved))
                                if not store.rows('SELECT id FROM capabilities WHERE id=?', (ident,)): continue
                                call_id = payload.get('call_id')
                                if call_id:
                                    entry = pending_reads.setdefault(call_id, {'events': [], 'expected': expected_receipts})
                                    entry['events'].append((ident, timestamp, call_id, role, 'loaded'))
                        elif row.get('type') == 'response_item' and payload.get('type') in ('function_call_output', 'custom_tool_call_output'):
                            entry = pending_reads.pop(payload.get('call_id'), None)
                            if entry:
                                if _successful_read_receipt(payload.get('output'), entry['expected']): found.extend(entry['events'])
                                else: unverified_reads += len(entry['events']); partial = True
                unverified_reads += sum(len(entry['events']) for entry in pending_reads.values())
                found.extend((n, t, ref, r, 'invoked') for n, t, ref, r in pending)
                for name, timestamp, ref, event_role, signal in found:
                    ident = name if signal == 'loaded' else registry.resolve(name)
                    event_id = stable_id('usage', host, str(file.resolve()), ref, ident, signal)
                    store.record('usage', {'id': event_id, 'capability_id': ident, 'host': host,
                        'role': str(event_role), 'session_id': str(session_id), 'occurred_at': timestamp,
                        'signal': signal, 'source_path': str(file.resolve()), 'source_ref': str(ref)}, producer='collector')
                    counts[host] += 1
                scanned += 1
            except (OSError, ValueError) as exc: warnings.append(str(exc)); partial = True
        if malformed: partial = True; warnings.append(f'{host}: {malformed} malformed JSONL rows skipped')
        status = 'unavailable' if not files else 'partial'  # Supported signals are never complete behavioral coverage.
        detail = f'{scanned} transcripts / {scanned_bytes} bytes scanned; {skipped} files / {skipped_bytes} bytes skipped by per-host read limits. Structured signals only; skill reads are loads, not completed executions.'
        if partial: detail += ' Read budget, unsupported row or source errors limit coverage.'
        if host == 'codex': detail += f' {unverified_reads} read requests lacked a verifiable successful receipt. Code-mode supports unconditional literal exec_command reads only; dynamic/conditional code and inherited/compacted content are not counted.'
        store.record('coverage', {'id': stable_id('coverage', host, org, 'activity'), 'source': str(directory),
            'host': host, 'scope': org, 'since': cutoff.isoformat(), 'until': now.isoformat(),
            'observed_at': utc_now(), 'status': status, 'detail': detail}, producer='collector')
    return {'usage_signals': counts, 'warnings': warnings}


def _manifest_suites(path):
    suites = []; current = None; in_suites = False
    for line in _text(path).splitlines():
        if re.match(r'^suites:\s*$', line): in_suites = True; continue
        if re.match(r'^[A-Za-z_][\w-]*:', line): in_suites = False
        if not in_suites: continue
        m = re.match(r'^\s*- target:\s*(.+)$', line)
        if m:
            current = {'target': _scalar(m.group(1))}; suites.append(current)
        elif current:
            m = re.match(r'^\s+(owner_skill|layer|runner|last_green):\s*(.*)$', line)
            if m: current[m.group(1)] = _scalar(m.group(2))
    return suites


def _eval_artifacts(store, root):
    """Index bounded existing eval evidence without guessing a report's verdict."""
    count = 0; warnings = []; seen = set()
    bases = [root / 'evals/reports']
    skills = root / 'skills'
    if skills.is_dir():
        for skill in sorted(skills.iterdir()):
            if not skill.is_dir() or skill.name in EXCLUDE: continue
            bases += [skill / 'evals', skill / 'reports']
            bases += [p for p in skill.iterdir() if p.is_dir() and 'workspace' in p.name]
    known = {'grading.json', 'benchmark.json', 'timing.json', 'eval_results.json',
             'summary.json', 'results.json', 'evals.json', 'eval_metadata.json'}
    for base in bases:
        if not base.is_dir(): continue
        for directory, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in {'fixtures', 'files', 'node_modules', '.git', '__pycache__'})
            for filename in sorted(files):
                if filename not in known and not (filename.endswith('.md') and ('report' in filename or 'review' in filename or base.name == 'reports')): continue
                file = (Path(directory) / filename).resolve()
                if file in seen: continue
                seen.add(file)
                try:
                    if file.stat().st_size > MAX_TEXT:
                        warnings.append(f'Eval artifact exceeds bounded metadata import: {file}')
                        continue
                    kind = 'eval-definition' if filename == 'evals.json' else 'eval-artifact'
                    _artifact(store, file, kind, 'Original evaluation artifact. Verdict/metrics remain owned by its source process.')
                    count += 1
                except (OSError, ValueError) as exc: warnings.append(str(exc))
    return count, warnings


def ingest_evals(store, registry, root):
    root = Path(root); manifest = root / 'evals/manifest.yaml'; suites = {}; warnings = []; count = 0
    if manifest.is_file():
        _artifact(store, manifest, 'eval-manifest', 'Suite registry; last_green is not a current-revision execution result.')
        suites = {str(s['target']): s for s in _manifest_suites(manifest)}
        for target, suite in suites.items():
            ident = registry.resolve(str(suite.get('owner_skill') or target.split('/')[0]))
            store.record('eval_suite', {'id': stable_id('eval-suite', str(manifest.resolve()), target),
                'suite_id': target, 'capability_id': ident, 'layer': str(suite.get('layer') or 'unknown'),
                'source_path': str(manifest.resolve()), 'observed_at': utc_now(),
                'runner': suite.get('runner') or None, 'last_green': suite.get('last_green') or None}, producer='collector')
    artifact_count, artifact_warnings = _eval_artifacts(store, root)
    warnings.extend(artifact_warnings)
    reportdir = root / 'evals/reports'
    for report in sorted(reportdir.glob('*.md')) if reportdir.is_dir() else []:
        try: text = _text(report)
        except (ValueError, OSError) as exc: warnings.append(str(exc)); continue
        _artifact(store, report, 'eval-report')
        occurred = None
        for lineno, line in enumerate(text.splitlines(), 1):
            stamp = re.search(r'Layer A sweep\s*[—-]\s*(\d{4}-\d{2}-\d{2})', line)
            if stamp: occurred = stamp.group(1)
            m = re.match(r'^## (PASS|FAIL)\s*[—-]\s*(.+?)\s*\(exit\s+([^)]*)\)', line)
            if not m or not occurred: continue
            verdict, target, code = m.groups(); suite = suites.get(target, {})
            ident = registry.resolve(str(suite.get('owner_skill') or target.split('/')[0]))
            assertion_hash = hashlib.sha256(line.encode()).hexdigest()
            source_ref = f'line:{lineno}; assertion_sha256:{assertion_hash}'
            if store.rows('SELECT id FROM eval_runs WHERE source_path=? AND source_ref=?', (str(report.resolve()), source_ref)):
                count += 1
                continue
            store.record('eval', {'id': stable_id('eval', str(report.resolve()), lineno, target, occurred, line),
                'suite_id': target, 'capability_id': ident, 'occurred_at': occurred,
                'outcome': 'pass' if verdict == 'PASS' else 'fail', 'source_path': str(report.resolve()),
                'source_ref': source_ref, 'layer': str(suite.get('layer') or 'unknown'),
                'summary': f'Reported {verdict}; runner exit {code}. Tested skill revision and host unrecorded.'}, producer='eval-runner')
            count += 1
    store.record('coverage', {'id': stable_id('coverage', 'evals', str(root)), 'source': str(reportdir),
        'host': 'shared', 'scope': 'harness evals', 'observed_at': utc_now(),
        'status': 'partial' if manifest.is_file() else 'unavailable',
        'detail': f'{len(suites)} suite definitions referenced; {count} supported sweep results imported; {artifact_count} original artifacts indexed. Other report shapes remain linked artifacts. No evaluation was executed.'}, producer='collector')
    return {'eval_results': count, 'eval_suites': len(suites), 'eval_artifacts': artifact_count, 'warnings': warnings}


def ingest_factories(store, registry, root, org='klever'):
    root = Path(root); count = 0; warnings = []
    for name in ['dark-factory', 'service-factory']:
        runs = root / 'skills' / name / 'runs'
        for path in sorted(runs.glob('run-*.yaml')) if runs.is_dir() else []:
            try: text = _text(path)
            except (ValueError, OSError) as exc: warnings.append(str(exc)); continue
            fields = _fields(text)
            scope = fields.get('ticket_folder', '')
            if scope and not _in_scope(scope, org): continue
            # Both factory families are Klever-scoped in their source contracts.
            if org != 'klever' and not scope: continue
            date = fields.get('date'); status = fields.get('terminal_status') or fields.get('terminal')
            _artifact(store, path, 'factory-run')
            fingerprint = _fingerprint(path)
            if not date or not status: continue
            ident = registry.resolve(name)
            summary = fields.get('halt_point') or fields.get('title') or 'Legacy factory outcome; see source evidence.'
            store.record('outcome', {'id': stable_id('outcome', str(path.resolve()), fingerprint),
                'capability_id': ident, 'occurred_at': str(date), 'status': str(status),
                'source_path': str(path.resolve()), 'source_ref': 'terminal_status; source_sha256:' + fingerprint,
                'summary': str(summary)[:2000]}, producer='collector')
            count += 1
            # Only explicit top-level scalar red flag list items are recognized without YAML dependencies.
            in_flags = False
            for index, line in enumerate(text.splitlines(), 1):
                if re.match(r'^red_flags:\s*$', line): in_flags = True; continue
                if in_flags and line and not line[0].isspace(): in_flags = False
                m = re.match(r'^  -\s+(?:title:\s*)?(.+)$', line) if in_flags else None
                if not m: continue
                summary = _scalar(m.group(1))
                if not summary or summary in ('>', '|'): continue
                store.record('friction', {'id': stable_id('friction', str(path.resolve()), str(date), 'red_flags', str(summary)),
                    'capability_id': ident, 'host': 'unknown', 'role': 'factory-retro',
                    'session_id': str(fields.get('run_id') or path.stem), 'occurred_at': str(date),
                    'summary': str(summary), 'impact': 'Agent-reported factory red flag; see original run.',
                    'evidence': f'{path.resolve()}#red_flags'}, producer='agent')
    store.record('coverage', {'id': stable_id('coverage', 'factories', org), 'source': str(root / 'skills'),
        'host': 'shared', 'scope': org, 'observed_at': utc_now(), 'status': 'partial',
        'detail': f'{count} dated terminal outcomes imported. Host, tested revision and nested retro fields may be unknown; no factory executed.'}, producer='collector')
    return {'factory_outcomes': count, 'warnings': warnings}


def ingest_artifact(store, kind, path, records=None):
    """Preserve a producer's own output and optional already-validated domain records."""
    path = Path(path); _artifact(store, path, kind)
    written = 0
    for record in records or []:
        record = dict(record); domain = record.pop('kind'); payload = record.pop('payload', record)
        producer = 'eval-runner' if domain == 'eval' else 'collector'
        written += bool(store.record(domain, payload, producer=producer))
    return written


def refresh(store, root, home, org='klever', project_root=None, days=90):
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 3650:
        raise ValueError('days must be an integer from 1 to 3650')
    root, home = Path(root), Path(home)
    if project_root is None and org == 'klever':
        candidate = home / 'Developer/grp-beklever-com/project-management'
        if candidate.is_dir(): project_root = candidate
    registry, stats = inventory(store, root, home, project_root)
    for result in [collect_activity(store, registry, home, org, project_root, days),
                   ingest_evals(store, registry, root), ingest_factories(store, registry, root, org)]:
        stats['warnings'].extend(result.pop('warnings', [])); stats.update(result)
    # Legacy estimates/references stay original report artifacts, not fabricated dated executions.
    for folder in [home / '.claude/skill-proposals', root / 'claude-home/skill-proposals']:
        for name in ['USAGE-SCAN.md', 'RETIREMENT-CANDIDATES.md', 'TAX-REPORT.md']:
            path = folder / name
            if path.is_file(): _artifact(store, path, 'legacy-report', 'Historical report; counts are not verified executions.')
    return stats

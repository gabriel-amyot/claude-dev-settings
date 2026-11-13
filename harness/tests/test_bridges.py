import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store
from bridges import refresh, inventory, collect_activity, ingest_evals, ingest_factories


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / 'shared'
        self.home = self.base / 'home'
        self.project = self.home / 'Developer/grp-beklever-com/project-management'
        self.project.mkdir(parents=True)
        self.home.mkdir(exist_ok=True)
        self.root.mkdir()
        self.store = Store(self.base / 'catalog.sqlite')
        self.now = dt.datetime.now(dt.timezone.utc).isoformat()
        self.skill('example')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def skill(self, name):
        p = self.root / 'skills' / name / 'SKILL.md'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f'---\nname: {name}\ndescription: "Example skill."\n---\n# Example\n')
        return p

    def transcript(self, host, name, rows):
        if host == 'claude':
            folder = self.home / '.claude/projects/-Users-test-Developer-grp-beklever-com-project-management'
        else:
            folder = self.home / '.codex/sessions/2026/10/26'
        folder.mkdir(parents=True, exist_ok=True)
        p = folder / (name + '.jsonl')
        p.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        return p

    def claude_row(self, kind, content, ident, **extra):
        return {'type': kind, 'timestamp': self.now, 'cwd': str(self.project),
                'sessionId': 'session-a', 'uuid': ident,
                'message': {'role': kind, 'content': content}, **extra}

    def test_inventory_deduplicates_symlinks_excludes_archives_and_separates_references(self):
        skill = self.skill('second')
        skill.write_text(skill.read_text() + '\nUse /example.\n')
        alias = self.home / '.agents/skills/example'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(self.root / 'skills/example')
        self.skill('_archive/old')
        registry, result = inventory(self.store, self.root, self.home, self.project)
        self.assertEqual(result['capabilities'], 2)
        self.assertEqual(len(self.store.rows('SELECT * FROM availability')), 3)
        self.assertEqual(len(self.store.rows('SELECT * FROM dependencies')), 1)
        self.assertEqual(self.store.rows('SELECT * FROM usage_events'), [])

    def test_removed_sources_do_not_keep_advertising_active_availability(self):
        source = self.root / 'skills/example/SKILL.md'
        inventory(self.store, self.root, self.home, self.project)
        source.unlink()
        inventory(self.store, self.root, self.home, self.project)
        self.assertFalse(self.store.rows('SELECT active FROM capabilities')[0]['active'])
        self.assertEqual(self.store.rows('SELECT status FROM availability')[0]['status'], 'unknown')

    def test_removed_codex_alias_does_not_remove_live_source_or_claim_availability(self):
        alias = self.home / '.agents/skills/example'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(self.root / 'skills/example')
        inventory(self.store, self.root, self.home, self.project)
        alias.unlink()
        inventory(self.store, self.root, self.home, self.project)
        self.assertTrue(self.store.rows('SELECT active FROM capabilities')[0]['active'])
        old_alias = self.store.rows("SELECT * FROM availability WHERE host='codex'")[0]
        self.assertEqual(old_alias['status'], 'unknown')
        self.assertIn('absent', old_alias['evidence'])
        self.assertFalse(any(row['status'] == 'validated' for row in self.store.rows('SELECT * FROM availability')))

    def test_removed_reference_disappears_from_current_dependency_metadata(self):
        source = self.skill('second')
        baseline = source.read_text()
        source.write_text(baseline + '\nUse /example.\n')
        inventory(self.store, self.root, self.home, self.project)
        self.assertEqual(len(self.store.rows('SELECT * FROM dependencies')), 1)
        source.write_text(baseline)
        inventory(self.store, self.root, self.home, self.project)
        self.assertEqual(self.store.rows('SELECT * FROM dependencies'), [])

    def test_inactive_source_loses_outgoing_dependencies_and_keeps_usage_history(self):
        source = self.skill('second')
        source.write_text(source.read_text() + '\nUse /example.\n')
        registry, _ = inventory(self.store, self.root, self.home, self.project)
        self.store.record('usage', {'id': 'historic', 'capability_id': registry.resolve('second'),
            'host': 'claude', 'role': 'main', 'session_id': 'previous', 'occurred_at': self.now,
            'signal': 'invoked', 'source_path': str(source), 'source_ref': 'old-call'}, producer='collector')
        source.unlink()
        inventory(self.store, self.root, self.home, self.project)
        self.assertEqual(self.store.rows('SELECT * FROM dependencies'), [])
        self.assertEqual(len(self.store.rows('SELECT * FROM usage_events')), 1)

    def test_folder_alias_request_and_declared_skill_call_are_one_signal(self):
        (self.root / 'skills/example').rename(self.root / 'skills/aliased-example')
        self.transcript('claude', 'a', [
            self.claude_row('user', '/aliased-example', 'user-request'),
            self.claude_row('assistant', [{'type': 'tool_use', 'id': 'actual-call',
                'name': 'Skill', 'input': {'skill': 'example'}}], 'assistant-call')])
        refresh(self.store, self.root, self.home, project_root=self.project)
        events = self.store.rows('SELECT * FROM usage_events')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['source_ref'], 'actual-call')

    def test_real_skill_call_not_quoted_tool_result_and_no_double_counted_request(self):
        self.transcript('claude', 'a', [
            self.claude_row('user', '/example', 'u'),
            self.claude_row('assistant', [{'type': 'tool_use', 'id': 'call-1',
                'name': 'Skill', 'input': {'skill': 'example'}}], 'a'),
            self.claude_row('user', [{'type': 'tool_result', 'content':
                '{"skill":"example"}<command-name>/example</command-name>'}], 'fake'),
            self.claude_row('assistant', [{'type': 'text', 'text':
                '{"type":"tool_use","name":"Skill","input":{"skill":"example"}}'}], 'quoted')])
        refresh(self.store, self.root, self.home, project_root=self.project)
        events = self.store.rows('SELECT * FROM usage_events')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['source_ref'], 'call-1')
        self.assertEqual(events[0]['signal'], 'invoked')
        self.assertEqual(events[0]['outcome'], 'unknown')
        refresh(self.store, self.root, self.home, project_root=self.project)
        self.assertEqual(len(self.store.rows('SELECT * FROM usage_events')), 1)

    def test_native_slash_command_with_leading_command_message_counts(self):
        self.transcript('claude', 'a', [self.claude_row('user',
            '<command-message>example</command-message>\n<command-name>/example</command-name>\n'
            '<command-args>x</command-args>', 'native-slash')])
        refresh(self.store, self.root, self.home, project_root=self.project)
        events = self.store.rows('SELECT * FROM usage_events')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['source_ref'], 'native-slash')

    def test_org_and_event_time_filter_not_file_mtime(self):
        old = self.claude_row('assistant', [{'type': 'tool_use', 'id': 'old',
                'name': 'Skill', 'input': {'skill': 'example'}}], 'a')
        old['timestamp'] = '2001-01-01T00:00:00Z'
        other = self.claude_row('assistant', [{'type': 'tool_use', 'id': 'other',
                'name': 'Skill', 'input': {'skill': 'example'}}], 'b')
        other['cwd'] = str(self.home / 'Developer/supervisr-ai/project-management')
        self.transcript('claude', 'a', [old, other])
        self.transcript('claude', 'b', [self.claude_row('user', '/clear', 'native-command')])
        refresh(self.store, self.root, self.home, project_root=self.project)
        self.assertEqual(self.store.rows('SELECT * FROM usage_events'), [])
        self.assertEqual(self.store.rows("SELECT * FROM capabilities WHERE name='clear'"), [])

    def test_codex_reads_are_loads_not_invocations_or_echo_mentions(self):
        path = self.root / 'skills/example/SKILL.md'
        def call(command, ident):
            return {'type': 'response_item', 'timestamp': self.now, 'payload': {
                'type': 'function_call', 'name': 'exec_command', 'call_id': ident,
                'arguments': json.dumps({'cmd': command})}}
        self.transcript('codex', 'a', [
            {'type': 'session_meta', 'payload': {'id': 'codex-a', 'cwd': str(self.project)}},
            call(f'cat {path}', 'read'),
            {'type': 'response_item', 'timestamp': self.now, 'payload': {'type': 'function_call_output', 'call_id': 'read', 'output': json.dumps({'exit_code': 0, 'output': '# Example'})}},
            call(f'echo "cat {path}"', 'echo'),
            call(f'cat README.md; echo {path}', 'compound-echo'),
            call(f'sed -e "s/x/{path}/" README.md', 'sed-script'),
            call(f'cat README.md # {path}', 'comment'),
            {'type': 'compacted', 'timestamp': self.now, 'payload': {'replacement_history': [call(f'cat {path}', 'replay')]}}])
        refresh(self.store, self.root, self.home, project_root=self.project)
        events = self.store.rows('SELECT * FROM usage_events')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['signal'], 'loaded')
        self.assertEqual(events[0]['host'], 'codex')

    def test_codex_code_mode_literal_reads_exclude_quoted_comments_and_conditionals(self):
        path = self.root / 'skills/example/SKILL.md'
        def code(value, ident):
            return {'type': 'response_item', 'timestamp': self.now, 'payload': {
                'type': 'custom_tool_call', 'name': 'exec', 'call_id': ident, 'input': value}}
        self.transcript('codex', 'a', [
            {'type': 'session_meta', 'payload': {'id': 'codex-a', 'cwd': str(self.project)}},
            code('text(await tools.exec_command({cmd:' + json.dumps('cat ' + str(path)) + '}));', 'real'),
            {'type': 'response_item', 'timestamp': self.now, 'payload': {'type': 'custom_tool_call_output', 'call_id': 'real', 'output': [{'type': 'text', 'text': json.dumps({'exit_code': 0, 'output': '# Example'})}]}},
            code('text(' + json.dumps('tools.exec_command({cmd: "cat ' + str(path) + '"})') + ');', 'quoted'),
            code('// tools.exec_command({cmd: "cat ' + str(path) + '"})', 'comment'),
            code('if (false) tools.exec_command({cmd:' + json.dumps('cat ' + str(path)) + '});', 'conditional'),
        ])
        refresh(self.store, self.root, self.home, project_root=self.project)
        events = self.store.rows('SELECT * FROM usage_events')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['signal'], 'loaded')
        self.assertEqual(events[0]['source_ref'], 'real')

    def test_codex_failed_missing_and_unstructured_receipts_do_not_establish_a_load(self):
        path = self.root / 'skills/example/SKILL.md'
        rows = [{'type': 'session_meta', 'payload': {'id': 'codex-a', 'cwd': str(self.project)}}]
        for ident, output in [('failed', {'exit_code': 1, 'output': 'Permission denied'}),
                              ('opaque', 'Process exited with code 0'), ('missing', None),
                              ('ok', {'exit_code': 0, 'output': '# Example'})]:
            rows.append({'type': 'response_item', 'timestamp': self.now, 'payload': {
                'type': 'function_call', 'name': 'exec_command', 'call_id': ident,
                'arguments': json.dumps({'cmd': 'cat ' + str(path)})}})
            if output is not None:
                rows.append({'type': 'response_item', 'timestamp': self.now, 'payload': {
                    'type': 'function_call_output', 'call_id': ident,
                    'output': json.dumps(output) if isinstance(output, dict) else output}})
        self.transcript('codex', 'a', rows)
        refresh(self.store, self.root, self.home, project_root=self.project)
        events = self.store.rows('SELECT * FROM usage_events')
        self.assertEqual([e['source_ref'] for e in events], ['ok'])
        coverage = self.store.rows("SELECT detail FROM coverage WHERE host='codex'")[0]['detail']
        self.assertIn('3 read requests lacked', coverage)

    def test_code_mode_dynamic_string_prefix_and_empty_read_receipts_are_not_loads(self):
        path = self.root / 'skills/example/SKILL.md'
        rows = [{'type': 'session_meta', 'payload': {'id': 'codex-a', 'cwd': str(self.project)}}]
        for ident, code, output in [
            ('prefix', 'text(await tools.exec_command({cmd:' + json.dumps('cat ' + str(path)) + '+ variable}));', '# Example'),
            ('empty', 'text(await tools.exec_command({cmd:' + json.dumps('head -n 0 ' + str(path)) + '}));', '')]:
            rows += [
                {'type': 'response_item', 'timestamp': self.now, 'payload': {'type': 'custom_tool_call', 'name': 'exec', 'call_id': ident, 'input': code}},
                {'type': 'response_item', 'timestamp': self.now, 'payload': {'type': 'custom_tool_call_output', 'call_id': ident,
                    'output': [{'type': 'text', 'text': json.dumps({'exit_code': 0, 'output': output})}]}}]
        self.transcript('codex', 'a', rows)
        refresh(self.store, self.root, self.home, project_root=self.project)
        self.assertEqual(self.store.rows('SELECT * FROM usage_events'), [])

    def test_eval_registry_and_original_grading_artifacts_do_not_invent_passes(self):
        (self.root / 'evals').mkdir()
        (self.root / 'evals/manifest.yaml').write_text('suites:\n  - target: example/check\n    owner_skill: example\n    layer: A\n    runner: do-not-execute-this\n    last_green: 2026-09-01\nexclusions:\n  - target: unrelated\n')
        artifact = self.root / 'skills/example/example-workspace/iteration-1/grading.json'
        artifact.parent.mkdir(parents=True)
        artifact.write_text('{"pass_rate":1.0}')
        registry, _ = inventory(self.store, self.root, self.home, self.project)
        result = ingest_evals(self.store, registry, self.root)
        self.assertEqual(result['eval_suites'], 1)
        self.assertEqual(result['eval_artifacts'], 1)
        suites = self.store.rows('SELECT * FROM eval_suites')
        self.assertEqual(suites[0]['last_green'], '2026-09-01')
        self.assertEqual(suites[0]['runner'], 'do-not-execute-this')
        self.assertEqual(self.store.rows('SELECT * FROM eval_runs'), [])
        self.assertEqual(artifact.read_text(), '{"pass_rate":1.0}')

    def test_typed_eval_result_and_legacy_report_are_one_assertion(self):
        folder = self.root / 'evals/reports'; folder.mkdir(parents=True)
        report = folder / 'sweep.md'
        assertion = '## PASS — example/check (exit 0)'
        report.write_text('# Layer A sweep — 2026-10-01 09:00 (manual)\n' + assertion + '\n')
        registry, _ = inventory(self.store, self.root, self.home, self.project)
        self.store.record('eval', {'id': 'typed-eval', 'suite_id': 'example/check',
            'capability_id': registry.resolve('example'), 'occurred_at': '2026-10-01T09:00:00Z',
            'outcome': 'pass', 'source_path': str(report.resolve()),
            'source_ref': 'line:2; assertion_sha256:' + hashlib.sha256(assertion.encode()).hexdigest()}, producer='eval-runner')
        ingest_evals(self.store, registry, self.root)
        self.assertEqual([e['id'] for e in self.store.rows('SELECT id FROM eval_runs')], ['typed-eval'])

    def test_eval_results_keep_original_artifact_and_unknown_revision(self):
        folder = self.root / 'evals/reports'; folder.mkdir(parents=True)
        (self.root / 'evals/manifest.yaml').write_text('suites:\n  - target: example/check\n    owner_skill: example\n    layer: A\n    last_green: 2026-09-01\n')
        report = folder / 'sweep.md'
        original = '# Layer A sweep — 2026-10-01 09:00 (manual)\n\n## PASS — example/check (exit 0)\n\n# Layer A sweep — 2026-10-02 09:00 (manual)\n\n## FAIL — example/check (exit 1)\n'
        report.write_text(original)
        registry, _ = inventory(self.store, self.root, self.home, self.project)
        ingest_evals(self.store, registry, self.root)
        ingest_evals(self.store, registry, self.root)
        events = self.store.rows('SELECT * FROM eval_runs ORDER BY occurred_at')
        self.assertEqual([e['outcome'] for e in events], ['pass', 'fail'])
        self.assertEqual([e['revision'] for e in events], [None, None])
        self.assertEqual(report.read_text(), original)
        report.write_text(original.replace('## PASS', '## FAIL', 1))
        ingest_evals(self.store, registry, self.root)
        self.assertEqual(len(self.store.rows('SELECT * FROM eval_runs')), 3)

    def test_factory_terminal_and_red_flags_are_reported_evidence(self):
        self.skill('dark-factory')
        folder = self.root / 'skills/dark-factory/runs'; folder.mkdir()
        source = folder / 'run-a.yaml'
        source.write_text('run_id: run-a\ndate: 2026-10-02\nterminal_status: HALT_AGENT_SKIPPED\nred_flags:\n  - "Null dispatch"\n')
        registry, _ = inventory(self.store, self.root, self.home, self.project)
        ingest_factories(self.store, registry, self.root)
        ingest_factories(self.store, registry, self.root)
        self.assertEqual(len(self.store.rows('SELECT * FROM outcomes')), 1)
        events = self.store.rows('SELECT * FROM frictions')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['producer'], 'agent')
        self.assertEqual(events[0]['host'], 'unknown')
        self.assertEqual(events[0]['occurred_at'], '2026-10-02')
        source.write_text(source.read_text().replace('HALT_AGENT_SKIPPED', 'READY_TO_SHIP'))
        ingest_factories(self.store, registry, self.root)
        self.assertEqual(len(self.store.rows('SELECT * FROM outcomes')), 2)
        self.assertEqual(len(self.store.rows('SELECT * FROM frictions')), 1)

    def test_missing_sources_are_coverage_gaps_and_unknowns_not_zero_claims(self):
        refresh(self.store, self.root, self.home, project_root=self.project)
        coverage = self.store.rows('SELECT * FROM coverage')
        self.assertTrue(coverage)
        self.assertTrue(any(c['status'] == 'unavailable' for c in coverage))
        self.assertFalse(any(c['status'] == 'complete' for c in coverage))


if __name__ == '__main__':
    unittest.main()

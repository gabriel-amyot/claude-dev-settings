import contextlib
import datetime as dt
import importlib.util
import hashlib
import sys
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


producer = load("catalog_producer_test", "harness/producer.py")
usage = load("usage_scanner_test", "claude-home/skill-proposals/skill_usage_scan.py")


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        code = self.root / "harness"
        code.mkdir()
        for name in ["store.py", "bridges.py", "render.py", "schema"]:
            (code / name).symlink_to(ROOT / "harness" / name, target_is_directory=name == "schema")
        self.report = self.root / "report.md"
        self.report.write_text("original output\n")
        self.db = self.root / "data.sqlite"

    def test_eval_result_idempotent_and_unknown_revision_preserved(self):
        record = {"suite_id": "demo/contract", "owner_skill": "demo", "occurred_at": "2026-10-26T10:00:00Z", "outcome": "fail", "revision": None}
        self.assertTrue(producer.publish("eval-sweep", self.report, [record], root=self.root, db=self.db))
        self.assertTrue(producer.publish("eval-sweep", self.report, [record], root=self.root, db=self.db))
        module = producer._load_store(self.root)
        with module.Store(self.db) as store:
            rows = store.rows("SELECT outcome,revision FROM eval_runs")
            self.assertEqual(rows, [{"outcome": "fail", "revision": None}])
            self.assertEqual(len(store.rows("SELECT id FROM artifacts")), 1)
        self.assertEqual(self.report.read_text(), "original output\n")
        self.assertTrue((self.root / "harness/view/index.html").is_file())
        self.assertFalse(list((self.db.parent / "backups").glob("*.sqlite")))

    def test_typed_then_legacy_refresh_counts_each_report_assertion_once(self):
        bridge = load("eval_dedup_bridge", "harness/bridges.py")
        (self.root / "evals/reports").mkdir(parents=True)
        (self.root / "evals/manifest.yaml").write_text("suites:\n  - target: demo/check\n    layer: A\n    owner_skill: demo\n")
        report = self.root / "evals/reports/2026-10-26-sweep.md"
        heading = "## PASS — demo/check (exit 0)"
        report.write_text("# Layer A sweep — 2026-10-26 10:00 (manual)\n\n" + heading + "\n")
        record = {"suite_id": "demo/check", "owner_skill": "demo", "occurred_at": "2026-10-26T10:00:00Z", "outcome": "pass", "revision": None}
        self.assertTrue(producer.publish("eval-sweep", report, [record], root=self.root, db=self.db))
        with producer._load_store(self.root).Store(self.db) as store:
            registry = bridge.Registry(store, self.root)
            bridge.ingest_evals(store, registry, self.root)
            bridge.ingest_evals(store, registry, self.root)
            self.assertEqual(store.rows("SELECT outcome,occurred_at,revision FROM eval_runs"), [{"outcome": "pass", "occurred_at": "2026-10-26T10:00:00Z", "revision": None}])
        # A later result appended to the SAME report is a separate execution.
        with report.open("a") as stream:
            stream.write("\n# Layer A sweep — 2026-10-26 11:00 (manual)\n\n## FAIL — demo/check (exit 1)\n")
        with producer._load_store(self.root).Store(self.db) as store:
            registry = bridge.Registry(store, self.root)
            bridge.ingest_evals(store, registry, self.root)
            bridge.ingest_evals(store, registry, self.root)
            self.assertEqual(sorted(row["outcome"] for row in store.rows("SELECT outcome FROM eval_runs")), ["fail", "pass"])
        # New producer can bind that appended result after legacy import, too.
        late = {**record, "occurred_at": "2026-10-26T11:00:00Z", "outcome": "fail"}
        self.assertTrue(producer.publish("eval-sweep", report, [late], root=self.root, db=self.db))
        with producer._load_store(self.root).Store(self.db) as store:
            self.assertEqual(len(store.rows("SELECT id FROM eval_runs")), 2)

    def test_old_untyped_results_survive_next_to_exact_typed_result(self):
        bridge = load("eval_history_bridge", "harness/bridges.py")
        (self.root / "evals/reports").mkdir(parents=True)
        (self.root / "evals/manifest.yaml").write_text("suites:\n  - target: demo/check\n    layer: A\n    owner_skill: demo\n")
        report = self.root / "evals/reports/2026-10-26-sweep.md"
        heading = "## PASS — demo/check (exit 0)"
        lines = ["# Layer A sweep — 2026-10-25 09:00 (manual)", heading, "", "# Layer A sweep — 2026-10-26 10:00 (manual)", heading]
        report.write_text("\n".join(lines) + "\n")
        source_ref = "line:5; assertion_sha256:" + hashlib.sha256(heading.encode()).hexdigest()
        record = {"suite_id": "demo/check", "owner_skill": "demo", "occurred_at": "2026-10-26T10:00:00Z", "outcome": "pass", "source_ref": source_ref}
        self.assertTrue(producer.publish("eval-sweep", report, [record], root=self.root, db=self.db))
        with producer._load_store(self.root).Store(self.db) as store:
            registry = bridge.Registry(store, self.root)
            bridge.ingest_evals(store, registry, self.root)
            bridge.ingest_evals(store, registry, self.root)
            rows = store.rows("SELECT occurred_at,revision FROM eval_runs ORDER BY occurred_at")
            self.assertEqual(rows, [{"occurred_at": "2026-10-25", "revision": None}, {"occurred_at": "2026-10-26T10:00:00Z", "revision": None}])

    def test_changed_delivery_snapshots_existing_operational_data(self):
        record = {"suite_id": "demo/check", "owner_skill": "demo", "occurred_at": "2026-10-26T10:00:00Z", "outcome": "pass"}
        self.assertTrue(producer.publish("eval-sweep", self.report, [record], root=self.root, db=self.db))
        self.report.write_text("second measured run\n")
        record = {**record, "occurred_at": "2026-10-26T11:00:00Z", "outcome": "fail"}
        self.assertTrue(producer.publish("eval-sweep", self.report, [record], root=self.root, db=self.db))
        backups = list((self.db.parent / "backups").glob("*.sqlite"))
        self.assertTrue(backups)
        with producer._load_store(self.root).Store(backups[0]) as store:
            self.assertEqual(store.rows("SELECT outcome FROM eval_runs"), [{"outcome": "pass"}])

    def test_failed_delivery_is_spooled_and_retry_is_idempotent(self):
        record = {"suite_id": "demo/check", "owner_skill": "demo", "occurred_at": "2026-10-26T11:00:00Z", "outcome": "pass"}
        with patch.object(producer, "_load_store", side_effect=RuntimeError("offline")), contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(producer.publish("eval-sweep", self.report, [record], root=self.root, db=self.db))
        self.assertEqual(len(list((self.root / "harness/data/pending").glob("*.json"))), 1)
        self.assertEqual(producer.retry_pending(root=self.root, db=self.db), {"delivered": 1, "pending": 0})
        self.assertEqual(producer.retry_pending(root=self.root, db=self.db), {"delivered": 0, "pending": 0})

    def test_bad_eval_fields_do_not_forge_a_result(self):
        record = {"suite_id": "demo/check", "owner_skill": "demo", "occurred_at": "2026-10-26T11:00:00Z", "outcome": "pass", "approved": True}
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(producer.publish("eval-sweep", self.report, [record], root=self.root, db=self.db))
        with producer._load_store(self.root).Store(self.db) as store:
            self.assertEqual(store.rows("SELECT id FROM eval_runs"), [])

    def test_factory_directory_publishes_shared_importer_outcome(self):
        run_dir = self.root / "skills/dark-factory/runs"
        run_dir.mkdir(parents=True)
        (run_dir.parent / "SKILL.md").write_text("---\nname: dark-factory\ndescription: fixture\n---\n")
        run = run_dir / "run-2026-10-26-example.yaml"
        run.write_text("date: 2026-10-26\nterminal_status: READY_TO_SHIP\n")
        with patch.dict(os.environ, {"HARNESS_HOME": str(self.root)}):
            self.assertTrue(producer.publish("factory-telemetry", run_dir, root=self.root, db=self.db))
            self.assertTrue(producer.publish("factory-telemetry", run_dir, root=self.root, db=self.db))
        with producer._load_store(self.root).Store(self.db) as store:
            rows = store.rows("SELECT occurred_at,status,revision FROM outcomes")
            self.assertEqual(rows, [{"occurred_at": "2026-10-26", "status": "READY_TO_SHIP", "revision": None}])

    def test_spool_limit_preserves_previous_deliveries(self):
        envelope = {"kind": "tax-scan", "source_path": str(self.report), "fingerprint": "x", "observed_at": "2026-10-26T11:00:00Z", "records": []}
        first = producer._spool(envelope, self.root)
        with patch.object(producer, "MAX_PENDING", 1):
            with self.assertRaises(RuntimeError):
                producer._spool({**envelope, "fingerprint": "y"}, self.root)
        self.assertTrue(first.exists())

    def test_real_claude_events_only_with_timestamp_and_org_scope(self):
        projects = self.root / ".claude/projects"
        selected = projects / "-Users-example-Developer-grp-beklever-com-project"
        selected.mkdir(parents=True)
        other = projects / "-Users-example-Developer-supervisr-ai-project"
        other.mkdir()
        now = dt.datetime.now(dt.timezone.utc)
        current = now.isoformat()
        old = (now - dt.timedelta(days=100)).isoformat()
        call = lambda timestamp: {"type": "assistant", "timestamp": timestamp, "cwd": "/Users/example/Developer/grp-beklever-com/app", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "demo"}}]}}
        entries = [call(current), call(old), {"type": "user", "timestamp": current, "message": {"content": "quoted example: <command-name>/demo</command-name>"}}, {"type": "user", "timestamp": current, "message": {"content": [{"type": "tool_result", "content": json.dumps(call(current))}]}}, {"type": "user", "timestamp": current, "message": {"content": "/demo run"}}]
        (selected / "events.jsonl").write_text("\n".join(json.dumps(e) for e in entries))
        (other / "events.jsonl").write_text(json.dumps(call(current)))
        with patch.object(usage, "PROJECTS", projects), patch.object(usage, "_aliases", return_value={"demo": "demo"}):
            tools, slash, count = usage.scan(30, "klever")
        self.assertEqual(tools["demo"], 1)
        self.assertEqual(slash["demo"], 1)
        self.assertEqual(count, 1)

    def test_usage_includes_registered_plugin_skills(self):
        skill = self.root / ".claude/skills/core/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: core\ndescription: example\n---\n")
        plugin = self.root / "plugin"
        session = plugin / "skills/pickup/SKILL.md"
        session.parent.mkdir(parents=True)
        session.write_text("---\nname: pickup\ndescription: example\n---\n")
        registry = self.root / ".claude/plugins/installed_plugins.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({"plugins": {"session@local": [{"installPath": str(plugin)}]}}))
        with patch.object(Path, "home", return_value=self.root):
            self.assertEqual(usage.installed_skills(), {"core", "session:pickup"})


class SweepIntegrationTests(unittest.TestCase):
    def test_sweep_emits_exact_assertion_refs_and_labels_simulation(self):
        try:
            sweep = load("sweep_provenance_test", "skills/skill-evals/scripts/run_sweep.py")
        except ModuleNotFoundError:
            self.skipTest("existing eval runner requires PyYAML")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.yaml"
            manifest.write_text("suites:\n  - target: demo/check\n    layer: A\n    owner_skill: demo\n    runner: NEVER EXECUTE\n    last_green: null\n")
            published = []
            with patch.object(sweep, "MANIFEST", str(manifest)), patch.object(sweep, "REPORTS_DIR", str(root / "reports")), patch.object(sweep, "INBOX_DIR", str(root / "inbox")), patch.object(sweep, "run_suite", return_value=(True, 0, "fixture result")), patch.object(sweep, "publish_harness", side_effect=lambda kind, path, records: published.append((path, records))), patch("sys.argv", ["run_sweep.py", "--simulate-failure", "demo/check"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sweep.main(), 1)
            path, records = published[0]
            self.assertEqual(records[0]["outcome"], "fail")
            self.assertIsNone(records[0]["revision"])
            self.assertTrue(records[0]["summary"].startswith("SIMULATED failure"))
            self.assertEqual(producer._eval_source_ref(path, records[0]), records[0]["source_ref"])
            self.assertIn("harness-eval-run:", Path(path).read_text())

    def test_publish_failure_does_not_change_original_failed_or_passed_sweep(self):
        try:
            sweep = load("sweep_producer_test", "skills/skill-evals/scripts/run_sweep.py")
        except ModuleNotFoundError:
            self.skipTest("existing eval runner requires PyYAML")
        for passed in (True, False):
            with self.subTest(passed=passed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest = root / "manifest.yaml"
                manifest.write_text("suites:\n  - target: demo/check\n    layer: A\n    owner_skill: demo\n    runner: NEVER EXECUTE\n    last_green: null\n")
                with patch.object(sweep, "MANIFEST", str(manifest)), patch.object(sweep, "REPORTS_DIR", str(root / "reports")), patch.object(sweep, "INBOX_DIR", str(root / "inbox")), patch.object(sweep, "run_suite", return_value=(passed, 0 if passed else 1, "fixture result")), patch.dict(os.environ, {"HARNESS_ROOT": str(root / "missing")}), patch("sys.argv", ["run_sweep.py"]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    result = sweep.main()
                self.assertEqual(result, 0 if passed else 1)
                self.assertTrue(list((root / "reports").glob("*-sweep.md")))
                if not passed:
                    self.assertTrue(list((root / "inbox").glob("*.json")))


if __name__ == "__main__":
    unittest.main()

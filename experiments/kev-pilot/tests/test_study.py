"""Study lifecycle checks use fake stages and never launch a model or install tools."""
import fcntl
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_client
import runtime
import study


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.folder = self.data / "studies" / "test"
        self.folder.mkdir(parents=True)
        self.library = self.root / "library"
        self.library.mkdir()
        self.original = {"pid": 11111, "identity": "original owned process"}
        self.replacement = {"pid": 22222, "identity": "another owned process"}
        study.save(self.folder / "status.json", {"status": "starting", "started_at": study.now()})
        (self.data / "snapshot.json").write_text(json.dumps({"root": str(self.library), "files": {}}))
        self.args = SimpleNamespace(data=self.data, study=self.folder, source=self.root / "source",
                                    wait_bootstrap=None, bootstrap_wait_seconds=10, keep_server=False)
        self.calls = []

    def status(self):
        return json.loads((self.folder / "status.json").read_text())

    def events(self):
        return [json.loads(line) for line in (self.folder / "events.jsonl").read_text().splitlines()]

    def fake_stages(self, argv, **kwargs):
        self.calls.append(argv)
        if len(argv) > 2 and Path(argv[1]).name == "runtime.py" and argv[2] == "start":
            kwargs["stdout"].write(json.dumps({"status": "starting", **self.original}))
            runtime.write_private(self.data / "server.json", self.original)
        stage = Path(argv[1]).stem if len(argv) > 1 else ""
        if stage == "pilot":
            stage = argv[-1]
        if stage in ("probes", "benchmark", "diagnostic"):
            run = self.data / "runs" / stage
            run.mkdir(parents=True, exist_ok=True)
            (run / "manifest.json").write_text(json.dumps({"started_at": study.now()}))
            (run / "report.json").write_text(json.dumps({"kind": stage, "completed_requests": 1,
                                                        "failed_requests": 0, "not_run_requests": 0}))
            kwargs["stdout"].write(json.dumps({"run": str(run)}) + "\n")
        return SimpleNamespace(returncode=0)

    def test_failed_bootstrap_preserves_failure_and_never_starts_stages(self):
        receipt = self.root / "bootstrap.json"
        receipt.write_text(json.dumps({"status": "failed", "error": "test download failure"}))
        self.args.wait_bootstrap = receipt
        with patch.object(study.subprocess, "run") as run, patch.object(local_client, "Client") as client:
            self.assertEqual(study.run_study(self.args), 1)
        run.assert_not_called()
        client.assert_not_called()
        self.assertEqual(self.status()["status"], "failed")
        self.assertIn("bootstrap failed", self.status()["error"])
        summary = json.loads((self.folder / "summary.json").read_text())
        self.assertEqual(summary["study_status"], "failed")
        self.assertEqual(summary["runs"], [])

    def test_wait_budget_exhaustion_never_starts_inference(self):
        receipt = self.root / "bootstrap.json"
        receipt.write_text(json.dumps({"status": "started"}))
        self.args.wait_bootstrap = receipt
        self.args.bootstrap_wait_seconds = 0
        with patch.object(study.subprocess, "run") as run:
            self.assertEqual(study.run_study(self.args), 1)
        run.assert_not_called()
        self.assertIn("budget exhausted", self.status()["error"])

    def test_lock_contention_does_not_clobber_current_state_or_launch_stages(self):
        before = (self.folder / "status.json").read_bytes()
        with (self.data / "study.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(study.subprocess, "run") as run:
                self.assertEqual(study.run_study(self.args), 1)
            run.assert_not_called()
        self.assertEqual((self.folder / "status.json").read_bytes(), before)
        self.assertEqual(self.events()[-1]["event"], "study_reentry_rejected")

    def test_terminal_or_already_running_study_cannot_repeat_inference(self):
        for state in ("completed", "failed", "running", "waiting_for_bootstrap"):
            with self.subTest(state=state):
                study.save(self.folder / "status.json", {"status": state, "started_at": study.now()})
                before = (self.folder / "status.json").read_bytes()
                with patch.object(study.subprocess, "run") as run, patch.object(local_client, "Client") as client:
                    self.assertEqual(study.run_study(self.args), 1)
                run.assert_not_called()
                client.assert_not_called()
                self.assertEqual((self.folder / "status.json").read_bytes(), before)

    def test_summary_excludes_unrelated_manual_runs_after_study_start(self):
        state = {"status": "completed", "started_at": study.now(), "run_paths": []}
        manual = self.data / "runs" / "manual"
        manual.mkdir(parents=True)
        (manual / "manifest.json").write_text(json.dumps({"started_at": study.now()}))
        (manual / "report.json").write_text(json.dumps({"kind": "manual", "completed_requests": 99,
                                                       "failed_requests": 0, "not_run_requests": 0}))
        study.write_summary(self.folder, state, self.data)
        self.assertEqual(json.loads((self.folder / "summary.json").read_text())["runs"], [])

    def test_transient_bootstrap_fragment_recovers_within_same_wait_budget(self):
        receipt = self.root / "bootstrap.json"
        receipt.write_text('{"status":')
        self.args.wait_bootstrap = receipt
        def completed_after_sleep(seconds):
            self.assertEqual(seconds, 1)
            receipt.write_text(json.dumps({"status": "completed"}))
        with patch.object(study.time, "sleep", side_effect=completed_after_sleep), patch.object(study.subprocess, "run", side_effect=self.fake_stages), patch.object(local_client, "Client", return_value=SimpleNamespace(get_models=lambda: {})):
            self.assertEqual(study.run_study(self.args), 0)
        self.assertEqual(self.status()["status"], "completed")
        self.assertTrue(any(row["event"] == "bootstrap_observed" for row in self.events()))

    def test_stage_failure_survives_owned_runtime_cleanup(self):
        def stages(argv, **kwargs):
            result = self.fake_stages(argv, **kwargs)
            if argv[-1] == "benchmark":
                kwargs["stdout"].write("retained benchmark failure\n")
                return SimpleNamespace(returncode=1)
            return result
        with patch.object(study.subprocess, "run", side_effect=stages), patch.object(local_client, "Client", return_value=SimpleNamespace(get_models=lambda: {})):
            self.assertEqual(study.run_study(self.args), 1)
        status = self.status()
        self.assertEqual((status["status"], status["stage"]), ("failed", "benchmark"))
        self.assertIn("retained benchmark failure", (self.folder / "benchmark.log").read_text())
        stop = next(argv for argv in self.calls if len(argv) > 2 and argv[2] == "stop")
        self.assertEqual(stop[stop.index("--expected-pid") + 1], str(self.original["pid"]))
        self.assertEqual(stop[stop.index("--expected-identity") + 1], self.original["identity"])
        self.assertFalse(any(argv[-1] == "diagnostic" for argv in self.calls))

    def test_changed_source_stops_before_inference_and_retains_error(self):
        def stages(argv, **kwargs):
            result = self.fake_stages(argv, **kwargs)
            if len(argv) > 2 and Path(argv[1]).name == "runtime.py" and argv[2] == "start":
                (self.library / "context").mkdir()
                (self.library / "context/changed.md").write_text("Changed source fixture")
            return result
        with patch.object(study.subprocess, "run", side_effect=stages), patch.object(local_client, "Client") as client:
            self.assertEqual(study.run_study(self.args), 1)
        client.assert_not_called()
        self.assertEqual(self.status()["status"], "failed")
        self.assertIn("library source changed", self.status()["error"])
        self.assertFalse(any(len(argv) > 1 and Path(argv[1]).name == "probes.py" for argv in self.calls))
        self.assertTrue(any(len(argv) > 2 and argv[2] == "stop" for argv in self.calls))

    def test_replaced_runtime_during_study_is_never_signalled(self):
        def stages(argv, **kwargs):
            result = self.fake_stages(argv, **kwargs)
            if len(argv) > 1 and Path(argv[1]).name == "probes.py":
                runtime.write_private(self.data / "server.json", self.replacement)
            if len(argv) > 2 and Path(argv[1]).name == "runtime.py" and argv[2] == "stop":
                args = SimpleNamespace(expected_pid=int(argv[argv.index("--expected-pid") + 1]),
                                       expected_identity=argv[argv.index("--expected-identity") + 1])
                try:
                    runtime.stop(args, self.data)
                except local_client.ClientError:
                    return SimpleNamespace(returncode=1)
            return result
        with patch.object(study.subprocess, "run", side_effect=stages), patch.object(local_client, "Client", return_value=SimpleNamespace(get_models=lambda: {})), patch.object(runtime, "identity", return_value=self.replacement["identity"]), patch.object(runtime.os, "kill") as kill:
            study.run_study(self.args)
        kill.assert_not_called()
        self.assertTrue(any(row["event"] == "cleanup_error" for row in self.events()))
        self.assertEqual(json.loads((self.data / "server.json").read_text()), self.replacement)


if __name__ == "__main__":
    unittest.main()

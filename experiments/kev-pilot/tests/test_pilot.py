import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pilot import Run, diagnostic, digest, main, packet, protect_output, report, run_guarded, summarize


class CharacterTokenizer:
    def encode(self, text):
        return list(text)

    def decode(self, tokens):
        return "".join(tokens)


class PilotTests(unittest.TestCase):
    def manifest(self, planned=2):
        return {"run_id": "test", "kind": "test", "status": "completed", "planned_requests": planned,
                "corpus_manifest_sha256": "corpus", "protocol_sha256": "protocol"}

    def test_empty_run_cannot_be_success_or_quality_evidence(self):
        result = summarize(self.manifest(), [])
        self.assertEqual(result["completed_requests"], 0)
        self.assertEqual(result["not_run_requests"], 2)
        self.assertEqual(result["quality_decision"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["production_enabled"])

    def test_failures_and_priming_are_not_measured_successes(self):
        records = [{"event": "attempt", "request_id": "a", "phase": "measured"},
                   {"event": "outcome", "request_id": "a", "phase": "measured", "status": "failed", "wall_ms": 2},
                   {"event": "attempt", "request_id": "p", "phase": "prime"},
                   {"event": "outcome", "request_id": "p", "phase": "prime", "status": "completed", "wall_ms": 1}]
        result = summarize(self.manifest(), records)
        self.assertEqual((result["attempted_requests"], result["completed_requests"], result["failed_requests"]), (1, 0, 1))
        self.assertEqual(result["priming_attempts"], 1)
        self.assertEqual(result["not_run_requests"], 1)

    def test_interrupted_attempt_remains_unfinished(self):
        result = summarize(self.manifest(), [{"event": "attempt", "request_id": "a", "phase": "measured"}])
        self.assertEqual(result["unfinished_requests"], 1)
        self.assertEqual(result["completed_requests"], 0)

    def test_packet_excludes_grade_id_and_notes(self):
        document = {"id": "SECRET_ID", "title": "Reference", "text": "Useful body", "labels": {"a": 3}, "label_note": "SECRET_NOTE"}
        state, info = packet("What helps?", document, CharacterTokenizer(), 300)
        self.assertNotIn("SECRET_ID", state)
        self.assertNotIn("SECRET_NOTE", state)
        self.assertNotIn("labels", state)
        self.assertFalse(info["document_prefix_used"])

    def test_document_prefix_is_disclosed_and_bounded(self):
        state, info = packet("query", {"title": "title", "text": "x"*1000}, CharacterTokenizer(), 200)
        self.assertLessEqual(len(state), 200)
        self.assertTrue(info["document_prefix_used"])
        self.assertGreater(info["omitted_tokens"], 0)

    def test_output_cannot_be_under_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                protect_output(root / "results", root)
            protect_output(root / "results", root / "library")

    def test_receipt_is_written_before_failed_network_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = {"latency": {"maximum_seconds": 60}}
            snapshot = {"root": str(root / "library"), "corpus_manifest_sha256": "hash"}
            run = Run("test", root / "output", protocol, snapshot, 1)
            class FailingClient:
                def request(self, state, questions):
                    before = [json.loads(line) for line in (run.path / "receipts.jsonl").read_text().splitlines()]
                    self.was_logged = before[0]["event"] == "attempt"
                    raise TimeoutError("test timeout")
            client = FailingClient()
            self.assertIsNone(run.request(client, "state", {"q": {"type": "noul"}}))
            self.assertTrue(client.was_logged)
            records = [json.loads(line) for line in (run.path / "receipts.jsonl").read_text().splitlines()]
            self.assertEqual(records[-1]["status"], "failed")
            self.assertNotIn("fallback", records[-1])
            self.assertIn("fallback_policy", records[-1])

    def test_hash_is_stable_under_dictionary_order(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))

    def test_client_setup_failure_retains_report_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "library"
            source.mkdir()
            snapshot = {"root": str(source), "files": {}, "corpus_manifest_sha256": "corpus"}
            run = Run("test", root / "output", {"latency": {"maximum_seconds": 60}}, snapshot, 2)
            def missing_key():
                raise FileNotFoundError("missing private key")
            result = run_guarded(run, missing_key, lambda client: self.fail("must not execute"))
            self.assertEqual(result["run_status"], "failed")
            self.assertEqual(result["not_run_requests"], 2)
            self.assertEqual(result["completed_requests"], 0)
            self.assertTrue((run.path / "report.md").exists())
            records = [json.loads(line) for line in (run.path / "receipts.jsonl").read_text().splitlines()]
            self.assertEqual(records[0]["event"], "run_error")

    def test_all_failed_requests_fail_guarded_run_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "library"
            source.mkdir()
            snapshot = {"root": str(source), "files": {}, "corpus_manifest_sha256": "corpus"}
            protocol = {"latency": {"maximum_seconds": 60}}
            run = Run("test", root / "output", protocol, snapshot, 1)
            class FailingClient:
                def get_models(self):
                    return {}
                def request(self, state, questions):
                    raise TimeoutError("actual request failed")
            result = run_guarded(run, FailingClient, lambda client: run.request(client, "state", {"q": {"type": "noul"}}))
            self.assertEqual(result["run_status"], "failed")
            self.assertEqual((result["completed_requests"], result["failed_requests"]), (0, 1))
            self.assertEqual(json.loads((run.path / "manifest.json").read_text())["status"], "failed")
            data = root / "output"
            (data / "snapshot.json").write_text(json.dumps(snapshot))
            with patch.object(sys, "argv", ["pilot.py", "--data", str(data), "benchmark"]), patch("pilot.benchmark", return_value=result):
                self.assertEqual(main(), 1)

    def test_mixed_and_partial_counts_cannot_report_completed(self):
        rows = [{"event": "attempt", "request_id": "a", "phase": "measured", "stratum": "test"},
                {"event": "outcome", "request_id": "a", "phase": "measured", "status": "completed", "wall_ms": 2, "stratum": "test"},
                {"event": "attempt", "request_id": "b", "phase": "measured", "stratum": "test"},
                {"event": "outcome", "request_id": "b", "phase": "measured", "status": "failed", "wall_ms": 90, "stratum": "test"}]
        result = summarize(self.manifest(), rows)
        self.assertEqual(result["run_status"], "completed_with_errors")
        self.assertEqual(result["strata"]["test"]["failed"], 1)
        self.assertEqual(result["strata"]["test"]["failure_p95_ms"], 90)
        self.assertEqual(result["strata"]["test"]["p95_ms"], 2)
        self.assertEqual(summarize(self.manifest(3), rows)["run_status"], "incomplete")

    def test_torn_trailing_receipt_preserves_bytes_and_unfinished_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "manifest.json").write_text(json.dumps(self.manifest(1)))
            raw = json.dumps({"event": "attempt", "request_id": "a", "phase": "measured"}).encode() + b'\n{"event":"outcome","request_id":'
            (path / "receipts.jsonl").write_bytes(raw)
            result = report(path)
            self.assertEqual(result["run_status"], "failed")
            self.assertEqual(result["unfinished_requests"], 1)
            self.assertEqual(result["receipt_corruptions"][0]["kind"], "torn_trailing_record")
            self.assertEqual((path / "receipts.jsonl").read_bytes(), raw)
            self.assertTrue((path / "receipt-corruption.json").exists())

    def test_middle_corruption_is_failed_even_with_valid_success_after_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "manifest.json").write_text(json.dumps(self.manifest(1)))
            rows = [json.dumps({"event": "attempt", "request_id": "a", "phase": "measured"}),
                    "not json", json.dumps({"event": "outcome", "request_id": "a", "phase": "measured", "status": "completed", "wall_ms": 4})]
            raw = ("\n".join(rows)+"\n").encode()
            (path / "receipts.jsonl").write_bytes(raw)
            result = report(path)
            self.assertEqual(result["completed_requests"], 1)
            self.assertEqual(result["run_status"], "failed")
            self.assertEqual(result["receipt_corruption_count"], 1)
            self.assertEqual((path / "receipts.jsonl").read_bytes(), raw)

    def test_empty_candidate_pool_is_not_a_kev_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "library"
            source.mkdir()
            snapshot = {"root": str(source), "files": {}, "documents": [], "corpus_manifest_sha256": "corpus"}
            fixtures = root / "queries.jsonl"
            fixtures.write_text(json.dumps({"id": "empty", "query": "no match", "labels": {}, "dataset_type": "authored_diagnostic"})+"\n")
            args = SimpleNamespace(data=root / "output", fixtures=fixtures, limit=0)
            protocol = {"latency": {"maximum_seconds": 60}, "candidate_pool": 20, "diagnostic_dataset": "authored"}
            class NoInferenceClient:
                def get_models(self):
                    return {}
                def request(self, *args):
                    raise AssertionError("no inference should run")
            with patch("pilot.client_for", return_value=NoInferenceClient()), patch("pilot.tokenizer", return_value=CharacterTokenizer()):
                result = diagnostic(args, protocol, snapshot)
            self.assertEqual(result["run_status"], "no_measured_requests")
            self.assertEqual(result["no_candidate_queries"], 1)
            self.assertEqual(result["query_count"], 0)
            self.assertEqual(result["queries_with_fallback"], 0)
            run = next((args.data / "runs").iterdir())
            rows = [json.loads(line) for line in (run / "receipts.jsonl").read_text().splitlines()]
            empty = next(row for row in rows if row["event"] == "no_candidates")
            self.assertFalse(empty["kev_success"])
            self.assertEqual(empty["status"], "not_run")
            self.assertNotIn("fallback", empty)


if __name__ == "__main__":
    unittest.main()

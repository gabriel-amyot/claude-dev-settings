"""Offline checks for the read-only corpus and evaluation boundaries."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid

MODULE = Path(__file__).resolve().parents[1] / "retrieval.py"
spec = importlib.util.spec_from_file_location("pilot_retrieval", MODULE)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "library"
        (self.root / "context").mkdir(parents=True)
        (self.root / "context/a.md").write_text("# HTTP Egress\nDisable proxy inheritance.\n")
        (self.root / "context/b.md").write_text("# Build Files\nPreserve build files.\n")
        (self.root / "ALIASES.md").write_text(
            "| Alias | Path | Trigger | Keywords |\n"
            "| http-egress | context/a.md | proxy inheritance requests | network header |\n"
            "| build-files | context/b.md | build config files | terraform lockfile |\n")
        self.hook = Path(self.temp.name) / "hook.sh"
        self.hook.write_text("# fixture hook\n")

    def snapshot(self):
        return r.snapshot_library(self.root, self.hook)

    def test_legacy_and_lexical_rank_the_relevant_document(self):
        snap = self.snapshot()
        self.assertEqual(r.legacy_rank("HTTP egress proxy inheritance", snap)[0], "context/a.md")
        self.assertEqual(r.lexical_rank("HTTP proxy inheritance", snap)[0], "context/a.md")
        self.assertEqual(r.legacy_rank("library HTTP proxy inheritance", snap), [])
        self.assertEqual(r.legacy_rank("hi", snap), [])

    def test_stateful_hook_is_never_executed(self):
        self.hook.write_text("exit 99\n")
        self.assertEqual(r.legacy_rank("HTTP proxy inheritance", self.snapshot()), ["context/a.md"])

    def test_legacy_scoring_matches_real_hook_with_disposable_home(self):
        hook = MODULE.parents[2] / "hooks/bibliotheque-recall.sh"
        if not hook.is_file():
            self.skipTest("source hook unavailable in this checkout")
        fake_home = Path(self.temp.name)
        (fake_home / ".claude").mkdir()
        (fake_home / ".claude/library").symlink_to(self.root, target_is_directory=True)
        snap = self.snapshot()
        for query in ("HTTP proxy inheritance", "build config files", "network header only", "library proxy inheritance"):
            session_id = "kev-retrieval-test-" + uuid.uuid4().hex
            marker = Path("/tmp") / ("bibliotheque-recall-" + session_id)
            self.addCleanup(lambda p=marker: p.unlink(missing_ok=True))
            result = subprocess.run(["bash", str(hook)], input=json.dumps({
                "prompt": query, "cwd": str(fake_home), "session_id": session_id}),
                env={**os.environ, "HOME": str(fake_home)}, text=True, capture_output=True, check=True)
            observed = [line.split("→ ~/", 1)[1].split(" — ", 1)[0]
                        for line in result.stdout.splitlines() if "→ ~/" in line]
            expected = [".claude/library/" + doc_id for doc_id in r.legacy_rank(query, snap)]
            self.assertEqual(observed, expected, query)

    def test_manifest_detects_mutation_addition_deletion(self):
        before = self.snapshot()
        self.assertTrue(r.assert_source_unchanged(self.root, before))
        p = self.root / "context/a.md"
        p.write_text("changed")
        with self.assertRaises(RuntimeError):
            r.assert_source_unchanged(self.root, before)
        snap = self.snapshot()
        added = self.root / "context/new.md"
        added.write_text("new")
        with self.assertRaises(RuntimeError):
            r.assert_source_unchanged(self.root, snap["files"])
        snap = self.snapshot()
        added.unlink()
        with self.assertRaises(RuntimeError):
            r.assert_source_unchanged(self.root, snap)

    def test_symlink_escape_and_out_of_scope_alias_are_observations(self):
        outside = Path(self.temp.name) / "secret.md"
        outside.write_text("not allowed")
        (self.root / "context/leak.md").symlink_to(outside)
        (self.root / "context/dir").symlink_to(outside.parent, target_is_directory=True)
        with (self.root / "ALIASES.md").open("a") as f:
            f.write("| escape | ../secret.md | leak | |\n| lost | context/lost.md | gone | |\n")
        snap = self.snapshot()
        self.assertNotIn("not allowed", json.dumps(snap))
        self.assertTrue(any(o["kind"] == "symlink_excluded" for o in snap["observations"]))
        self.assertTrue(any(o["kind"] == "missing_alias_target" for o in snap["observations"]))
        self.assertEqual(len(snap["documents"]), 2)

    def test_metrics_discriminate_reversal_and_do_not_invent_labels(self):
        labels = {"a": 3, "b": 0, "c": 1}
        good = r.metrics(labels, ["a", "c", "b"])
        bad = r.metrics(labels, ["b", "c", "a"])
        self.assertGreater(good["ndcg_at_5"], bad["ndcg_at_5"])
        self.assertEqual(good["first_useful_hit"], 1)
        self.assertEqual(bad["first_useful_hit"], 3)
        self.assertEqual(good["recall_at_5"], 1.0)
        missing = r.metrics(labels, ["unlabelled", "a"])
        self.assertIsNone(missing["ndcg_at_5"])
        self.assertIsNone(missing["irrelevant_at_5"])
        self.assertEqual(missing["unjudged_at_5"], 1)
        self.assertIsNone(r.metrics({}, ["a"])["recall_at_5"])
        self.assertIsNone(r.metrics({"a": 0}, ["a"])["recall_at_5"])
        with self.assertRaises(ValueError):
            r.metrics({"a": 7}, ["a"])


if __name__ == "__main__":
    unittest.main()

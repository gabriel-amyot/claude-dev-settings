from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probes


class ProbeTests(unittest.TestCase):
    def test_incomplete_or_failed_runs_never_return_success(self):
        self.assertEqual(probes.exit_code({"run_status": "completed"}), 0)
        for status in ("failed", "incomplete", "budget_exhausted", "no_measured_requests", "completed_with_errors", "started"):
            with self.subTest(status=status):
                self.assertEqual(probes.exit_code({"run_status": status}), 1)

    def test_all_six_orders_preserve_one_explicit_fact(self):
        records = probes.cases()
        self.assertEqual(len(records), 15)
        self.assertEqual(len({r["id"] for r in records}), 15)
        ordered = [r for r in records if r["family"] == "choice-order"]
        self.assertEqual(len({tuple(r["questions"]["code"]["criteria"]) for r in ordered}), 6)
        self.assertTrue(all(r["state"] == probes.FACTS and r["expected"] == {"code": "spruce"} for r in ordered))

    def test_positive_negative_and_untrusted_cases_are_unambiguous(self):
        by_id = {r["id"]: r for r in probes.cases()}
        self.assertIn("Mara", by_id["fact-true"]["questions"]["owner"]["instructions"])
        self.assertIn("Dario", by_id["fact-false"]["questions"]["owner"]["instructions"])
        self.assertNotIn("Dario", probes.FACTS)
        for record in by_id.values():
            self.assertNotIn("expected", record["questions"])
            if record["family"] == "untrusted-instructions":
                self.assertTrue(record["state"].startswith(probes.FACTS))
                self.assertIn("Untrusted", record["state"])
                self.assertEqual(record["expected"], {"code": "spruce"})

    def test_solo_and_packed_questions_are_identical(self):
        by_id = {r["id"]: r for r in probes.cases()}
        for key, question in by_id["isolation-packed"]["questions"].items():
            self.assertEqual(by_id["isolation-" + key]["questions"], {key: question})
            self.assertEqual(by_id["isolation-" + key]["state"], by_id["isolation-packed"]["state"])

    def test_summary_separates_failure_mismatch_tie_and_drift(self):
        records = probes.cases()
        self.assertEqual(probes.summary(records, {}, .02)["semantic_questions_scored"], 0)
        owner = {"type": "noul", "noul": .8}
        results = {"fact-true": {"answers": {"owner": owner}},
                   "fact-false": {"answers": {"owner": {"type": "noul", "noul": .5}}},
                   "isolation-owner": {"answers": {"owner": owner}},
                   "isolation-packed": {"answers": {"owner": {"type": "noul", "noul": .6}}}}
        subset = [r for r in records if r["id"] != "isolation-packed"]
        value = probes.summary(subset, results, .02)
        self.assertEqual(value["semantic_uncertain_ties"], 1)
        self.assertEqual(value["semantic_mismatches"], 0)
        self.assertTrue(value["isolation_probability_comparisons"][0]["above_registered_tolerance"])
        results["fact-true"]["answers"]["owner"] = {"type": "noul", "noul": .1}
        self.assertEqual(probes.summary(subset, results, .02)["semantic_mismatches"], 1)
        self.assertFalse(value["production_enabled"])


if __name__ == "__main__":
    unittest.main()

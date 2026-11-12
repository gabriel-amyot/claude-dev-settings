"""Semantic store checks. Fixtures never touch the installed catalog."""
import concurrent.futures
import multiprocessing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store, ValidationError, stable_id, utc_now


WHEN = "2026-10-26T12:00:00Z"


def capability(identity="skill-one", **changes):
    return dict(id=identity, kind="skill", name=identity, description="Fixture skill",
                source_path="/fixture/" + identity + "/SKILL.md", revision="abc123",
                discovered_at=WHEN, **changes)


def usage(identity="use-one", **changes):
    value = dict(id=identity, capability_id="skill-one", host="codex", role="reviewer",
                 session_id="session-fixture", occurred_at=WHEN, signal="loaded",
                 source_path="/fixture/session.jsonl", source_ref="line:7")
    value.update(changes)
    return value


def append_worker(arguments):
    database, index = arguments
    with Store(database, backup_before_write=False) as store:
        # All workers race to insert one common event plus their unique event.
        store.record("usage", usage("shared"), producer="collector")
        return store.record("usage", usage(f"worker-{index}"), producer="collector")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "catalog.sqlite"
        self.store = Store(self.path)
        self.store.record("capability", capability(), producer="collector")

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_schema_is_strict_and_every_domain_exists(self):
        tables = {row["name"]: row for row in self.store.rows("SELECT name,sql FROM sqlite_master WHERE type='table'")}
        expected = {"capabilities", "availability", "dependencies", "usage_events", "frictions",
                    "eval_suites", "eval_runs", "outcomes", "decisions", "coverage", "artifacts"}
        self.assertEqual(expected, set(tables))
        self.assertTrue(all("STRICT" in row["sql"] for row in tables.values()))
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.conn.execute("INSERT INTO usage_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("bad", "skill-one", "codex", "reviewer", "s", WHEN, "loaded", "p", "r", None, "unknown", 1, "agent"))

    def test_eval_suite_definition_is_metadata_with_owned_validated_historical_date(self):
        suite = dict(id="registered", suite_id="one/check", capability_id="skill-one", layer="A",
                     source_path="/fixture/manifest.yaml", observed_at=WHEN, last_green="2026-09-01")
        with self.assertRaises(PermissionError):
            self.store.record("eval_suite", suite, producer="agent")
        self.assertTrue(self.store.record("eval_suite", suite, producer="collector"))
        self.assertFalse(self.store.record("eval_suite", suite, producer="collector"))
        self.assertEqual([], self.store.rows("SELECT * FROM eval_runs"))
        with self.assertRaises(ValidationError):
            self.store.record("eval_suite", {**suite, "last_green": "recently"}, producer="collector")

    def test_reference_replacement_is_atomic_and_preserves_history(self):
        self.store.record("capability", capability("other"), producer="collector")
        self.store.record("usage", usage(), producer="collector")
        references = [{"target_id": "other", "evidence": "fixture reference"}]
        self.store.replace_references("skill-one", references)
        self.assertEqual(0, self.store.replace_references("skill-one", references))
        with self.assertRaises(PermissionError):
            self.store.replace_references("skill-one", [], producer="agent")
        with self.assertRaises(ValidationError):
            self.store.replace_references("skill-one", [{"target_id": "missing", "evidence": "bad"}])
        self.assertEqual("other", self.store.rows("SELECT target_id FROM dependencies")[0]["target_id"])
        self.store.replace_references("skill-one", [])
        self.assertEqual([], self.store.rows("SELECT * FROM dependencies"))
        self.assertEqual(1, len(self.store.rows("SELECT * FROM usage_events")))

    def test_exact_replay_does_not_inflate_usage(self):
        record = usage()
        self.assertTrue(self.store.record("usage", record, producer="collector"))
        self.assertFalse(self.store.record("usage", record, producer="collector"))
        self.assertEqual(1, self.store.rows("SELECT COUNT(*) AS n FROM usage_events")[0]["n"])
        with self.assertRaisesRegex(ValidationError, "Conflicting immutable"):
            self.store.record("usage", usage(signal="invoked"), producer="collector")
        self.assertEqual("loaded", self.store.rows("SELECT signal FROM usage_events")[0]["signal"])

    def test_metadata_updates_are_scoped_to_stable_key(self):
        original = capability()
        self.assertFalse(self.store.record("capability", original, producer="collector"))
        changed = {**original, "revision": "new-revision"}
        self.assertTrue(self.store.record("capability", changed, producer="collector"))
        self.assertEqual([{"revision": "new-revision"}], self.store.rows("SELECT revision FROM capabilities"))
        self.assertEqual(1, self.store.rows("SELECT COUNT(*) AS n FROM capabilities")[0]["n"])

    def test_rejects_unknown_fields_wrong_types_and_invented_enum_values(self):
        invalid = [usage(extra="ignored?"), usage(count=True), usage(count=0), usage(count=1.5),
                   usage(host="made-up"), usage(signal="mentioned"), usage(occurred_at="yesterday"),
                   usage(occurred_at="2026-10-26T12:00:00"), usage(source_path=""), usage(session_id=None)]
        for record in invalid:
            with self.subTest(record=record):
                with self.assertRaises(ValidationError):
                    self.store.record("usage", record, producer="collector")
        with self.assertRaises(ValidationError):
            self.store.record("usage", {}, producer="collector")
        self.assertEqual([], self.store.rows("SELECT * FROM usage_events"))

    def test_sqlite_preserves_original_events_even_if_a_caller_bypasses_helper(self):
        self.store.record("usage", usage(), producer="collector")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            self.store.conn.execute("UPDATE usage_events SET count=900 WHERE id='use-one'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            self.store.conn.execute("DELETE FROM usage_events")
        self.assertEqual(1, self.store.rows("SELECT count FROM usage_events")[0]["count"])

    def test_foreign_key_failure_rolls_back_and_connection_remains_usable(self):
        with self.assertRaises(ValidationError):
            self.store.record("usage", usage(capability_id="missing"), producer="collector")
        self.assertTrue(self.store.record("usage", usage(), producer="collector"))

    def test_agent_cannot_forge_a_pass_or_approve_a_retirement(self):
        evaluation = dict(id="eval-one", suite_id="suite-one", capability_id="skill-one", occurred_at=WHEN,
                          outcome="pass", source_path="/fixture/report.md", source_ref="suite-one")
        with self.assertRaises(PermissionError):
            self.store.record("eval", evaluation, producer="agent")
        with self.assertRaises(PermissionError):
            self.store.record("eval", evaluation, producer="collector")
        self.assertTrue(self.store.record("eval", evaluation, producer="eval-runner"))
        decision = dict(id="decision-one", capability_id="skill-one", occurred_at=WHEN, action="retire",
                        status="approved", rationale="An agent prefers this", authority="agent", evidence="session:x")
        with self.assertRaises(PermissionError):
            self.store.record("decision", decision, producer="agent")
        self.assertTrue(self.store.record("decision", {**decision, "status": "proposed"}))
        self.assertEqual("proposed", self.store.rows("SELECT status FROM decisions")[0]["status"])
        with self.assertRaises(PermissionError):
            self.store.record("capability", capability("other"), producer="maintainer")

    def test_friction_resolution_is_a_separate_attributed_event(self):
        observation = dict(id="friction-one", capability_id="skill-one", host="codex", role="reviewer",
                           session_id="session-one", occurred_at=WHEN, summary="Missing helper",
                           impact="Could not complete", evidence="fixture:7")
        self.assertTrue(self.store.record("friction", observation))
        resolution = {**observation, "id": "resolution-one", "status": "resolved", "resolves_id": "friction-one"}
        with self.assertRaises(PermissionError):
            self.store.record("friction", resolution)
        self.assertTrue(self.store.record("friction", resolution, producer="maintainer"))
        self.assertFalse(self.store.record("friction", resolution, producer="maintainer"))
        with self.assertRaises(ValidationError):
            self.store.record("friction", {**resolution, "id": "resolution-two"}, producer="maintainer")
        self.assertEqual(["open", "resolved"], [row["status"] for row in self.store.rows("SELECT status FROM frictions ORDER BY id")])

    def test_resolution_cannot_target_another_capability(self):
        self.store.record("capability", capability("other"), producer="collector")
        common = dict(host="codex", role="reviewer", session_id="session", occurred_at=WHEN,
                      summary="Problem", impact="Blocked", evidence="fixture")
        self.store.record("friction", dict(id="original", capability_id="skill-one", **common))
        with self.assertRaises(ValidationError):
            self.store.record("friction", dict(id="resolution", capability_id="other", status="resolved",
                                               resolves_id="original", **common), producer="maintainer")

    def test_rows_cannot_mutate_even_through_a_with_clause_or_pragma(self):
        for sql in ["DELETE FROM capabilities", "PRAGMA writable_schema=ON", "CREATE TABLE x (a)",
                    "WITH n AS (SELECT 1) DELETE FROM capabilities", "BEGIN IMMEDIATE"]:
            with self.subTest(sql=sql):
                with self.assertRaises(ValidationError):
                    self.store.rows(sql)
        self.assertEqual([{"n": 1}], self.store.rows("WITH n AS (SELECT 1 AS n) SELECT * FROM n"))
        self.assertEqual([{"name": "skill-one"}], self.store.rows("SELECT name FROM capabilities"))

    def test_backup_is_consistent_without_replaying_later_writes(self):
        target = Path(self.directory.name) / "backup.sqlite"
        self.store.record("usage", usage(), producer="collector")
        self.store.backup(target)
        self.store.record("usage", usage("later"), producer="collector")
        with sqlite3.connect(target) as connection:
            self.assertEqual("ok", connection.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0])
        self.assertEqual(2, self.store.rows("SELECT COUNT(*) AS n FROM usage_events")[0]["n"])
        with self.assertRaises(ValidationError):
            self.store.backup(self.path)

    def test_existing_populated_database_snapshots_once_before_actual_mutation(self):
        with Store(self.path) as reopened:
            self.assertFalse(reopened.record("capability", capability(), producer="collector"))
            self.assertEqual([], list(Path(self.directory.name).glob("backups/*")))
            reopened.record("usage", usage(), producer="collector")
            reopened.record("usage", usage("later"), producer="collector")
        backups = list(Path(self.directory.name).glob("backups/*.sqlite"))
        self.assertEqual(1, len(backups))
        with sqlite3.connect(backups[0]) as connection:
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0])
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0])

    def test_multiple_processes_share_one_database_without_lost_or_duplicate_events(self):
        with concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("spawn")) as pool:
            results = list(pool.map(append_worker, [(str(self.path), i) for i in range(12)]))
        self.assertEqual([True] * 12, results)
        self.assertEqual(13, self.store.rows("SELECT COUNT(*) AS n FROM usage_events")[0]["n"])

    def test_dates_keep_original_precision_and_defaults_are_validated(self):
        self.store.record("usage", usage(occurred_at="2026-10-26", count=None), producer="collector")
        row = self.store.rows("SELECT occurred_at,count FROM usage_events")[0]
        self.assertEqual({"occurred_at": "2026-10-26", "count": 1}, row)
        self.assertNotEqual(stable_id("a", "bc"), stable_id("ab", "c"))
        self.assertEqual(stable_id("a", "b"), stable_id("a", "b"))
        self.assertTrue(utc_now().endswith("Z"))


if __name__ == "__main__":
    unittest.main()

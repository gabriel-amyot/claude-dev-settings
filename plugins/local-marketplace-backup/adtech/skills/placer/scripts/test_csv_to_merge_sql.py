#!/usr/bin/env python3
"""Unit tests for csv_to_merge_sql.py (AC-1, KTP-695).

The generator turns an entity-match bridge CSV into a ready-to-run, idempotent
MERGE .sql file targeting klever_placer_entity_map. These tests pin the
contract that makes the SQL safe to paste into bq CLI or the web console:

  - CREATE TABLE IF NOT EXISTS preamble so a first run on an empty env works.
  - Only HIGH-confidence, chain-verified rows reach the bridge (the 80% gate's
    downstream guard — never insert MEDIUM/LOW/UNVERIFIED/UNMATCHED).
  - MERGE keyed on klever_location_id so re-running never duplicates a row
    (idempotency — the whole point of the AC).
  - advertiser_id is injected (the CSV does not carry it; the bridge needs it).
  - String literals are escaped (apostrophes in store names must not break SQL).

stdlib only. Run: python3 test_csv_to_merge_sql.py
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csv_to_merge_sql as gen  # noqa: E402


DEV_PROJECT = "prj-d-grid-insigt-3vm2fcstbw"
TABLE_FQN = f"`{DEV_PROJECT}.dts_external_data.klever_placer_entity_map`"


def sample_rows():
    """Mimics the entity-match bridge CSV: a HIGH match, a LOW match, an
    unmatched row, and a chain-unverified row. Only the HIGH+verified row
    should reach the bridge."""
    return [
        {
            "klever_location_id": "51001",
            "placer_entity_id": "venue:abc123",
            "entity_type": "venue",
            "location_name": "Shrimp Basket - Gulf Shores",
            "address": "100 E Beach Blvd",
            "city": "Gulf Shores",
            "state": "AL",
            "match_confidence": "HIGH",
            "alternative_entity_ids": "",
            "notes": "",
        },
        {
            "klever_location_id": "51002",
            "placer_entity_id": "venue:def456",
            "entity_type": "venue",
            "location_name": "Cap'n Jack's Wharf",  # apostrophe -> escaping
            "address": "200 Main St",
            "city": "Pensacola",
            "state": "FL",
            "match_confidence": "HIGH",
            "alternative_entity_ids": "",
            "notes": "",
        },
        {
            "klever_location_id": "51003",
            "placer_entity_id": "venue:low789",
            "entity_type": "venue",
            "location_name": "Shrimp Basket - Mobile",
            "address": "300 Dauphin St",
            "city": "Mobile",
            "state": "AL",
            "match_confidence": "LOW",
            "alternative_entity_ids": "",
            "notes": "only city matched",
        },
        {
            "klever_location_id": "51004",
            "placer_entity_id": "",
            "entity_type": "",
            "location_name": "Shrimp Basket - Tuscaloosa",
            "address": "400 University Blvd",
            "city": "Tuscaloosa",
            "state": "AL",
            "match_confidence": "NONE",
            "alternative_entity_ids": "",
            "notes": "unmatched",
        },
        {
            "klever_location_id": "51005",
            "placer_entity_id": "complex:notinchain",
            "entity_type": "complex",
            "location_name": "Shrimp Basket - Orange Beach",
            "address": "500 Canal Rd",
            "city": "Orange Beach",
            "state": "AL",
            "match_confidence": "HIGH",
            "alternative_entity_ids": "",
            "notes": "UNVERIFIED: not in chain",
        },
    ]

    # ----- generation contract -----

class TestGenerateMergeSql(unittest.TestCase):
    def setUp(self):
        self.sql = gen.generate_merge_sql(
            sample_rows(), advertiser_id=51, project=DEV_PROJECT
        )

    def test_create_table_if_not_exists_preamble(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS", self.sql)
        self.assertIn(TABLE_FQN, self.sql)
        # schema columns pinned (created_at is server-defaulted)
        self.assertIn("klever_location_id INT64", self.sql)
        self.assertIn("placer_entity_id STRING", self.sql)
        self.assertIn("advertiser_id INT64", self.sql)
        self.assertIn("location_name STRING", self.sql)

    def test_merge_keyed_on_location_id_for_idempotency(self):
        self.assertIn("MERGE", self.sql)
        self.assertIn("T.klever_location_id = S.klever_location_id", self.sql)
        self.assertIn("WHEN MATCHED THEN", self.sql)
        self.assertIn("UPDATE SET", self.sql)
        self.assertIn("WHEN NOT MATCHED THEN", self.sql)
        self.assertIn("INSERT", self.sql)

    def test_only_high_verified_rows_inserted(self):
        # HIGH + verified
        self.assertIn("venue:abc123", self.sql)
        self.assertIn("venue:def456", self.sql)
        # LOW -> excluded
        self.assertNotIn("venue:low789", self.sql)
        # unmatched -> excluded
        self.assertNotIn("51004", self.sql)
        # chain-unverified HIGH -> excluded
        self.assertNotIn("complex:notinchain", self.sql)

    def test_advertiser_id_injected(self):
        self.assertIn("51 AS advertiser_id", self.sql)

    def test_apostrophe_escaped(self):
        # GoogleSQL uses backslash escaping, NOT doubled quotes. Cap'n -> Cap\'n
        self.assertIn("Cap\\'n Jack\\'s Wharf", self.sql)
        # the raw unescaped form must not appear as a standalone literal value
        self.assertNotIn("'Cap'n Jack's Wharf'", self.sql)

    def test_deterministic_output(self):
        again = gen.generate_merge_sql(
            sample_rows(), advertiser_id=51, project=DEV_PROJECT
        )
        self.assertEqual(self.sql, again)

    def test_empty_after_filter_raises(self):
        only_low = [r for r in sample_rows() if r["match_confidence"] == "LOW"]
        with self.assertRaises(gen.NoMatchesError):
            gen.generate_merge_sql(only_low, advertiser_id=51, project=DEV_PROJECT)

    # ----- CSV reader -----

class TestReadBridgeCsv(unittest.TestCase):
    def test_reads_header_and_rows(self):
        header = (
            "klever_location_id,placer_entity_id,entity_type,location_name,"
            "address,city,state,match_confidence,alternative_entity_ids,notes\n"
        )
        body = "51001,venue:abc123,venue,Shrimp Basket - Gulf Shores,100 E Beach Blvd,Gulf Shores,AL,HIGH,,\n"
        with tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(header + body)
            path = f.name
        try:
            rows = gen.read_bridge_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["placer_entity_id"], "venue:abc123")
            self.assertEqual(rows[0]["match_confidence"], "HIGH")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

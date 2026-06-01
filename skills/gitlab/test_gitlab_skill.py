#!/usr/bin/env python3
"""Tests for gitlab_skill.py safeguards, project resolution, and core logic.

Run: python3 -m unittest test_gitlab_skill -v
From: ~/.claude-shared-config/skills/gitlab/
"""
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

# Add skill directory to path so we can import the module
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)

import gitlab_skill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_INDEX = {
    "version": 1,
    "organizations": {
        "test": {
            "app-proximity-report": {"id": 577, "path": "grp/app-proximity-report"},
            "proximity-report": {"id": 577, "path": "grp/app-proximity-report"},
            "proximityreport": {"id": 577, "path": "grp/app-proximity-report"},
            "eqs": {"id": 224, "path": "supervisr/eqs"},
            "lead-lifecycle": {"id": 225, "path": "supervisr/lead-lifecycle"},
            "leadlifecycle": {"id": 225, "path": "supervisr/lead-lifecycle"},
        }
    }
}

ORG_CONFIG = {
    "organizations": {
        "klever": {"local_path": "/Users/gab/Developer/grp-beklever-com"},
        "supervisrai": {"local_path": "/Users/gab/Developer/supervisr-ai"},
    },
    "default_org": "supervisrai"
}


def _set_test_globals():
    """Set module globals so functions that reference them don't crash."""
    gitlab_skill.gitlab_url = "https://test.example.com"
    gitlab_skill.headers = {"PRIVATE-TOKEN": "test-token", "Content-Type": "application/json"}
    gitlab_skill.current_org = {"name": "test", "url": "https://test.example.com"}


# ===========================================================================
# SAFEGUARD TESTS: Prod protection
# ===========================================================================

class TestBlockedRefs(unittest.TestCase):
    """BLOCKED_REFS must cover all production-adjacent branches."""

    def test_main_blocked(self):
        self.assertIn("main", gitlab_skill.BLOCKED_REFS)

    def test_master_blocked(self):
        self.assertIn("master", gitlab_skill.BLOCKED_REFS)

    def test_prod_blocked(self):
        self.assertIn("prod", gitlab_skill.BLOCKED_REFS)

    def test_production_blocked(self):
        self.assertIn("production", gitlab_skill.BLOCKED_REFS)

    def test_uat_blocked(self):
        self.assertIn("uat", gitlab_skill.BLOCKED_REFS)


class TestBlockedScopes(unittest.TestCase):
    """BLOCKED_SCOPES must cover prod/uat CI/CD variable scopes."""

    def test_production_blocked(self):
        self.assertIn("production", gitlab_skill.BLOCKED_SCOPES)

    def test_prod_blocked(self):
        self.assertIn("prod", gitlab_skill.BLOCKED_SCOPES)

    def test_uat_blocked(self):
        self.assertIn("uat", gitlab_skill.BLOCKED_SCOPES)

    def test_main_blocked(self):
        self.assertIn("main", gitlab_skill.BLOCKED_SCOPES)


class TestMaxRetriesConstant(unittest.TestCase):
    """MAX_API_RETRIES must exist and be exactly 2."""

    def test_exists_and_equals_2(self):
        self.assertEqual(gitlab_skill.MAX_API_RETRIES, 2)


class TestTriggerPipelineSafeguard(unittest.TestCase):
    """trigger_pipeline must refuse all prod-adjacent refs."""

    def test_blocks_main(self):
        result = gitlab_skill.trigger_pipeline(123, ref="main")
        self.assertIn("error", result)

    def test_blocks_master(self):
        result = gitlab_skill.trigger_pipeline(123, ref="master")
        self.assertIn("error", result)

    def test_blocks_prod(self):
        result = gitlab_skill.trigger_pipeline(123, ref="prod")
        self.assertIn("error", result)

    def test_blocks_production(self):
        result = gitlab_skill.trigger_pipeline(123, ref="production")
        self.assertIn("error", result)

    def test_blocks_uat(self):
        result = gitlab_skill.trigger_pipeline(123, ref="uat")
        self.assertIn("error", result)

    def test_blocks_case_insensitive(self):
        result = gitlab_skill.trigger_pipeline(123, ref="MAIN")
        self.assertIn("error", result)

    def test_allows_dev(self):
        _set_test_globals()
        with patch.object(gitlab_skill, "api_request") as mock_api:
            mock_api.return_value = {
                "id": 1, "status": "pending", "ref": "dev", "web_url": "http://example.com"
            }
            result = gitlab_skill.trigger_pipeline(123, ref="dev")
            self.assertNotIn("error", result)
            mock_api.assert_called_once()


class TestVariablesSafeguard(unittest.TestCase):
    """manage_variables must block 'set' on prod/uat scopes."""

    def test_blocks_production_scope(self):
        result = gitlab_skill.manage_variables(123, "set", key="K", value="V", scope="production")
        self.assertIn("error", result)
        self.assertIn("BLOCKED", result["error"])

    def test_blocks_prod_scope(self):
        result = gitlab_skill.manage_variables(123, "set", key="K", value="V", scope="prod")
        self.assertIn("error", result)

    def test_blocks_uat_scope(self):
        result = gitlab_skill.manage_variables(123, "set", key="K", value="V", scope="uat")
        self.assertIn("error", result)

    def test_blocks_main_scope(self):
        result = gitlab_skill.manage_variables(123, "set", key="K", value="V", scope="main")
        self.assertIn("error", result)

    def test_allows_dev_scope(self):
        _set_test_globals()
        with patch.object(gitlab_skill, "api_request") as mock_api:
            mock_api.return_value = {"key": "K", "value": "V", "environment_scope": "dev"}
            result = gitlab_skill.manage_variables(123, "set", key="K", value="V", scope="dev")
            self.assertTrue(mock_api.called)

    def test_list_allowed_any_scope(self):
        """Read-only operations should work regardless of scope."""
        _set_test_globals()
        with patch.object(gitlab_skill, "api_request") as mock_api:
            mock_api.return_value = [
                {"key": "K", "value": "V", "environment_scope": "*",
                 "protected": False, "masked": False}
            ]
            result = gitlab_skill.manage_variables(123, "list")
            self.assertIsInstance(result, list)


# ===========================================================================
# SAFEGUARD TESTS: Retry behavior
# ===========================================================================

class TestApiRequestRetry(unittest.TestCase):
    """api_request must retry on 5xx, never on 4xx or redirects."""

    def setUp(self):
        _set_test_globals()

    def test_success_first_try(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": "ok"}

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertEqual(result, {"data": "ok"})
            self.assertEqual(mock_get.call_count, 1)

    def test_retries_on_500(self):
        fail = MagicMock()
        fail.status_code = 500
        fail.text = "Internal Server Error"

        with patch("requests.get", return_value=fail) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertIn("error", result)
            # 1 original + 2 retries = 3 total
            self.assertEqual(mock_get.call_count, 3)

    def test_success_after_one_retry(self):
        fail = MagicMock()
        fail.status_code = 502
        fail.text = "Bad Gateway"

        ok = MagicMock()
        ok.status_code = 200
        ok.json.return_value = {"recovered": True}

        with patch("requests.get", side_effect=[fail, ok]) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertEqual(result, {"recovered": True})
            self.assertEqual(mock_get.call_count, 2)

    def test_no_retry_on_404(self):
        fail = MagicMock()
        fail.status_code = 404
        fail.text = "Not Found"

        with patch("requests.get", return_value=fail) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertIn("error", result)
            self.assertEqual(mock_get.call_count, 1)

    def test_no_retry_on_401(self):
        fail = MagicMock()
        fail.status_code = 401
        fail.text = "Unauthorized"

        with patch("requests.get", return_value=fail) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertEqual(mock_get.call_count, 1)

    def test_no_retry_on_redirect(self):
        fail = MagicMock()
        fail.status_code = 302

        with patch("requests.get", return_value=fail) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertIn("error", result)
            self.assertIn("IAP", result["error"])
            self.assertEqual(mock_get.call_count, 1)

    def test_retries_on_connection_error(self):
        import requests as req
        ok = MagicMock()
        ok.status_code = 200
        ok.json.return_value = {"recovered": True}

        with patch("requests.get", side_effect=[req.ConnectionError("timeout"), ok]) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertEqual(result, {"recovered": True})
            self.assertEqual(mock_get.call_count, 2)

    def test_connection_error_exhausts_retries(self):
        import requests as req

        with patch("requests.get", side_effect=req.ConnectionError("timeout")) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertIn("error", result)
            self.assertEqual(mock_get.call_count, 3)


# ===========================================================================
# CORE LOGIC TESTS: Project resolution
# ===========================================================================

class TestResolveProjectId(unittest.TestCase):
    """Project name to ID resolution."""

    def test_numeric_int_passthrough(self):
        self.assertEqual(gitlab_skill.resolve_project_id(577), 577)

    def test_numeric_string_passthrough(self):
        self.assertEqual(gitlab_skill.resolve_project_id("577"), 577)

    def test_exact_name_match(self):
        with patch.object(gitlab_skill, "load_index", return_value=MOCK_INDEX):
            self.assertEqual(gitlab_skill.resolve_project_id("eqs", "test"), 224)

    def test_hyphenated_name(self):
        with patch.object(gitlab_skill, "load_index", return_value=MOCK_INDEX):
            self.assertEqual(gitlab_skill.resolve_project_id("lead-lifecycle", "test"), 225)

    def test_collapsed_match(self):
        with patch.object(gitlab_skill, "load_index", return_value=MOCK_INDEX):
            self.assertEqual(gitlab_skill.resolve_project_id("leadlifecycle", "test"), 225)

    def test_case_insensitive(self):
        with patch.object(gitlab_skill, "load_index", return_value=MOCK_INDEX):
            self.assertEqual(gitlab_skill.resolve_project_id("EQS", "test"), 224)

    def test_not_found_returns_none(self):
        with patch.object(gitlab_skill, "load_index", return_value=MOCK_INDEX):
            self.assertIsNone(gitlab_skill.resolve_project_id("nonexistent", "test"))


# ===========================================================================
# CORE LOGIC TESTS: Org detection
# ===========================================================================

class TestDetectOrgFromCwd(unittest.TestCase):
    """CWD-based org auto-detection via longest prefix match."""

    def test_klever_path(self):
        with patch("os.getcwd", return_value="/Users/gab/Developer/grp-beklever-com/project-management"):
            self.assertEqual(gitlab_skill.detect_org_from_cwd(ORG_CONFIG), "klever")

    def test_supervisr_path(self):
        with patch("os.getcwd", return_value="/Users/gab/Developer/supervisr-ai/faas"):
            self.assertEqual(gitlab_skill.detect_org_from_cwd(ORG_CONFIG), "supervisrai")

    def test_unknown_falls_back_to_default(self):
        with patch("os.getcwd", return_value="/tmp/random"):
            self.assertEqual(gitlab_skill.detect_org_from_cwd(ORG_CONFIG), "supervisrai")

    def test_longest_prefix_wins(self):
        config = {
            "organizations": {
                "parent": {"local_path": "/Users/gab/Developer"},
                "child": {"local_path": "/Users/gab/Developer/grp-beklever-com"},
            },
            "default_org": "parent"
        }
        with patch("os.getcwd", return_value="/Users/gab/Developer/grp-beklever-com/tickets"):
            self.assertEqual(gitlab_skill.detect_org_from_cwd(config), "child")


# ===========================================================================
# CORE LOGIC TESTS: Formatters
# ===========================================================================

class TestFormatters(unittest.TestCase):
    """compact/full formatters extract the right fields."""

    def test_compact_group_excludes_extras(self):
        raw = {"id": 1, "name": "test", "path": "test", "full_path": "org/test", "extra": "ignored"}
        result = gitlab_skill.compact_group(raw)
        self.assertEqual(result["id"], 1)
        self.assertNotIn("extra", result)

    def test_compact_repo_excludes_visibility(self):
        raw = {"id": 1, "name": "r", "path": "r", "path_with_namespace": "org/r", "visibility": "private"}
        result = gitlab_skill.compact_repo(raw)
        self.assertNotIn("visibility", result)

    def test_full_repo_includes_visibility(self):
        raw = {"id": 1, "name": "r", "path": "r", "path_with_namespace": "org/r",
               "visibility": "private", "default_branch": "dev", "web_url": "http://x.com"}
        result = gitlab_skill.full_repo(raw)
        self.assertEqual(result["visibility"], "private")
        self.assertEqual(result["default_branch"], "dev")


# ===========================================================================
# CORE LOGIC TESTS: IAP cookie parsing
# ===========================================================================

class TestIapTokenParsing(unittest.TestCase):
    """IAP cookie file parsing."""

    def test_valid_cookie(self):
        future = int(time.time()) + 86400
        content = f".example.com\tTRUE\t/\tTRUE\t{future}\tiap\tmy-secret-token"

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "user@example.com.cookie"), "w") as f:
                f.write(content)

            with patch.object(gitlab_skill, "IAP_COOKIE_DIR", tmpdir):
                token = gitlab_skill.get_iap_token("https://example.com")
                self.assertEqual(token, "my-secret-token")

    def test_expired_cookie(self):
        past = int(time.time()) - 86400
        content = f".example.com\tTRUE\t/\tTRUE\t{past}\tiap\texpired"

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "example.com.cookie"), "w") as f:
                f.write(content)

            with patch.object(gitlab_skill, "IAP_COOKIE_DIR", tmpdir), \
                 patch.object(gitlab_skill, "IAP_HELPER_BIN", "/nonexistent"):
                token = gitlab_skill.get_iap_token("https://example.com")
                self.assertIsNone(token)

    def test_empty_cookie(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "example.com.cookie"), "w") as f:
                f.write("")

            with patch.object(gitlab_skill, "IAP_COOKIE_DIR", tmpdir), \
                 patch.object(gitlab_skill, "IAP_HELPER_BIN", "/nonexistent"):
                token = gitlab_skill.get_iap_token("https://example.com")
                self.assertIsNone(token)


# ===========================================================================
# SAFEGUARD TESTS: MR create to prod blocked
# ===========================================================================

class TestMrCreateSafeguard(unittest.TestCase):
    """MR creation targeting blocked refs should error (pipeline would auto-run)."""

    def test_mr_create_missing_fields_caught(self):
        result = gitlab_skill.manage_merge_request(123, "create", title=None, source=None, target=None)
        self.assertIn("error", result)

    def test_mr_unknown_action(self):
        result = gitlab_skill.manage_merge_request(123, "bogus")
        self.assertIn("error", result)


# ===========================================================================
# GAP TESTS: Rate limiting (429)
# ===========================================================================

class TestRateLimitHandling(unittest.TestCase):
    """429 responses should retry with backoff, respecting Retry-After."""

    def setUp(self):
        _set_test_globals()

    def test_retries_on_429(self):
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.text = "Rate limited"
        rate_limited.headers = {"Retry-After": "1"}

        ok = MagicMock()
        ok.status_code = 200
        ok.json.return_value = {"recovered": True}

        with patch("requests.get", side_effect=[rate_limited, ok]) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertEqual(result, {"recovered": True})
            self.assertEqual(mock_get.call_count, 2)

    def test_429_exhausts_retries(self):
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.text = "Rate limited"
        rate_limited.headers = {"Retry-After": "1"}

        with patch("requests.get", return_value=rate_limited) as mock_get:
            result = gitlab_skill.api_request("/test")
            self.assertIn("error", result)
            self.assertIn("Rate limited", result["error"])
            self.assertEqual(mock_get.call_count, 3)


# ===========================================================================
# GAP TESTS: Shared trace_utils
# ===========================================================================

class TestTraceUtils(unittest.TestCase):
    """trace_utils shared parsing functions."""

    def test_strip_ansi(self):
        from trace_utils import strip_ansi
        raw = "\x1b[32mSuccess\x1b[0m: all good"
        self.assertEqual(strip_ansi(raw), "Success: all good")

    def test_extract_plan_stats_found(self):
        from trace_utils import extract_plan_stats
        text = "Plan: 3 to add, 1 to change, 0 to destroy."
        add, change, destroy = extract_plan_stats(text)
        self.assertEqual((add, change, destroy), (3, 1, 0))

    def test_extract_plan_stats_not_found(self):
        from trace_utils import extract_plan_stats
        add, change, destroy = extract_plan_stats("No plan here")
        self.assertIsNone(add)

    def test_extract_plan_dict(self):
        from trace_utils import extract_plan_dict
        text = "Plan: 2 to add, 0 to change, 1 to destroy."
        result = extract_plan_dict("my-job", text)
        self.assertEqual(result["job"], "my-job")
        self.assertEqual(result["plan_add"], 2)
        self.assertEqual(result["plan_destroy"], 1)

    def test_extract_plan_dict_none(self):
        from trace_utils import extract_plan_dict
        self.assertIsNone(extract_plan_dict("job", "no plan"))

    def test_extract_error_lines(self):
        from trace_utils import extract_error_lines
        text = "line 1 ok\n[ ERROR ] something broke\nline 3 ok\nError: bad thing"
        errors = extract_error_lines(text)
        self.assertEqual(len(errors), 2)
        self.assertIn("something broke", errors[0])

    def test_extract_error_lines_max(self):
        from trace_utils import extract_error_lines
        text = "\n".join([f"Error: line {i}" for i in range(20)])
        errors = extract_error_lines(text, max_lines=5)
        self.assertEqual(len(errors), 5)


# ===========================================================================
# GAP TESTS: File locking on index
# ===========================================================================

class TestIndexFileLocking(unittest.TestCase):
    """save_index should use file locking."""

    def test_save_index_creates_lock_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "test_index.json")
            lock_path = index_path + ".lock"

            with patch.object(gitlab_skill, "INDEX_FILE", index_path):
                gitlab_skill.save_index({"version": 1, "organizations": {}})

            self.assertTrue(os.path.exists(index_path))
            self.assertTrue(os.path.exists(lock_path))

            with open(index_path) as f:
                data = json.load(f)
            self.assertEqual(data["version"], 1)


if __name__ == "__main__":
    unittest.main()

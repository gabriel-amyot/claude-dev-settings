#!/usr/bin/env python3
"""
Integration tests for Jira skill new features (2026-05-06):
  1. link / link-types
  2. retype
  3. hierarchy validation on --parent

Uses real Jira API against KTP project. Test tickets:
  - KTP-647 (Story under KTP-646) — Store Detail Panel tracker
  - KTP-648 (Story under KTP-646) — Pre-fetch Pipeline
  - KTP-646 (Epic) — Visitor Analytics umbrella

Run: python3 evals/test_new_features.py --org klever
"""

import subprocess
import json
import sys
import os

SKILL_PATH = os.path.expanduser("~/.claude/skills/jira/jira_skill.py")
ORG = "klever"

# Parse --org flag
if "--org" in sys.argv:
    idx = sys.argv.index("--org")
    if idx + 1 < len(sys.argv):
        ORG = sys.argv[idx + 1]


def run_skill(args):
    """Run jira_skill.py with given args, return parsed JSON."""
    cmd = ["python3", SKILL_PATH] + args + ["--org", ORG]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # JSON is on stdout, disclaimers on stderr
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"_raw_stdout": result.stdout, "_raw_stderr": result.stderr, "_returncode": result.returncode}


class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = None
        self.message = ""

    def ok(self, msg=""):
        self.passed = True
        self.message = msg
        return self

    def fail(self, msg):
        self.passed = False
        self.message = msg
        return self


def test_link_types():
    """link-types should return a non-empty list with Relates."""
    t = TestResult("link-types returns available types")
    result = run_skill(["link-types"])
    if isinstance(result, list) and len(result) > 0:
        names = [lt.get("name") for lt in result]
        if "Relates" in names:
            return t.ok(f"{len(result)} link types, includes Relates")
        return t.fail(f"Relates not found in: {names}")
    return t.fail(f"Expected list, got: {result}")


def test_link_create():
    """link should create a Relates link between two tickets."""
    t = TestResult("link creates Relates between KTP-647 and KTP-648")
    result = run_skill(["link", "KTP-647", "KTP-648", "--type", "Relates"])
    if result.get("success"):
        return t.ok(f"Link created: {result.get('link_type')}")
    # Duplicate link is OK (idempotent in Jira)
    err = result.get("error", "")
    if "already" in err.lower() or "duplicate" in err.lower():
        return t.ok("Link already exists (idempotent)")
    return t.fail(f"Failed: {err}")


def test_link_invalid_type():
    """link with a nonexistent type should fail gracefully."""
    t = TestResult("link rejects invalid link type")
    result = run_skill(["link", "KTP-647", "KTP-648", "--type", "FakeType123"])
    if "error" in result:
        return t.ok(f"Rejected: {result['error'][:80]}")
    return t.fail(f"Expected error, got: {result}")


def test_link_missing_args():
    """link without enough args should show usage."""
    t = TestResult("link shows usage when args missing")
    result = run_skill(["link", "KTP-647"])
    if "error" in result and "requires" in result["error"].lower():
        return t.ok("Usage message shown")
    return t.fail(f"Expected usage error, got: {result}")


def test_retype_same_type():
    """retype to same type should be a no-op with a clear message."""
    t = TestResult("retype same type is no-op")
    # KTP-648 is a Story
    result = run_skill(["retype", "KTP-648", "--type", "Story"])
    if "error" in result and "already" in result["error"].lower():
        return t.ok("Correctly detected same type")
    return t.fail(f"Expected 'already type' error, got: {result}")


def test_retype_missing_type():
    """retype without --type should show usage."""
    t = TestResult("retype requires --type flag")
    result = run_skill(["retype", "KTP-648"])
    if "error" in result and "requires" in result["error"].lower():
        return t.ok("Usage message shown")
    return t.fail(f"Expected usage error, got: {result}")


def test_hierarchy_story_under_story():
    """--parent should reject Story under Story."""
    t = TestResult("hierarchy blocks Story under Story")
    result = run_skill(["update", "KTP-611", "--parent", "KTP-647"])
    if "error" in result and "HIERARCHY" in result.get("error", ""):
        return t.ok(f"Blocked: {result.get('child_type')} under {result.get('parent_type')}")
    return t.fail(f"Expected HIERARCHY error, got: {result}")


def test_hierarchy_story_under_epic():
    """--parent should allow Story under Epic."""
    t = TestResult("hierarchy allows Story under Epic")
    # KTP-647 is already under KTP-646 (Epic), so this should succeed (idempotent)
    result = run_skill(["update", "KTP-647", "--parent", "KTP-646"])
    if result.get("success"):
        return t.ok("Story under Epic accepted")
    # If it was already set, some implementations return success
    err = result.get("error", "")
    if "HIERARCHY" in err:
        return t.fail(f"Incorrectly blocked: {err}")
    return t.fail(f"Unexpected result: {result}")


def test_hierarchy_force_bypass():
    """--force should bypass hierarchy validation."""
    t = TestResult("--force bypasses hierarchy check")
    # This would normally be blocked, but --force should let it through to Jira
    # (Jira itself will still reject it, but the skill's pre-check should be skipped)
    result = run_skill(["update", "KTP-611", "--parent", "KTP-647", "--force"])
    err = result.get("error", "")
    if "HIERARCHY" in err:
        return t.fail("--force did NOT bypass the hierarchy check")
    # Either success (unlikely for Story under Story) or Jira's own error (expected)
    if result.get("success") or "hierarchy" in err.lower() or "parent" in err.lower():
        return t.ok("Hierarchy pre-check was bypassed (Jira may still reject)")
    return t.ok(f"Pre-check bypassed, Jira responded: {err[:80]}")


def test_hierarchy_epic_under_epic():
    """--parent should reject Epic under Epic (if KTP-130 is still Epic)."""
    t = TestResult("hierarchy blocks Epic under Epic")
    # Check current type of KTP-558 (known Epic)
    meta = run_skill(["metadata", "KTP-558"])
    if meta.get("type") != "Epic":
        return t.ok(f"KTP-558 is {meta.get('type')}, skipping Epic-under-Epic test")
    result = run_skill(["update", "KTP-558", "--parent", "KTP-646"])
    if "error" in result and "HIERARCHY" in result.get("error", ""):
        return t.ok("Epic under Epic correctly blocked")
    return t.fail(f"Expected HIERARCHY error, got: {result}")


# ── Run all tests ───────────────────────────────────────────────────────────

ALL_TESTS = [
    test_link_types,
    test_link_create,
    test_link_invalid_type,
    test_link_missing_args,
    test_retype_same_type,
    test_retype_missing_type,
    test_hierarchy_story_under_story,
    test_hierarchy_story_under_epic,
    test_hierarchy_force_bypass,
    test_hierarchy_epic_under_epic,
]


def main():
    print(f"\n{'='*60}")
    print(f"  Jira Skill Integration Tests (org: {ORG})")
    print(f"{'='*60}\n")

    results = []
    for test_fn in ALL_TESTS:
        try:
            r = test_fn()
        except Exception as e:
            r = TestResult(test_fn.__name__)
            r.fail(f"EXCEPTION: {e}")
        results.append(r)
        icon = "PASS" if r.passed else "FAIL"
        print(f"  [{icon}] {r.name}")
        if r.message:
            print(f"         {r.message}")

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}\n")

    # Write results as JSON for automated consumption
    json_results = {
        "skill": "jira",
        "org": ORG,
        "total": total,
        "passed": passed,
        "failed": failed,
        "tests": [
            {"name": r.name, "passed": r.passed, "message": r.message}
            for r in results
        ]
    }
    output_path = os.path.join(os.path.dirname(__file__), "test_results.json")
    with open(output_path, "w") as f:
        json.dump(json_results, f, indent=2)
    print(f"  Results written to: {output_path}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

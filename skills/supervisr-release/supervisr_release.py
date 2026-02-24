#!/usr/bin/env python3
"""
Supervisr Release Skill - Full release pipeline for Supervisr.AI microservices.

Pipeline:
  Phase 1: TEST      -> mvn clean compile test
  Phase 2: TAG+BUILD -> increment patch tag, push, mvn jib:build
  Phase 3: SCHEMA    -> detect GraphQL changes, rover subgraph publish

Usage:
  supervisr-release                # Full pipeline
  supervisr-release --skip-tests   # Skip Phase 1
  supervisr-release --no-build     # Test + tag only (no image, no schema)
  supervisr-release --schema-only  # Only publish schema
  supervisr-release --check-sync   # Check all schemas against Apollo Gateway (dev)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

CONFIG_FILENAME = "supervisr_release_config.json"


def run_command(cmd: str, capture: bool = False, timeout: int = 600) -> Tuple[int, str]:
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True, timeout=timeout)
            return result.returncode, ""
    except subprocess.TimeoutExpired:
        print("  Command timed out")
        return 1, ""
    except Exception as e:
        print(f"  Error running command: {e}")
        return 1, ""


def load_config() -> dict:
    config_path = Path(__file__).parent / CONFIG_FILENAME
    if not config_path.exists():
        print(f"  Config not found: {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)


def detect_service(config: dict) -> Optional[dict]:
    cwd = os.getcwd()
    best_match = None
    best_length = 0
    for name, svc in config["services"].items():
        local_path = svc["local_path"]
        if cwd.startswith(local_path) and len(local_path) > best_length:
            best_match = {**svc, "name": name}
            best_length = len(local_path)
    return best_match


def get_latest_tag() -> Optional[str]:
    returncode, output = run_command(
        "git tag -l | grep -E '^[0-9]+\\.[0-9]+\\.[0-9]+(-dev)?$' | sort -V | tail -1",
        capture=True
    )
    if returncode == 0 and output:
        return output
    return None


def increment_patch_version(tag: str) -> str:
    base = tag.replace("-dev", "")
    parts = base.split(".")
    if len(parts) != 3:
        print(f"  Invalid version format: {tag}")
        sys.exit(1)
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        return f"{major}.{minor}.{patch + 1}-dev"
    except ValueError:
        print(f"  Could not parse version: {tag}")
        sys.exit(1)


def get_git_status_clean() -> bool:
    returncode, output = run_command("git status --porcelain", capture=True)
    return len(output) == 0


def get_current_branch() -> Optional[str]:
    returncode, output = run_command("git rev-parse --abbrev-ref HEAD", capture=True)
    return output if returncode == 0 else None


def get_service_name() -> str:
    pom_path = Path("pom.xml")
    if pom_path.exists():
        returncode, output = run_command(
            "grep '<artifactId>' pom.xml | head -1 | sed 's/.*<artifactId>//;s/<\\/artifactId>.*//'",
            capture=True
        )
        if returncode == 0 and output:
            return output.strip()
    return Path.cwd().name


# Phase 1: Test
def run_tests() -> bool:
    print("\nPhase 1: Running Tests")
    print("   $ mvn clean compile test")
    returncode, _ = run_command("mvn clean compile test", timeout=600)
    if returncode != 0:
        print("   Tests failed. Aborting release.")
        return False
    print("   Tests passed")
    return True


# Phase 2: Tag & Build
def tag_and_push(new_tag: str) -> bool:
    print(f"   Creating tag: {new_tag}")
    returncode, _ = run_command(f"git tag {new_tag}")
    if returncode != 0:
        print("   Failed to create tag")
        return False

    branch = get_current_branch()
    print(f"   Pushing branch {branch}")
    returncode, _ = run_command(f"git push origin {branch}")
    if returncode != 0:
        print("   Failed to push branch")
        return False

    print(f"   Pushing tag {new_tag}")
    returncode, _ = run_command(f"git push origin {new_tag}")
    if returncode != 0:
        print("   Failed to push tag")
        return False

    return True


def build_image(tag: str) -> bool:
    service_name = get_service_name()
    print(f"   Building image: {service_name}:{tag}")
    returncode, _ = run_command(
        f"mvn compile jib:build -Djib.to.tags={tag} -DskipTests",
        timeout=600
    )
    if returncode == 0:
        print("   Image pushed")
        return True
    else:
        print("   Docker build failed")
        return False


# Phase 3: Schema Publish
def detect_schema_changes(latest_tag: Optional[str], schema_path: str) -> bool:
    if not latest_tag:
        return True
    returncode, output = run_command(
        f"git diff {latest_tag} -- {schema_path}",
        capture=True
    )
    return returncode == 0 and len(output) > 0


def prompt_environment(routing_urls: dict) -> Optional[str]:
    envs = ["dev", "sandbox", "uat", "prod"]
    print("   Select environment:")
    for i, env in enumerate(envs, 1):
        url = routing_urls.get(env)
        suffix = "" if url else " (not configured)"
        print(f"     [{i}] {env}{suffix}")

    try:
        choice = input("   > ").strip()
        idx = int(choice) - 1
        if 0 <= idx < len(envs):
            selected = envs[idx]
            if not routing_urls.get(selected):
                print(f"   Environment '{selected}' is not configured yet. Skipping schema publish.")
                return None
            return selected
    except (ValueError, EOFError):
        pass

    print("   Invalid selection. Skipping schema publish.")
    return None


def publish_schema(config: dict, service: dict, env: str) -> bool:
    graph = config["apollo_graph"]
    schema_path = service["schema_path"]
    subgraph = service["subgraph_name"]
    url = service["routing_urls"][env]

    cmd = (
        f'rover subgraph publish {graph}@{env} '
        f'--schema {schema_path} '
        f'--name {subgraph} '
        f'--routing-url {url}'
    )
    print(f"   $ {cmd}")
    returncode, _ = run_command(cmd)
    if returncode == 0:
        print(f"   Schema published to {graph}@{env}")
        return True
    else:
        print("   Schema publish failed")
        return False


def check_schema_sync(config: dict, service_name: str, service: dict, graph: str) -> dict:
    """
    Run rover subgraph check for a service and return sync status.
    Returns: {"in_sync": bool, "output": str, "error": str}
    """
    schema_path = Path(service["local_path"]) / service["schema_path"]
    subgraph = service["subgraph_name"]

    if not schema_path.exists():
        return {
            "in_sync": False,
            "output": "",
            "error": f"Schema file not found: {schema_path}"
        }

    cmd = f'rover subgraph check {graph}@dev --schema {schema_path} --name {subgraph}'
    returncode, output = run_command(cmd, capture=True, timeout=60)

    # Parse rover output to determine status
    output_lower = output.lower()

    # Check for various success/failure indicators
    has_changes = "change" in output_lower or "diff" in output_lower
    has_breaking = "breaking" in output_lower
    check_passed = returncode == 0 or "passed" in output_lower or "succeeded" in output_lower
    no_changes = "no changes" in output_lower or "identical" in output_lower

    # Determine sync status
    if no_changes:
        in_sync = True
        error = ""
    elif check_passed and not has_breaking:
        # Compatible changes only
        in_sync = False  # Schema differs but safe to publish
        error = ""
    elif has_breaking:
        in_sync = False
        error = "Breaking changes detected"
    elif returncode != 0:
        in_sync = False
        error = f"Check failed (exit code {returncode})"
    else:
        in_sync = False
        error = ""

    return {
        "in_sync": in_sync,
        "output": output,
        "error": error
    }


def run_check_sync(config: dict):
    """Check all services' schemas against Apollo Gateway (dev)."""
    print("Checking schemas against Apollo Gateway (dev)...\n")

    graph = config["apollo_graph"]
    results = []

    for name, service in config["services"].items():
        # Skip services without GraphQL schemas
        if not service.get("schema_path") or not service.get("subgraph_name"):
            continue

        print(f"   Checking {name}...")
        result = check_schema_sync(config, name, service, graph)
        results.append({
            "name": name,
            **result
        })

    # Print results
    print("\n" + "="*60)
    needs_publish = []
    has_errors = []

    for r in results:
        if r["error"]:
            print(f"❌ {r['name']}: {r['error']}")
            has_errors.append(r["name"])
            # Show first few lines of output for debugging
            if r["output"]:
                output_lines = r["output"].split("\n")[:5]
                for line in output_lines:
                    if line.strip():
                        print(f"    {line.strip()}")
        elif r["in_sync"]:
            print(f"✅ {r['name']}: Schema in sync")
        else:
            print(f"⚠️  {r['name']}: Schema changes detected")
            needs_publish.append(r["name"])
            # Show relevant output lines
            if r["output"]:
                shown_lines = 0
                for line in r["output"].split("\n"):
                    # Filter for useful change indicators
                    if any(keyword in line.lower() for keyword in ["change", "added", "removed", "field", "type", "breaking"]):
                        print(f"    {line.strip()}")
                        shown_lines += 1
                        if shown_lines >= 10:  # Limit output
                            break

    print("="*60)

    # Summary
    if has_errors:
        print(f"\n⚠️  Errors encountered checking {len(has_errors)} service(s)")
        print(f"   Run 'rover subgraph check' manually to debug")

    if needs_publish:
        print(f"\n📋 Summary: {len(needs_publish)} service(s) need schema publish:")
        for name in needs_publish:
            print(f"   - {name}")
        print(f"\nTo publish a schema, cd into the service directory and run:")
        print(f"   /supervisr-release --schema-only")
    elif not has_errors:
        print("\n✅ All schemas are in sync with Apollo Gateway (dev)")


def main():
    args = sys.argv[1:]
    skip_tests = "--skip-tests" in args
    no_build = "--no-build" in args
    schema_only = "--schema-only" in args
    check_sync = "--check-sync" in args

    config = load_config()

    # Handle --check-sync (can run from anywhere)
    if check_sync:
        run_check_sync(config)
        sys.exit(0)

    # Verify git repo (required for all other operations)
    returncode, _ = run_command("git rev-parse --git-dir", capture=True)
    if returncode != 0:
        print("Not in a git repository")
        sys.exit(1)

    service = detect_service(config)

    service_name = service["name"] if service else get_service_name()
    branch = get_current_branch()
    print(f"Supervisr Release: {service_name} ({branch})")

    if not schema_only:
        # Check for uncommitted changes
        if not get_git_status_clean():
            print("Working tree has uncommitted changes. Commit or stash first.")
            sys.exit(1)

    # Phase 1: Test
    if not skip_tests and not schema_only:
        if not run_tests():
            sys.exit(1)

    # Phase 2: Tag + Build
    new_tag = None
    if not schema_only:
        latest_tag = get_latest_tag()
        if latest_tag:
            new_tag = increment_patch_version(latest_tag)
            print(f"\nPhase 2: Tag & Build")
            print(f"   Latest tag: {latest_tag}")
            print(f"   New tag: {new_tag}")
        else:
            new_tag = "0.0.1-dev"
            print(f"\nPhase 2: Tag & Build")
            print(f"   No existing tags found")
            print(f"   New tag: {new_tag}")

        if not tag_and_push(new_tag):
            sys.exit(1)

        if not no_build:
            if not build_image(new_tag):
                print("   Tag created and pushed, but Docker build failed")
                sys.exit(1)

    # Phase 3: Schema Publish
    has_schema = service and service.get("schema_path") and service.get("subgraph_name")

    if has_schema:
        latest_tag_for_diff = get_latest_tag() if schema_only else (
            get_latest_tag()  # After tagging, latest_tag is now new_tag's predecessor
        )
        # For schema-only, always publish. Otherwise check for changes.
        should_publish = schema_only or detect_schema_changes(
            latest_tag_for_diff, service["schema_path"]
        )

        if should_publish:
            print(f"\nPhase 3: Schema Publish")
            if not schema_only:
                print(f"   Schema changes detected in {Path(service['schema_path']).name}")
            env = prompt_environment(service["routing_urls"])
            if env:
                if not publish_schema(config, service, env):
                    sys.exit(1)
        elif not schema_only:
            print(f"\n   No schema changes detected. Skipping Phase 3.")

    # Summary
    if schema_only:
        print(f"\nSchema publish complete")
    elif new_tag:
        print(f"\nRelease complete: {new_tag}")


if __name__ == "__main__":
    main()

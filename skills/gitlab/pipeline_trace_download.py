#!/usr/bin/env python3
"""Download full GitLab CI job trace to a local file in the DAC repo.

Standalone script — does NOT import gitlab_skill.py (which has module-level side effects).
Instead, it reads the same config/index files and reuses the same auth pattern.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "gitlab_config.json")
INDEX_FILE = os.path.join(SCRIPT_DIR, "dac_index.json")
IAP_COOKIE_DIR = os.path.expanduser("~/.config/git-gcp-iap")
IAP_HELPER_BIN = os.path.expanduser("~/bin/git-remote-https+iap")


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def load_index():
    try:
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_token_from_keychain(org_name):
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "claude-gitlab", "-a", f"gitlab_{org_name}", "-w"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_iap_token(gitlab_url):
    hostname = gitlab_url.replace("https://", "").replace("http://", "").rstrip("/")
    cookie_file = os.path.join(IAP_COOKIE_DIR, f"{hostname}.cookie")
    if not os.path.exists(cookie_file):
        return None
    with open(cookie_file, "r") as f:
        line = f.read().strip()
    if not line:
        return None
    parts = line.split("\t")
    if len(parts) < 7:
        return None
    if time.time() > int(parts[4]):
        return None
    return parts[6]


def resolve_project(name, org_name="supervisrai"):
    """Resolve DAC name to (project_id, gitlab_path) from cached index."""
    index_data = load_index()
    if not index_data:
        return None, None

    org_index = index_data.get("organizations", {}).get(org_name, {})
    normalized = name.lower().replace(" ", "-").strip()

    entry = org_index.get(normalized)
    if not entry:
        collapsed = normalized.replace("-", "").replace("_", "")
        entry = org_index.get(collapsed)

    if not entry:
        return None, None
    return entry["id"], entry["path"]


def build_headers(org_name, gitlab_url):
    token = get_token_from_keychain(org_name)
    if not token:
        print(f"Error: No token for '{org_name}'. Run gitlab_config_setup.py configure {org_name}", file=sys.stderr)
        sys.exit(1)
    hdrs = {"PRIVATE-TOKEN": token}
    iap = get_iap_token(gitlab_url)
    if iap:
        hdrs["Authorization"] = f"Bearer {iap}"
    return hdrs


def main():
    parser = argparse.ArgumentParser(description="Download GitLab CI job trace to local file")
    parser.add_argument("dac_name", help="DAC project name (e.g., lead-lifecycle)")
    parser.add_argument("--job", required=True, help="Job ID")
    parser.add_argument("--env", default="dev", help="Environment label (default: dev)")
    parser.add_argument("--org", default="supervisrai", help="Organization (default: supervisrai)")
    args = parser.parse_args()

    config = load_config()
    org_config = config.get("organizations", {}).get(args.org)
    if not org_config:
        print(f"Error: Org '{args.org}' not found in config", file=sys.stderr)
        sys.exit(1)

    gitlab_url = org_config["gitlab_url"]
    local_path = org_config.get("local_path", "")
    headers = build_headers(args.org, gitlab_url)

    project_id, project_path = resolve_project(args.dac_name, args.org)
    if not project_id:
        print(f"Error: Could not resolve '{args.dac_name}'. Run: gitlab_skill.py index", file=sys.stderr)
        sys.exit(1)

    # Fetch trace
    url = f"{gitlab_url}/api/v4/projects/{project_id}/jobs/{args.job}/trace"
    resp = requests.get(url, headers=headers, allow_redirects=False)
    if resp.status_code in (301, 302, 303, 307, 308):
        print("Error: IAP auth failed (redirect). Refresh IAP token.", file=sys.stderr)
        sys.exit(1)
    if resp.status_code >= 400:
        print(f"Error: API {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        sys.exit(1)

    # Strip ANSI
    clean = re.sub(r'\x1b\[[0-9;]*m', '', resp.text)

    # Extract image tag
    m = re.search(r'TF_VAR_image_tag\s*[=:]\s*["\']?([^\s"\']+)', clean)
    image_tag = m.group(1) if m else "unknown"

    # Write to DAC repo
    repo_path = os.path.join(local_path, project_path)
    out_dir = os.path.join(repo_path, "gitlab-ci", args.env)
    os.makedirs(out_dir, exist_ok=True)

    filename = f"execution_{image_tag}_{args.job}.log"
    out_path = os.path.join(out_dir, filename)

    with open(out_path, "w") as f:
        f.write(clean)

    print(out_path)


if __name__ == "__main__":
    main()

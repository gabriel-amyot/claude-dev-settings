#!/usr/bin/env python3
"""Download full GitLab CI job trace to a local file in the DAC repo.

Imports auth and config from gitlab_skill.py (now safe to import as a module).
"""
import argparse
import os
import re
import sys

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from gitlab_skill import (
    load_config,
    load_index,
    get_token_from_keychain,
    get_iap_token,
    resolve_project_id,
    IAP_COOKIE_DIR,
)


def build_headers(org_name, gitlab_url, iap_refresh_repo=None):
    token = get_token_from_keychain(org_name)
    if not token:
        print(f"Error: No token for '{org_name}'. Run gitlab_config_setup.py configure {org_name}", file=sys.stderr)
        sys.exit(1)
    hdrs = {"PRIVATE-TOKEN": token}
    iap = get_iap_token(gitlab_url, iap_refresh_repo=iap_refresh_repo)
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
    headers = build_headers(args.org, gitlab_url, iap_refresh_repo=org_config.get("iap_refresh_repo"))

    project_id = resolve_project_id(args.dac_name, args.org)
    if not project_id:
        print(f"Error: Could not resolve '{args.dac_name}'. Run: gitlab_skill.py index", file=sys.stderr)
        sys.exit(1)

    # Look up the project path from the index for directory structure
    index_data = load_index()
    project_path = None
    if index_data:
        org_index = index_data.get("organizations", {}).get(args.org, {})
        for alias, info in org_index.items():
            if info["id"] == project_id:
                project_path = info["path"]
                break

    if not project_path:
        print(f"Error: Could not find path for project ID {project_id}", file=sys.stderr)
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

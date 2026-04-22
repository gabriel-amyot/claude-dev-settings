#!/usr/bin/env python3
"""Admin CLI for gcloud_config.json — manage org aliases and verify auth."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "gcloud_config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"ERROR: Config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def check_auth(account: str) -> bool:
    """Returns True if the account has a valid access token."""
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token", f"--account={account}"],
        capture_output=True, text=True, timeout=15,
    )
    return result.returncode == 0


def cmd_list(config: dict) -> None:
    default_org = config.get("default_org", "")
    print(f"Default org: {default_org}\n")
    for org_name, org in config["organizations"].items():
        marker = " (default)" if org_name == default_org else ""
        print(f"[{org_name}]{marker}")
        print(f"  account   : {org['gcloud_account']}")
        print(f"  local_path: {org['local_path']}")
        print(f"  aliases   :")
        for alias, project_id in org["project_aliases"].items():
            print(f"    {alias:<20} -> {project_id}")
        safety = org.get("safety", {})
        allowlist = safety.get("datastore_dev_allowlist", [])
        blocked = safety.get("datastore_blocked_envs", [])
        if allowlist or blocked:
            print(f"  datastore allowlist: {', '.join(allowlist) or 'none'}")
            print(f"  datastore blocked  : {', '.join(blocked) or 'none'}")
        print()


def cmd_check_auth(config: dict) -> None:
    all_ok = True
    for org_name, org in config["organizations"].items():
        account = org["gcloud_account"]
        ok = check_auth(account)
        status = "OK" if ok else "FAIL"
        print(f"[{org_name}] {account}: {status}")
        if not ok:
            all_ok = False
            print(f"  -> Run: gcloud auth login --account={account}")
    sys.exit(0 if all_ok else 1)


def cmd_add_alias(config: dict, org: str, alias: str, project_id: str) -> None:
    if org not in config["organizations"]:
        available = ", ".join(config["organizations"])
        print(f"ERROR: Unknown org '{org}'. Available: {available}", file=sys.stderr)
        sys.exit(1)
    config["organizations"][org]["project_aliases"][alias] = project_id
    save_config(config)
    print(f"Added: [{org}] {alias} -> {project_id}")


def cmd_remove_alias(config: dict, org: str, alias: str) -> None:
    if org not in config["organizations"]:
        print(f"ERROR: Unknown org '{org}'.", file=sys.stderr)
        sys.exit(1)
    aliases = config["organizations"][org]["project_aliases"]
    if alias not in aliases:
        print(f"ERROR: Alias '{alias}' not found in org '{org}'.", file=sys.stderr)
        sys.exit(1)
    removed_id = aliases.pop(alias)
    save_config(config)
    print(f"Removed: [{org}] {alias} (was {removed_id})")


def cmd_set_default(config: dict, org: str) -> None:
    if org not in config["organizations"]:
        available = ", ".join(config["organizations"])
        print(f"ERROR: Unknown org '{org}'. Available: {available}", file=sys.stderr)
        sys.exit(1)
    config["default_org"] = org
    save_config(config)
    print(f"Default org set to: {org}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage gcloud multi-org config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands:\n"
            "  list                          Show all orgs, accounts, aliases\n"
            "  check-auth                    Verify credentials for all accounts\n"
            "  add-alias ORG ALIAS PROJ_ID   Add a project alias\n"
            "  remove-alias ORG ALIAS        Remove a project alias\n"
            "  default ORG                   Set the default org\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="Show all orgs and aliases")
    subparsers.add_parser("check-auth", help="Verify gcloud auth for all accounts")

    p_add = subparsers.add_parser("add-alias", help="Add a project alias")
    p_add.add_argument("org", help="Org name (supervisrai|klever)")
    p_add.add_argument("alias", help="Alias to add (e.g. dev-analytics)")
    p_add.add_argument("project_id", help="Full GCP project ID")

    p_rm = subparsers.add_parser("remove-alias", help="Remove a project alias")
    p_rm.add_argument("org", help="Org name")
    p_rm.add_argument("alias", help="Alias to remove")

    p_def = subparsers.add_parser("default", help="Set the default org")
    p_def.add_argument("org", help="Org name to set as default")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config()

    if args.command == "list":
        cmd_list(config)
    elif args.command == "check-auth":
        cmd_check_auth(config)
    elif args.command == "add-alias":
        cmd_add_alias(config, args.org, args.alias, args.project_id)
    elif args.command == "remove-alias":
        cmd_remove_alias(config, args.org, args.alias)
    elif args.command == "default":
        cmd_set_default(config, args.org)


if __name__ == "__main__":
    main()

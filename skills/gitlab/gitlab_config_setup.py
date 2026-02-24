#!/usr/bin/env python3
"""GitLab Configuration Setup - Manages org credentials securely"""
import os
import sys
import json
import subprocess
import getpass
from pathlib import Path

CONFIG_FILE = os.path.expanduser("~/.claude-shared-config/skills/gitlab/gitlab_config.json")
KEYCHAIN_SERVICE = "claude-gitlab"


def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at {CONFIG_FILE}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {CONFIG_FILE}")
        sys.exit(1)


def save_config(config):
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
    except Exception as e:
        print(f"Error saving config: {e}")
        sys.exit(1)


def store_token_in_keychain(org_name, token):
    """Store GitLab token securely in macOS Keychain"""
    account = f"gitlab_{org_name}"
    service = KEYCHAIN_SERVICE

    try:
        # Delete existing entry if it exists
        subprocess.run(
            ["security", "delete-generic-password", "-s", service, "-a", account],
            capture_output=True
        )

        # Add new token to keychain - use direct password argument
        result = subprocess.run(
            ["security", "add-generic-password", "-s", service, "-a", account, "-w", token],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Error storing token in keychain: {result.stderr}")
            return False

        return True
    except Exception as e:
        print(f"Error accessing keychain: {e}")
        return False


def retrieve_token_from_keychain(org_name):
    """Retrieve GitLab token from macOS Keychain"""
    account = f"gitlab_{org_name}"
    service = KEYCHAIN_SERVICE

    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        print(f"Error retrieving token from keychain: {e}")
        return None


def list_orgs():
    """List all configured organizations"""
    config = load_config()
    print("\n=== Configured Organizations ===\n")

    for org_name, org_config in config.get("organizations", {}).items():
        default_marker = " [DEFAULT]" if org_name == config.get("default_org") else ""
        print(f"{org_name}{default_marker}")
        print(f"  URL: {org_config.get('gitlab_url')}")
        print(f"  Path: {org_config.get('local_path')}")
        print(f"  Group: {org_config.get('gitlab_group')}")

        # Check if token is stored
        token = retrieve_token_from_keychain(org_name)
        token_status = "✓ Token stored" if token else "✗ No token"
        print(f"  Token: {token_status}\n")


def configure_org(org_name):
    """Configure credentials for an organization"""
    config = load_config()

    if org_name not in config.get("organizations", {}):
        print(f"Error: Organization '{org_name}' not found in configuration")
        print(f"Available orgs: {', '.join(config.get('organizations', {}).keys())}")
        sys.exit(1)

    org_config = config["organizations"][org_name]

    print(f"\n=== Configuring {org_name} ===\n")
    print(f"GitLab URL: {org_config.get('gitlab_url')}")
    print(f"Local Path: {org_config.get('local_path')}")
    print(f"GitLab Group: {org_config.get('gitlab_group')}\n")

    # Get token from user
    token = getpass.getpass(f"Enter GitLab Personal Access Token for {org_name}: ")

    if not token:
        print("Error: Token cannot be empty")
        sys.exit(1)

    # Store in keychain
    if store_token_in_keychain(org_name, token):
        print(f"✓ Token stored securely in Keychain for {org_name}")
    else:
        print(f"✗ Failed to store token in Keychain")
        sys.exit(1)


def add_org(org_name, gitlab_url, local_path, gitlab_group):
    """Add a new organization configuration"""
    config = load_config()

    if org_name in config.get("organizations", {}):
        print(f"Error: Organization '{org_name}' already exists")
        sys.exit(1)

    config["organizations"][org_name] = {
        "gitlab_url": gitlab_url,
        "local_path": local_path,
        "gitlab_group": gitlab_group
    }

    save_config(config)
    print(f"✓ Organization '{org_name}' added to configuration")

    # Prompt to configure token
    response = input(f"Configure GitLab token for '{org_name}'? (y/n): ")
    if response.lower() == "y":
        configure_org(org_name)


def set_default_org(org_name):
    """Set default organization"""
    config = load_config()

    if org_name not in config.get("organizations", {}):
        print(f"Error: Organization '{org_name}' not found")
        sys.exit(1)

    config["default_org"] = org_name
    save_config(config)
    print(f"✓ Default organization set to '{org_name}'")


def show_help():
    """Show usage help"""
    print("""
GitLab Configuration Setup

Usage:
  gitlab_config_setup.py list                          - List all organizations
  gitlab_config_setup.py configure ORG_NAME            - Configure token for an org
  gitlab_config_setup.py add ORG_NAME URL PATH GROUP   - Add new organization
  gitlab_config_setup.py default ORG_NAME              - Set default organization
  gitlab_config_setup.py get-token ORG_NAME            - Get token for org (for debugging)

Environment Variables:
  GITLAB_CONFIG - Path to gitlab_config.json (default: ~/.claude-shared-config/skills/gitlab/gitlab_config.json)

Token Storage:
  Tokens are stored securely in macOS Keychain under service 'claude-gitlab'
  """)


if len(sys.argv) < 2:
    show_help()
    sys.exit(0)

command = sys.argv[1]

try:
    if command == "list":
        list_orgs()

    elif command == "configure":
        if len(sys.argv) < 3:
            print("Error: configure requires organization name")
            sys.exit(1)
        configure_org(sys.argv[2])

    elif command == "add":
        if len(sys.argv) < 6:
            print("Error: add requires ORG_NAME, URL, LOCAL_PATH, and GITLAB_GROUP")
            sys.exit(1)
        add_org(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

    elif command == "default":
        if len(sys.argv) < 3:
            print("Error: default requires organization name")
            sys.exit(1)
        set_default_org(sys.argv[2])

    elif command == "get-token":
        if len(sys.argv) < 3:
            print("Error: get-token requires organization name")
            sys.exit(1)
        token = retrieve_token_from_keychain(sys.argv[2])
        if token:
            print(f"Token for {sys.argv[2]}: {token[:20]}...")
        else:
            print(f"No token found for {sys.argv[2]}")

    elif command in ["help", "-h", "--help"]:
        show_help()

    else:
        print(f"Unknown command: {command}")
        show_help()
        sys.exit(1)

except KeyboardInterrupt:
    print("\nCancelled")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

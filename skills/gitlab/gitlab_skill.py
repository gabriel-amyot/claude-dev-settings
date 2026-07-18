#!/usr/bin/env python3
"""GitLab CLI for Claude Code - minimal, token-efficient interface"""
import fcntl
import glob
import os
import sys
import json
import subprocess
from pathlib import Path
import re
import time
import requests

from trace_utils import strip_ansi, extract_plan_dict, extract_error_lines

# Configuration management
CONFIG_FILE = os.path.expanduser("~/.claude-shared-config/skills/gitlab/gitlab_config.json")
IAP_HELPER_BIN = os.path.expanduser("~/bin/git-remote-https+iap")
IAP_COOKIE_DIR = os.path.expanduser("~/.config/git-gcp-iap")
BLOCKED_REFS = {"main", "master", "prod", "production", "uat"}
BLOCKED_SCOPES = {"production", "prod", "uat", "main", "master"}
MAX_API_RETRIES = 2
INDEX_FILE = os.path.join(os.path.dirname(CONFIG_FILE), "dac_index.json")


def load_index():
    """Load the cached project index"""
    try:
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_index(index_data):
    """Persist the project index to disk with file locking to prevent corruption
    when multiple agents write simultaneously."""
    lock_path = INDEX_FILE + ".lock"
    with open(lock_path, "w") as lock_f:
        try:
            fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            with open(INDEX_FILE, "w") as f:
                json.dump(index_data, f, indent=2)
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)


def build_index_from_api(org_config, group_override=None):
    """Fetch all projects from GitLab API and build the index for an org"""
    org_name = org_config["name"]

    # Use group override, or index_groups from config, or fall back to gitlab_group
    groups_to_index = []
    if group_override:
        groups_to_index = [group_override]
    elif org_config.get("index_groups"):
        groups_to_index = org_config["index_groups"]
    elif org_config.get("gitlab_group"):
        groups_to_index = [org_config["gitlab_group"]]
    else:
        return {"error": f"No group configured for '{org_name}'. Use: index --group GROUP_PATH"}

    # Fetch all projects under each group (recursive)
    projects = []
    for group in groups_to_index:
        # URL-encode the group path for the API (/ → %2F)
        encoded_group = requests.utils.quote(group, safe="")
        page = 1
        while True:
            response = api_request(
                f"/groups/{encoded_group}/projects",
                params={"page": page, "per_page": 100, "include_subgroups": "true"}
            )
            if isinstance(response, dict) and "error" in response:
                return response
            if not response:
                break
            projects.extend(response)
            page += 1

    # Build aliases: full name, short name, collapsed name
    org_index = {}
    for p in projects:
        pid = p.get("id")
        name = p.get("path", "")
        full_path = p.get("path_with_namespace", "")

        org_index[name] = {"id": pid, "path": full_path}

        # Strip org-configurable prefixes to create short aliases
        # e.g., "dac-sprvsr-core-eqs" → "eqs", "dac-gcp-back-proxrp" → "proxrp"
        short = name
        strip_prefixes = org_config.get("strip_prefixes",
                                        ["dac-sprvsr-core-", "dac-sprvsr-", "dac-"])
        for prefix in strip_prefixes:
            if short.startswith(prefix):
                short = short[len(prefix):]
                break

        if short != name:
            org_index[short] = {"id": pid, "path": full_path}
            # Also add collapsed version: "lead-lifecycle" → "leadlifecycle"
            collapsed = short.replace("-", "")
            if collapsed != short:
                org_index[collapsed] = {"id": pid, "path": full_path}

    return org_index


def run_index(org_configs=None, group_override=None):
    """Build and save the full index. Accepts list of org configs or indexes current org."""
    index_data = load_index() or {"version": 1, "organizations": {}}

    if org_configs is None:
        org_configs = [current_org]

    for org_conf in org_configs:
        org_name = org_conf["name"]
        org_index = build_index_from_api(org_conf, group_override=group_override)

        if isinstance(org_index, dict) and "error" in org_index:
            return org_index

        index_data["organizations"][org_name] = org_index
        index_data["indexed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    save_index(index_data)
    return index_data


def resolve_project_id(name_or_id, org_name="supervisrai"):
    """Resolve project name/alias to project ID from cached index"""
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
        return int(name_or_id)

    # Load index, auto-build if missing
    index_data = load_index()
    if not index_data or org_name not in index_data.get("organizations", {}):
        index_data = run_index()
        if isinstance(index_data, dict) and "error" in index_data:
            return None

    org_index = index_data.get("organizations", {}).get(org_name, {})

    # Normalize input
    normalized = name_or_id.lower().replace(" ", "-").strip()

    # Direct match on full name or short alias
    if normalized in org_index:
        return org_index[normalized]["id"]

    # Collapsed match (no hyphens/spaces/underscores)
    collapsed = normalized.replace("-", "").replace("_", "")
    if collapsed in org_index:
        return org_index[collapsed]["id"]

    # Substring match as last resort
    for alias, info in org_index.items():
        if collapsed in alias.replace("-", "").replace("_", ""):
            return info["id"]

    return None


def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(json.dumps({"error": f"Config file not found: {CONFIG_FILE}. Run gitlab_config_setup.py to initialize."}))
        sys.exit(1)
    except json.JSONDecodeError:
        print(json.dumps({"error": f"Invalid JSON in config file: {CONFIG_FILE}"}))
        sys.exit(1)


def get_token_from_keychain(org_name):
    """Retrieve GitLab token from macOS Keychain"""
    account = f"gitlab_{org_name}"
    service = "claude-gitlab"

    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def get_iap_token(gitlab_url, iap_refresh_repo=None):
    """Get IAP token for a GitLab instance behind GCP Identity-Aware Proxy.

    Reads the token from the git-remote-https+iap cookie file. If expired,
    tries the IAP helper binary, then falls back to git fetch on iap_refresh_repo.
    Self-healing: agents never need to manually refresh the IAP cookie.
    """
    hostname = gitlab_url.replace("https://", "").replace("http://", "").rstrip("/")
    cookie_file = os.path.join(IAP_COOKIE_DIR, f"{hostname}.cookie")

    def read_best_token():
        """Try hostname.cookie first, then any user@hostname.cookie, return first valid."""
        candidates = []
        if os.path.exists(cookie_file):
            candidates.append(cookie_file)
        # user@hostname format (e.g. gamyot-beklever@cicd.prod.datasophia.com.cookie)
        candidates.extend(sorted(glob.glob(os.path.join(IAP_COOKIE_DIR, f"*@{hostname}.cookie"))))
        for path in candidates:
            try:
                with open(path, "r") as f:
                    line = f.read().strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) < 7:
                    continue
                expiry = int(parts[4])
                if time.time() <= expiry:
                    return parts[6]
            except Exception:
                continue
        return None

    # Fast path: valid token already in cookie files
    token = read_best_token()
    if token:
        return token

    # Refresh attempt 1: IAP helper binary
    if os.path.exists(IAP_HELPER_BIN):
        try:
            subprocess.run(
                [IAP_HELPER_BIN, "check", "origin", f"https+iap://{hostname}"],
                capture_output=True, text=True, timeout=30
            )
            token = read_best_token()
            if token:
                return token
        except Exception:
            pass

    # Refresh attempt 2: git fetch on configured repo (self-healing for Klever IAP)
    if iap_refresh_repo and os.path.exists(iap_refresh_repo):
        try:
            subprocess.run(
                ["git", "-C", iap_refresh_repo, "fetch", "origin"],
                capture_output=True, text=True, timeout=30
            )
            return read_best_token()
        except Exception:
            pass

    return None


def detect_org_from_cwd(config):
    """Longest-prefix match on $PWD vs org local_path. Falls back to default_org."""
    cwd = os.getcwd()
    orgs = config.get("organizations", {})
    best_match = None
    best_len = 0
    for org_name, org_cfg in orgs.items():
        local_path = org_cfg.get("local_path", "")
        if local_path and cwd.startswith(local_path) and len(local_path) > best_len:
            best_match = org_name
            best_len = len(local_path)
    return best_match or config.get("default_org")


def get_org_config(org_name=None):
    """Get organization configuration"""
    config = load_config()
    orgs = config.get("organizations", {})

    # Use specified org, auto-detect from $PWD, or fall back to default
    if org_name:
        if org_name not in orgs:
            print(json.dumps({"error": f"Organization '{org_name}' not found. Available: {', '.join(orgs.keys())}"}))
            sys.exit(1)
    else:
        org_name = detect_org_from_cwd(config)
        if not org_name or org_name not in orgs:
            org_name = list(orgs.keys())[0] if orgs else None

    if not org_name:
        print(json.dumps({"error": "No organizations configured"}))
        sys.exit(1)

    org_config = orgs[org_name]

    # Get token from keychain
    token = get_token_from_keychain(org_name)
    if not token:
        print(json.dumps({"error": f"No token found for '{org_name}'. Run: gitlab_config_setup.py configure {org_name}"}))
        sys.exit(1)

    return {
        "name": org_name,
        "url": org_config.get("gitlab_url"),
        "token": token,
        "local_path": org_config.get("local_path"),
        "gitlab_group": org_config.get("gitlab_group"),
        "index_groups": org_config.get("index_groups"),
        "iap_refresh_repo": org_config.get("iap_refresh_repo")
    }


# Module-level globals for API calls. Set by _init() at startup or by tests.
current_org = None
gitlab_url = None
gitlab_token = None
headers = {}


def _init(org_override=None):
    """Initialize module globals from config. Called at startup or by tests."""
    global current_org, gitlab_url, gitlab_token, headers
    current_org = get_org_config(org_override)
    gitlab_url = current_org["url"]
    gitlab_token = current_org["token"]
    headers = {
        "PRIVATE-TOKEN": gitlab_token,
        "Content-Type": "application/json"
    }
    iap_token = get_iap_token(gitlab_url, iap_refresh_repo=current_org.get("iap_refresh_repo"))
    if iap_token:
        headers["Authorization"] = f"Bearer {iap_token}"


def api_request(endpoint, method="GET", params=None, data=None, raw=False):
    """Make API request to GitLab with retry on transient failures.

    Retries up to MAX_API_RETRIES times on 5xx errors and connection failures.
    Never retries on 4xx (client errors) or redirects (IAP auth).
    """
    url = f"{gitlab_url}/api/v4{endpoint}"
    last_error = None

    for attempt in range(1 + MAX_API_RETRIES):
        try:
            kwargs = {"headers": headers, "params": params, "allow_redirects": False}
            if method == "GET":
                response = requests.get(url, **kwargs)
            elif method == "POST":
                response = requests.post(url, json=data, **kwargs)
            elif method == "PUT":
                response = requests.put(url, json=data, **kwargs)
            elif method == "DELETE":
                response = requests.delete(url, **kwargs)

            # IAP redirect: auth problem, not transient. Don't retry.
            if response.status_code in (301, 302, 303, 307, 308):
                return {"error": "IAP authentication failed (redirect to login). "
                        "Run: ~/bin/git-remote-https+iap check origin https+iap://"
                        f"{gitlab_url.replace('https://', '')} to refresh the IAP token."}

            # 429: rate limited. Respect Retry-After header, then retry.
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                last_error = f"Rate limited (429). Retry-After: {retry_after}s"
                if attempt < MAX_API_RETRIES:
                    time.sleep(min(retry_after, 30))
                    continue
                return {"error": last_error}

            # 4xx: client error. Don't retry.
            if 400 <= response.status_code < 500:
                return {"error": f"API Error {response.status_code}: {response.text[:500]}"}

            # 5xx: server error. Retry if attempts remain.
            if response.status_code >= 500:
                last_error = f"API Error {response.status_code}: {response.text[:500]}"
                if attempt < MAX_API_RETRIES:
                    time.sleep(1 * (attempt + 1))
                    continue
                return {"error": last_error}

            if raw:
                return response.text

            try:
                return response.json()
            except ValueError:
                return response.text

        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = str(e)
            if attempt < MAX_API_RETRIES:
                time.sleep(1 * (attempt + 1))
                continue
            return {"error": last_error}

        except Exception as e:
            return {"error": str(e)}

    return {"error": last_error or "Unknown error after retries"}


def compact_group(group):
    """Minimal group format"""
    return {
        "id": group.get("id"),
        "name": group.get("name"),
        "path": group.get("path"),
        "full_path": group.get("full_path")
    }


def full_group(group):
    """Full group details"""
    return {
        "id": group.get("id"),
        "name": group.get("name"),
        "path": group.get("path"),
        "full_path": group.get("full_path"),
        "description": group.get("description", ""),
        "visibility": group.get("visibility"),
        "web_url": group.get("web_url"),
        "projects_count": group.get("projects_count"),
        "subgroups_count": group.get("subgroups_count")
    }


def compact_repo(project):
    """Minimal repo format"""
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "path": project.get("path"),
        "path_with_namespace": project.get("path_with_namespace")
    }


def full_repo(project):
    """Full repo details"""
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "path": project.get("path"),
        "path_with_namespace": project.get("path_with_namespace"),
        "description": project.get("description", ""),
        "visibility": project.get("visibility"),
        "ssh_url_to_repo": project.get("ssh_url_to_repo"),
        "http_url_to_repo": project.get("http_url_to_repo"),
        "web_url": project.get("web_url"),
        "created_at": project.get("created_at"),
        "last_activity_at": project.get("last_activity_at"),
        "default_branch": project.get("default_branch"),
        "star_count": project.get("star_count")
    }


def list_groups(full=False):
    """List all groups with pagination"""
    groups = []
    page = 1

    while True:
        response = api_request("/groups", params={"page": page, "per_page": 100, "all_available": True})

        if isinstance(response, dict) and "error" in response:
            return response

        if not response:
            break

        formatter = full_group if full else compact_group
        groups.extend([formatter(g) for g in response])
        page += 1

    return groups


def list_repos(group_id=None, all_repos=False, full=False):
    """List projects"""
    projects = []
    page = 1

    # Get group if specified
    if group_id:
        group_response = api_request(f"/groups/{group_id}")
        if isinstance(group_response, dict) and "error" in group_response:
            return group_response
        group_id = group_response.get("id")
        endpoint = f"/groups/{group_id}/projects"
    else:
        endpoint = "/projects"

    while True:
        params = {"page": page, "per_page": 100}
        if group_id:
            params["include_subgroups"] = "false"

        response = api_request(endpoint, params=params)

        if isinstance(response, dict) and "error" in response:
            return response

        if not response:
            break

        formatter = full_repo if full else compact_repo
        projects.extend([formatter(p) for p in response])
        page += 1

        if not all_repos and group_id:
            break

    return projects


def get_repo(project_id_or_path, full=False):
    """Get single repository"""
    response = api_request(f"/projects/{project_id_or_path}")

    if isinstance(response, dict) and "error" in response:
        return response

    return full_repo(response) if full else compact_repo(response)


def search_repos(query, max_results=20):
    """Search repositories"""
    response = api_request("/projects", params={
        "search": query,
        "per_page": max_results
    })

    if isinstance(response, dict) and "error" in response:
        return response

    return [compact_repo(p) for p in response]


def clone_repos(group_id, repo_list=None, output_dir=None):
    """Clone repositories with organized structure"""

    # Use organization's configured local_path if output_dir not specified
    if output_dir is None:
        output_dir = current_org.get("local_path", "./gitlab-repos")

    # Get group info
    group_response = api_request(f"/groups/{group_id}")
    if isinstance(group_response, dict) and "error" in group_response:
        return group_response

    group_path = group_response.get("full_path")

    # Get repositories
    endpoint = f"/groups/{group_id}/projects"
    response = api_request(endpoint, params={"per_page": 100, "include_subgroups": "false"})

    if isinstance(response, dict) and "error" in response:
        return response

    # Filter repos if specified
    if repo_list:
        repo_names = set(repo_list.split(","))
        repos = [p for p in response if p.get("path") in repo_names]
    else:
        repos = response

    cloned = []
    failed = []

    for project in repos:
        repo_path = project.get("path")
        ssh_url = project.get("ssh_url_to_repo")

        # Create directory structure: output_dir/group_path/repo_path
        clone_path = os.path.join(output_dir, group_path, repo_path)

        try:
            Path(clone_path).parent.mkdir(parents=True, exist_ok=True)

            if os.path.exists(os.path.join(clone_path, ".git")):
                # Pull if already cloned
                subprocess.run(["git", "-C", clone_path, "pull"],
                              capture_output=True, timeout=30)
                cloned.append({
                    "repo": repo_path,
                    "path": clone_path,
                    "status": "updated"
                })
            else:
                # Clone new repo
                result = subprocess.run(["git", "clone", ssh_url, clone_path],
                                      capture_output=True, timeout=60)
                if result.returncode == 0:
                    cloned.append({
                        "repo": repo_path,
                        "path": clone_path,
                        "status": "cloned"
                    })
                else:
                    failed.append({
                        "repo": repo_path,
                        "error": result.stderr.decode() if result.stderr else "Unknown error"
                    })
        except subprocess.TimeoutExpired:
            failed.append({"repo": repo_path, "error": "Clone timeout"})
        except Exception as e:
            failed.append({"repo": repo_path, "error": str(e)})

    return {
        "group": group_path,
        "output_directory": output_dir,
        "cloned_count": len(cloned),
        "failed_count": len(failed),
        "cloned": cloned,
        "failed": failed if failed else None
    }


def manage_merge_request(project_id, action, title=None, source=None, target=None, mr_iid=None, description=None):
    """Manage merge requests"""

    if action == "create":
        if not title or not source or not target:
            return {"error": "create action requires --title, --source, and --target"}

        data = {
            "title": title,
            "source_branch": source,
            "target_branch": target
        }
        if description:
            data["description"] = description

        response = api_request(f"/projects/{project_id}/merge_requests",
                             method="POST", data=data)

        if isinstance(response, dict) and "error" in response:
            return response

        return {
            "created": True,
            "iid": response.get("iid"),
            "title": response.get("title"),
            "state": response.get("state"),
            "web_url": response.get("web_url")
        }

    elif action == "update":
        if not mr_iid:
            return {"error": "update action requires --mr-iid"}
        data = {}
        if title:
            data["title"] = title
        if description:
            data["description"] = description
        if not data:
            return {"error": "update action requires at least --title or --description"}

        response = api_request(f"/projects/{project_id}/merge_requests/{mr_iid}",
                             method="PUT", data=data)

        if isinstance(response, dict) and "error" in response:
            return response

        return {
            "updated": True,
            "iid": response.get("iid"),
            "title": response.get("title"),
            "web_url": response.get("web_url")
        }

    elif action == "merge":
        if not mr_iid:
            return {"error": "merge action requires --mr-iid"}

        response = api_request(f"/projects/{project_id}/merge_requests/{mr_iid}/merge",
                             method="PUT", data={})

        if isinstance(response, dict) and "error" in response:
            return response

        return {
            "merged": True,
            "iid": response.get("iid"),
            "state": response.get("state")
        }

    elif action == "auto-merge":
        if not mr_iid:
            return {"error": "auto-merge action requires --mr-iid"}

        response = api_request(f"/projects/{project_id}/merge_requests/{mr_iid}/merge",
                             method="PUT", data={"merge_when_pipeline_succeeds": True})

        if isinstance(response, dict) and "error" in response:
            return response

        return {
            "auto_merge_set": True,
            "iid": response.get("iid"),
            "merge_when_pipeline_succeeds": True,
            "web_url": response.get("web_url")
        }

    elif action == "list":
        response = api_request(f"/projects/{project_id}/merge_requests",
                             params={"state": "opened", "per_page": 100})

        if isinstance(response, dict) and "error" in response:
            return response

        return [
            {
                "iid": mr.get("iid"),
                "title": mr.get("title"),
                "source_branch": mr.get("source_branch"),
                "target_branch": mr.get("target_branch"),
                "state": mr.get("state"),
                "web_url": mr.get("web_url")
            }
            for mr in response
        ]

    elif action == "approve":
        if not mr_iid:
            return {"error": "approve action requires --mr-iid"}

        response = api_request(f"/projects/{project_id}/merge_requests/{mr_iid}/approve",
                             method="POST")

        if isinstance(response, dict) and "error" in response:
            return response

        return {
            "approved": True,
            "iid": response.get("iid"),
            "web_url": response.get("web_url")
        }

    else:
        return {"error": f"Unknown MR action: {action}"}


def encode_project_path(name_or_id):
    """Return a project identifier usable directly as GitLab :id.

    Numeric IDs pass through. A full namespace path (e.g.
    grp-cst/grp-beklever-com/.../app-user-management) is URL-encoded so the
    API accepts it verbatim, bypassing the name/alias index. This is what the
    colleague-review agent uses since it already has the exact path from the
    MR URL.
    """
    s = str(name_or_id)
    if s.isdigit():
        return s
    return requests.utils.quote(s, safe="")


def get_mr_review(project, mr_iid):
    """Fetch everything needed to review an MR: metadata, diff_refs, per-file diffs.

    Returns the MR object plus the `changes` array (each with `diff`, `new_path`,
    `old_path`, and file-state flags) and `diff_refs` (base_sha/head_sha/start_sha)
    that inline discussion positions require.
    """
    pid = encode_project_path(project)
    response = api_request(f"/projects/{pid}/merge_requests/{mr_iid}/changes")
    if isinstance(response, dict) and "error" in response:
        return response

    return {
        "iid": response.get("iid"),
        "title": response.get("title"),
        "state": response.get("state"),
        "author": (response.get("author") or {}).get("username"),
        "source_branch": response.get("source_branch"),
        "target_branch": response.get("target_branch"),
        "web_url": response.get("web_url"),
        "diff_refs": response.get("diff_refs") or {},
        "changes": [
            {
                "new_path": c.get("new_path"),
                "old_path": c.get("old_path"),
                "new_file": c.get("new_file"),
                "deleted_file": c.get("deleted_file"),
                "renamed_file": c.get("renamed_file"),
                "diff": c.get("diff"),
            }
            for c in (response.get("changes") or [])
        ],
    }


def post_mr_note(project, mr_iid, body, new_path=None, new_line=None,
                 old_path=None, old_line=None, base_sha=None, head_sha=None,
                 start_sha=None):
    """Post a discussion on an MR. Inline (anchored to a diff line) when position
    args are supplied, otherwise a general MR discussion note.

    For a comment on an added/context line, pass --new-path + --new-line. For a
    removed line, pass --old-path + --old-line. base/head/start sha come from the
    MR's diff_refs (see get_mr_review)."""
    pid = encode_project_path(project)
    data = {"body": body}

    has_position = any([new_line, old_line]) and (new_path or old_path)
    if has_position:
        if not (base_sha and head_sha and start_sha):
            return {"error": "inline note requires --base-sha, --head-sha, and --start-sha "
                             "(from the MR diff_refs)"}
        path = new_path or old_path
        position = {
            "base_sha": base_sha,
            "head_sha": head_sha,
            "start_sha": start_sha,
            "position_type": "text",
            "new_path": new_path or path,
            "old_path": old_path or path,
        }
        if new_line:
            position["new_line"] = int(new_line)
        if old_line:
            position["old_line"] = int(old_line)
        data["position"] = position

    response = api_request(f"/projects/{pid}/merge_requests/{mr_iid}/discussions",
                           method="POST", data=data)
    if isinstance(response, dict) and "error" in response:
        return response

    return {
        "posted": True,
        "inline": has_position,
        "discussion_id": response.get("id"),
        "path": (new_path or old_path) if has_position else None,
    }


def edit_mr_discussion(project, mr_iid, discussion_id, body):
    """Replace the body of the first note in an existing MR discussion.

    Used to revise a review comment in place (e.g. add a concrete fix) instead
    of stacking replies. Resolves the note id from the discussion, then PUTs the
    new body."""
    pid = encode_project_path(project)
    disc = api_request(f"/projects/{pid}/merge_requests/{mr_iid}/discussions/{discussion_id}")
    if isinstance(disc, dict) and "error" in disc:
        return disc
    notes = disc.get("notes") or []
    if not notes:
        return {"error": f"discussion {discussion_id} has no notes to edit"}
    note_id = notes[0].get("id")
    response = api_request(
        f"/projects/{pid}/merge_requests/{mr_iid}/discussions/{discussion_id}/notes/{note_id}",
        method="PUT", data={"body": body})
    if isinstance(response, dict) and "error" in response:
        return response
    return {"edited": True, "discussion_id": discussion_id, "note_id": note_id}


def reply_mr_discussion(project, mr_iid, discussion_id, body):
    """Add a follow-up note to an existing MR discussion thread (a reply)."""
    pid = encode_project_path(project)
    response = api_request(
        f"/projects/{pid}/merge_requests/{mr_iid}/discussions/{discussion_id}/notes",
        method="POST", data={"body": body})
    if isinstance(response, dict) and "error" in response:
        return response
    return {"replied": True, "discussion_id": discussion_id, "note_id": response.get("id")}


def delete_mr_discussion(project, mr_iid, discussion_id):
    """Delete the first note of an MR discussion (removes the comment).

    Resolves the note id from the discussion, then issues DELETE. Used to retract
    a review comment that turned out to be a miss."""
    pid = encode_project_path(project)
    disc = api_request(f"/projects/{pid}/merge_requests/{mr_iid}/discussions/{discussion_id}")
    if isinstance(disc, dict) and "error" in disc:
        return disc
    notes = disc.get("notes") or []
    if not notes:
        return {"error": f"discussion {discussion_id} has no notes to delete"}
    note_id = notes[0].get("id")
    result = api_request(
        f"/projects/{pid}/merge_requests/{mr_iid}/discussions/{discussion_id}/notes/{note_id}",
        method="DELETE")
    if isinstance(result, dict) and "error" in result:
        return result
    return {"deleted": True, "discussion_id": discussion_id, "note_id": note_id}


def list_pipelines(project_id, ref=None, status=None, per_page=10):
    """List recent pipelines for a project"""
    params = {"per_page": per_page, "order_by": "id", "sort": "desc"}
    if ref:
        params["ref"] = ref
    if status:
        params["status"] = status

    response = api_request(f"/projects/{project_id}/pipelines", params=params)

    if isinstance(response, dict) and "error" in response:
        return response

    return [{
        "id": p.get("id"),
        "status": p.get("status"),
        "ref": p.get("ref"),
        "source": p.get("source"),
        "created_at": p.get("created_at"),
        "updated_at": p.get("updated_at"),
        "web_url": p.get("web_url")
    } for p in response]


def get_pipeline_jobs(project_id, pipeline_id, include_log=False):
    """Get jobs for a specific pipeline, optionally including failure logs"""
    response = api_request(f"/projects/{project_id}/pipelines/{pipeline_id}/jobs",
                           params={"per_page": 50})

    if isinstance(response, dict) and "error" in response:
        return response

    jobs = []
    for j in response:
        job = {
            "id": j.get("id"),
            "name": j.get("name"),
            "stage": j.get("stage"),
            "status": j.get("status"),
            "started_at": j.get("started_at"),
            "finished_at": j.get("finished_at"),
            "duration": j.get("duration"),
            "failure_reason": j.get("failure_reason"),
            "web_url": j.get("web_url")
        }

        if include_log and j.get("status") == "failed":
            log_resp = api_request(f"/projects/{project_id}/jobs/{j['id']}/trace", raw=True)
            if isinstance(log_resp, str):
                lines = log_resp.strip().split("\n")
                job["log_tail"] = "\n".join(lines[-200:])
            elif isinstance(log_resp, dict) and "error" not in log_resp:
                job["log_tail"] = str(log_resp)[-3000:]

        jobs.append(job)

    return jobs


def trigger_pipeline(project_id, ref="dev", variables=None):
    """Trigger a CI/CD pipeline"""
    if ref.lower() in BLOCKED_REFS:
        return {"error": "Production pipelines are blocked. Use the GitLab UI for production deployments."}

    data = {"ref": ref}
    if variables:
        data["variables"] = [{"key": k, "value": v} for k, v in variables]

    response = api_request(f"/projects/{project_id}/pipeline", method="POST", data=data)

    if isinstance(response, dict) and "error" in response:
        return response

    return {
        "id": response.get("id"),
        "status": response.get("status"),
        "ref": response.get("ref"),
        "web_url": response.get("web_url")
    }


def deploy_watch(project_id, pipeline_id, poll_interval=15, max_polls=80):
    """Watch a deployment pipeline through 3 stages:
    Stage 1: Wait for init/validate jobs to complete, show summary.
    Stage 2: Report pass/fail of validate stage.
    Stage 3: Detect blocked auto-deploy (e.g., resource destruction), report for user decision.
    """
    VALIDATE_STAGE_NAMES = {"validate", "init", "plan", "terraform-plan", "terraform-validate"}
    DEPLOY_STAGE_NAMES = {"deploy", "apply", "terraform-apply", "auto-deploy", "auto_deploy"}

    def classify_jobs(jobs):
        validate_jobs = []
        deploy_jobs = []
        other_jobs = []
        for j in jobs:
            stage = (j.get("stage") or "").lower()
            name = (j.get("name") or "").lower()
            if stage in VALIDATE_STAGE_NAMES or any(v in name for v in ("validate", "init", "plan")):
                validate_jobs.append(j)
            elif stage in DEPLOY_STAGE_NAMES or any(d in name for d in ("deploy", "apply")):
                deploy_jobs.append(j)
            else:
                other_jobs.append(j)
        return validate_jobs, deploy_jobs, other_jobs

    def job_summary(j):
        return {
            "id": j.get("id"),
            "name": j.get("name"),
            "stage": j.get("stage"),
            "status": j.get("status"),
            "duration": j.get("duration"),
            "failure_reason": j.get("failure_reason"),
            "web_url": j.get("web_url"),
            "allow_failure": j.get("allow_failure", False),
        }

    def is_terminal(status):
        return status in ("success", "failed", "canceled", "skipped")

    def get_validate_log_summary(project_id, validate_jobs):
        summaries = []
        for j in validate_jobs:
            if j.get("status") in ("success", "failed"):
                log_resp = api_request(f"/projects/{project_id}/jobs/{j['id']}/trace", raw=True)
                if isinstance(log_resp, str):
                    clean = strip_ansi(log_resp)
                    plan = extract_plan_dict(j.get("name"), clean)
                    if plan:
                        summaries.append(plan)
                    errors = extract_error_lines(clean)
                    if errors:
                        summaries.append({"job": j.get("name"), "errors": errors})
        return summaries

    stages_result = {
        "pipeline_id": pipeline_id,
        "stage_1_validate": None,
        "stage_2_result": None,
        "stage_3_deploy": None,
    }

    for poll in range(max_polls):
        jobs_resp = api_request(
            f"/projects/{project_id}/pipelines/{pipeline_id}/jobs",
            params={"per_page": 100}
        )
        if isinstance(jobs_resp, dict) and "error" in jobs_resp:
            return jobs_resp

        validate_jobs, deploy_jobs, other_jobs = classify_jobs(jobs_resp)

        if validate_jobs:
            all_done = all(is_terminal(j.get("status", "")) for j in validate_jobs)
            if all_done:
                log_summaries = get_validate_log_summary(project_id, validate_jobs)
                stages_result["stage_1_validate"] = {
                    "status": "complete",
                    "jobs": [job_summary(j) for j in validate_jobs],
                    "plan_summaries": log_summaries,
                }

                failed = [j for j in validate_jobs if j.get("status") == "failed" and not j.get("allow_failure")]
                if failed:
                    stages_result["stage_2_result"] = {
                        "status": "failed",
                        "failed_jobs": [job_summary(j) for j in failed],
                        "message": "Validate stage FAILED. Pipeline will not proceed to deploy.",
                    }
                    return stages_result
                else:
                    stages_result["stage_2_result"] = {
                        "status": "passed",
                        "message": "Validate stage passed.",
                    }

                if deploy_jobs:
                    blocked, manual, running, succeeded, failed_deploy = [], [], [], [], []
                    for j in deploy_jobs:
                        status = j.get("status", "")
                        if status == "manual":
                            manual.append(j)
                        elif status in ("created", "waiting_for_resource", "pending"):
                            blocked.append(j)
                        elif status == "running":
                            running.append(j)
                        elif status == "success":
                            succeeded.append(j)
                        elif status == "failed":
                            failed_deploy.append(j)

                    if manual:
                        manual_details = []
                        for j in manual:
                            detail = job_summary(j)
                            log_resp = api_request(
                                f"/projects/{project_id}/jobs/{j['id']}/trace", raw=True
                            )
                            if isinstance(log_resp, str):
                                clean = re.sub(r'\x1b\[[0-9;]*m', '', log_resp)
                                reason_lines = [
                                    l.strip() for l in clean.split("\n")
                                    if re.search(r"\[\s*ERROR\s*\]|Error:|[Dd]estroy", l)
                                ]
                                if reason_lines:
                                    detail["blocking_reasons"] = reason_lines[:10]
                            manual_details.append(detail)

                        stages_result["stage_3_deploy"] = {
                            "status": "blocked_manual",
                            "message": "Auto-deploy is BLOCKED. Manual approval required. Review the blocking reasons and use 'play-job' to trigger manually.",
                            "manual_jobs": manual_details,
                            "play_command": "play-job <project> --job <JOB_ID>",
                        }
                    elif running:
                        stages_result["stage_3_deploy"] = {
                            "status": "deploying",
                            "message": "Deploy is running.",
                            "jobs": [job_summary(j) for j in running],
                        }
                    elif succeeded:
                        stages_result["stage_3_deploy"] = {
                            "status": "deployed",
                            "message": "Deploy completed successfully.",
                            "jobs": [job_summary(j) for j in succeeded],
                        }
                    elif failed_deploy:
                        stages_result["stage_3_deploy"] = {
                            "status": "deploy_failed",
                            "message": "Deploy job(s) FAILED.",
                            "jobs": [job_summary(j) for j in failed_deploy],
                        }
                    elif blocked:
                        stages_result["stage_3_deploy"] = {
                            "status": "waiting",
                            "message": "Deploy jobs are waiting (not yet started).",
                            "jobs": [job_summary(j) for j in blocked],
                        }
                    else:
                        stages_result["stage_3_deploy"] = {
                            "status": "unknown",
                            "jobs": [job_summary(j) for j in deploy_jobs],
                        }
                else:
                    stages_result["stage_3_deploy"] = {
                        "status": "no_deploy_jobs",
                        "message": "No deploy-stage jobs found in this pipeline.",
                    }

                return stages_result

        time.sleep(poll_interval)

    return {"error": "Timed out waiting for validate stage to complete", "partial": stages_result}


def play_job(project_id, job_id):
    """Trigger a manual/blocked job (e.g., 'apply manually' after blocked auto-deploy)."""
    response = api_request(f"/projects/{project_id}/jobs/{job_id}/play", method="POST")
    if isinstance(response, dict) and "error" in response:
        return response
    return {
        "played": True,
        "id": response.get("id"),
        "name": response.get("name"),
        "status": response.get("status"),
        "stage": response.get("stage"),
        "web_url": response.get("web_url"),
    }


def get_pipeline_bridges(project_id, pipeline_id):
    """List bridge/trigger jobs for a pipeline. These are invisible in the /jobs endpoint."""
    response = api_request(f"/projects/{project_id}/pipelines/{pipeline_id}/bridges",
                           params={"per_page": 50})

    if isinstance(response, dict) and "error" in response:
        return response

    return [{
        "id": b.get("id"),
        "name": b.get("name"),
        "stage": b.get("stage"),
        "status": b.get("status"),
        "started_at": b.get("started_at"),
        "finished_at": b.get("finished_at"),
        "duration": b.get("duration"),
        "failure_reason": b.get("failure_reason"),
        "web_url": b.get("web_url"),
        "downstream_pipeline": b.get("downstream_pipeline", {}).get("id") if b.get("downstream_pipeline") else None,
    } for b in response]


def manage_variables(project_id, action, key=None, value=None, scope=None):
    """Manage CI/CD variables"""
    if action == "set" and scope and scope.lower() in BLOCKED_SCOPES:
        return {"error": f"BLOCKED: Setting CI/CD variables on scope '{scope}' is not allowed. "
                "Only dev scope is permitted from Claude Code."}

    scope_filter = {"filter[environment_scope]": scope} if scope else {}

    if action == "list":
        response = api_request(f"/projects/{project_id}/variables")

        if isinstance(response, dict) and "error" in response:
            return response

        return [
            {
                "key": v.get("key"),
                "value": v.get("value"),
                "scope": v.get("environment_scope"),
                "protected": v.get("protected"),
                "masked": v.get("masked")
            }
            for v in response
        ]

    elif action == "get":
        if not key:
            return {"error": "get action requires --key"}

        response = api_request(f"/projects/{project_id}/variables/{key}", params=scope_filter)

        if isinstance(response, dict) and "error" in response:
            return response

        return {
            "key": response.get("key"),
            "value": response.get("value"),
            "scope": response.get("environment_scope"),
            "protected": response.get("protected"),
            "masked": response.get("masked")
        }

    elif action == "set":
        if not key or value is None:
            return {"error": "set action requires --key and --value"}

        update_response = api_request(
            f"/projects/{project_id}/variables/{key}",
            method="PUT",
            params=scope_filter,
            data={"value": value}
        )

        if isinstance(update_response, dict) and "error" in update_response:
            error_text = update_response.get("error", "")
            if "404" in error_text:
                create_data = {"key": key, "value": value}
                if scope:
                    create_data["environment_scope"] = scope
                create_response = api_request(
                    f"/projects/{project_id}/variables",
                    method="POST",
                    data=create_data
                )
                if isinstance(create_response, dict) and "error" in create_response:
                    return create_response
                return {"action": "created", "key": create_response.get("key"), "value": create_response.get("value"), "scope": create_response.get("environment_scope")}
            return update_response

        return {"action": "updated", "key": update_response.get("key"), "value": update_response.get("value"), "scope": update_response.get("environment_scope")}

    else:
        return {"error": f"Unknown vars action: {action}. Use: list, get, set"}


def _resolve_or_error(name_or_id):
    """Resolve project name/ID via index. Returns (int_id, None) or (None, error_dict)."""
    pid = resolve_project_id(name_or_id, current_org["name"])
    if pid is None:
        return None, {"error": f"Could not resolve project '{name_or_id}'. Run 'index' to rebuild."}
    return pid, None


def _build_parser():
    """Build the argparse parser with all subcommands."""
    import argparse

    parser = argparse.ArgumentParser(prog="gitlab_skill.py", description="GitLab CLI for Claude Code")
    parser.add_argument("--org", help="Organization override (auto-detected from $PWD)")

    sub = parser.add_subparsers(dest="command")

    # list-groups
    p = sub.add_parser("list-groups")
    p.add_argument("--full", action="store_true")

    # list-repos
    p = sub.add_parser("list-repos")
    p.add_argument("--group", dest="group_id")
    p.add_argument("--all", action="store_true", dest="all_repos")
    p.add_argument("--full", action="store_true")

    # get-repo (now resolves names)
    p = sub.add_parser("get-repo")
    p.add_argument("project", help="Project name or numeric ID")
    p.add_argument("--full", action="store_true")

    # search
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--max", type=int, default=20, dest="max_results")

    # clone
    p = sub.add_parser("clone")
    p.add_argument("--group", required=True, dest="group_id")
    p.add_argument("--repos", dest="repo_list")
    p.add_argument("--output", dest="output_dir")

    # mr (now resolves project names)
    p = sub.add_parser("mr")
    p.add_argument("--project", required=True)
    p.add_argument("--action", required=True, choices=["create", "list", "approve", "merge", "auto-merge", "update"])
    p.add_argument("--title")
    p.add_argument("--source")
    p.add_argument("--target")
    p.add_argument("--mr-iid")
    p.add_argument("--description")
    p.add_argument("--description-file")

    # mr-diff: fetch MR metadata + per-file diffs + diff_refs for review
    p = sub.add_parser("mr-diff")
    p.add_argument("--project", required=True, help="numeric ID or full namespace path")
    p.add_argument("--mr-iid", required=True)

    # mr-note: post a discussion on an MR (inline when position args given)
    p = sub.add_parser("mr-note")
    p.add_argument("--project", required=True, help="numeric ID or full namespace path")
    p.add_argument("--mr-iid", required=True)
    p.add_argument("--body")
    p.add_argument("--body-file")
    p.add_argument("--new-path")
    p.add_argument("--new-line")
    p.add_argument("--old-path")
    p.add_argument("--old-line")
    p.add_argument("--base-sha")
    p.add_argument("--head-sha")
    p.add_argument("--start-sha")

    # mr-note-edit: replace the body of an existing discussion's note
    p = sub.add_parser("mr-note-edit")
    p.add_argument("--project", required=True, help="numeric ID or full namespace path")
    p.add_argument("--mr-iid", required=True)
    p.add_argument("--discussion-id", required=True)
    p.add_argument("--body")
    p.add_argument("--body-file")

    # mr-note-reply: add a follow-up note to an existing discussion thread
    p = sub.add_parser("mr-note-reply")
    p.add_argument("--project", required=True, help="numeric ID or full namespace path")
    p.add_argument("--mr-iid", required=True)
    p.add_argument("--discussion-id", required=True)
    p.add_argument("--body")
    p.add_argument("--body-file")

    # mr-note-delete: retract a discussion's comment
    p = sub.add_parser("mr-note-delete")
    p.add_argument("--project", required=True, help="numeric ID or full namespace path")
    p.add_argument("--mr-iid", required=True)
    p.add_argument("--discussion-id", required=True)

    # pipelines
    p = sub.add_parser("pipelines")
    p.add_argument("project", nargs="?")
    p.add_argument("--project", dest="project_flag")
    p.add_argument("--ref")
    p.add_argument("--status")
    p.add_argument("--count", type=int, default=10)

    # jobs
    p = sub.add_parser("jobs")
    p.add_argument("project", nargs="?")
    p.add_argument("--project", dest="project_flag")
    p.add_argument("--pipeline", required=True)
    p.add_argument("--logs", action="store_true")

    # bridges
    p = sub.add_parser("bridges")
    p.add_argument("project", nargs="?")
    p.add_argument("--project", dest="project_flag")
    p.add_argument("--pipeline", required=True)

    # trace
    p = sub.add_parser("trace")
    p.add_argument("project", nargs="?")
    p.add_argument("--project", dest="project_flag")
    p.add_argument("--job", required=True)
    p.add_argument("--filter")

    # pipeline (trigger)
    p = sub.add_parser("pipeline")
    p.add_argument("project", nargs="?")
    p.add_argument("--project", dest="project_flag")
    p.add_argument("--ref", default="dev")
    p.add_argument("--var", action="append", default=[])

    # vars
    p = sub.add_parser("vars")
    p.add_argument("project", nargs="?")
    p.add_argument("--project", dest="project_flag")
    p.add_argument("--action", required=True, choices=["list", "get", "set"])
    p.add_argument("--key")
    p.add_argument("--value")
    p.add_argument("--scope")

    # deploy-watch
    p = sub.add_parser("deploy-watch")
    p.add_argument("project", nargs="?")
    p.add_argument("--project", dest="project_flag")
    p.add_argument("--pipeline", required=True)
    p.add_argument("--interval", type=int, default=15)

    # play-job
    p = sub.add_parser("play-job")
    p.add_argument("project", nargs="?")
    p.add_argument("--project", dest="project_flag")
    p.add_argument("--job", required=True)

    # index
    p = sub.add_parser("index")
    p.add_argument("--group", dest="group_override")

    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        print(json.dumps({"error": "No command specified"}))
        sys.exit(1)

    _init(args.org)
    result = None

    try:
        cmd = args.command

        if cmd == "list-groups":
            result = list_groups(full=args.full)

        elif cmd == "list-repos":
            result = list_repos(group_id=args.group_id, all_repos=args.all_repos, full=args.full)

        elif cmd == "get-repo":
            pid, err = _resolve_or_error(args.project)
            result = err or get_repo(pid, full=args.full)

        elif cmd == "search":
            result = search_repos(args.query, max_results=args.max_results)

        elif cmd == "clone":
            result = clone_repos(args.group_id, repo_list=args.repo_list, output_dir=args.output_dir)

        elif cmd == "mr":
            pid, err = _resolve_or_error(args.project)
            if err:
                result = err
            else:
                description = None
                if args.description_file:
                    try:
                        with open(args.description_file, "r") as f:
                            description = f.read()
                    except FileNotFoundError:
                        result = {"error": f"Description file not found: {args.description_file}"}
                        print(json.dumps(result, indent=2))
                        sys.exit(1)
                elif args.description:
                    description = args.description
                result = manage_merge_request(pid, args.action,
                                             title=args.title, source=args.source,
                                             target=args.target, mr_iid=args.mr_iid,
                                             description=description)

        elif cmd == "mr-diff":
            result = get_mr_review(args.project, args.mr_iid)

        elif cmd == "mr-note":
            body = args.body
            if args.body_file:
                try:
                    with open(args.body_file, "r") as f:
                        body = f.read()
                except FileNotFoundError:
                    print(json.dumps({"error": f"Body file not found: {args.body_file}"}, indent=2))
                    sys.exit(1)
            if not body:
                result = {"error": "mr-note requires --body or --body-file"}
            else:
                result = post_mr_note(
                    args.project, args.mr_iid, body,
                    new_path=args.new_path, new_line=args.new_line,
                    old_path=args.old_path, old_line=args.old_line,
                    base_sha=args.base_sha, head_sha=args.head_sha,
                    start_sha=args.start_sha,
                )

        elif cmd == "mr-note-edit":
            body = args.body
            if args.body_file:
                try:
                    with open(args.body_file, "r") as f:
                        body = f.read()
                except FileNotFoundError:
                    print(json.dumps({"error": f"Body file not found: {args.body_file}"}, indent=2))
                    sys.exit(1)
            if not body:
                result = {"error": "mr-note-edit requires --body or --body-file"}
            else:
                result = edit_mr_discussion(args.project, args.mr_iid, args.discussion_id, body)

        elif cmd == "mr-note-reply":
            body = args.body
            if args.body_file:
                try:
                    with open(args.body_file, "r") as f:
                        body = f.read()
                except FileNotFoundError:
                    print(json.dumps({"error": f"Body file not found: {args.body_file}"}, indent=2))
                    sys.exit(1)
            if not body:
                result = {"error": "mr-note-reply requires --body or --body-file"}
            else:
                result = reply_mr_discussion(args.project, args.mr_iid, args.discussion_id, body)

        elif cmd == "mr-note-delete":
            result = delete_mr_discussion(args.project, args.mr_iid, args.discussion_id)

        elif cmd == "pipelines":
            name = args.project_flag or args.project
            if not name:
                result = {"error": "pipelines requires project name or ID"}
            else:
                pid, err = _resolve_or_error(name)
                result = err or list_pipelines(pid, ref=args.ref, status=args.status, per_page=args.count)

        elif cmd == "jobs":
            name = args.project_flag or args.project
            if not name:
                result = {"error": "jobs requires project name or ID"}
            else:
                pid, err = _resolve_or_error(name)
                result = err or get_pipeline_jobs(pid, args.pipeline, include_log=args.logs)

        elif cmd == "bridges":
            name = args.project_flag or args.project
            if not name:
                result = {"error": "bridges requires project name or ID"}
            else:
                pid, err = _resolve_or_error(name)
                result = err or get_pipeline_bridges(pid, args.pipeline)

        elif cmd == "trace":
            name = args.project_flag or args.project
            if not name:
                result = {"error": "trace requires project name or ID"}
            else:
                pid, err = _resolve_or_error(name)
                if err:
                    result = err
                else:
                    log_resp = api_request(f"/projects/{pid}/jobs/{args.job}/trace", raw=True)
                    if isinstance(log_resp, dict) and "error" in log_resp:
                        result = log_resp
                    elif isinstance(log_resp, str):
                        clean = re.sub(r'\x1b\[[0-9;]*m', '', log_resp)
                        lines = clean.strip().split("\n")
                        if args.filter:
                            kw = args.filter.lower()
                            filtered = [f"L{i}: {l.rstrip()}" for i, l in enumerate(lines) if kw in l.lower()]
                            result = {"job_id": args.job, "total_lines": len(lines),
                                      "filter": kw, "matched_lines": len(filtered),
                                      "output": "\n".join(filtered[:100])}
                        else:
                            result = {"job_id": args.job, "total_lines": len(lines),
                                      "output": "\n".join(lines[:500])}
                    else:
                        result = {"error": "Unexpected response type from trace endpoint"}

        elif cmd == "pipeline":
            name = args.project_flag or args.project
            if not name:
                result = {"error": "pipeline requires project name or ID"}
            else:
                pid, err = _resolve_or_error(name)
                if err:
                    result = err
                else:
                    variables = []
                    for kv in args.var:
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            variables.append((k, v))
                    result = trigger_pipeline(pid, ref=args.ref,
                                             variables=variables if variables else None)

        elif cmd == "vars":
            name = args.project_flag or args.project
            if not name:
                result = {"error": "vars requires project name or ID"}
            else:
                pid, err = _resolve_or_error(name)
                result = err or manage_variables(pid, args.action,
                                                key=args.key, value=args.value, scope=args.scope)

        elif cmd == "deploy-watch":
            name = args.project_flag or args.project
            if not name:
                result = {"error": "deploy-watch requires project name or ID"}
            else:
                pid, err = _resolve_or_error(name)
                result = err or deploy_watch(pid, args.pipeline, poll_interval=args.interval)

        elif cmd == "play-job":
            name = args.project_flag or args.project
            if not name:
                result = {"error": "play-job requires project name or ID"}
            else:
                pid, err = _resolve_or_error(name)
                result = err or play_job(pid, args.job)

        elif cmd == "index":
            index_data = run_index(group_override=args.group_override)
            if isinstance(index_data, dict) and "error" in index_data:
                result = index_data
            else:
                org_name = current_org["name"]
                org_projects = index_data.get("organizations", {}).get(org_name, {})
                seen = {}
                for alias, info in org_projects.items():
                    pid = info["id"]
                    if pid not in seen:
                        seen[pid] = {"id": pid, "name": alias, "path": info["path"]}
                result = {
                    "indexed": True,
                    "organization": org_name,
                    "project_count": len(seen),
                    "projects": list(seen.values()),
                    "index_file": INDEX_FILE
                }

        print(json.dumps(result, indent=2))

    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

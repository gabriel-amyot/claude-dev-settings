#!/usr/bin/env python3
"""Jira CLI for Claude Code - minimal, token-efficient interface"""
import os
import sys
import json
import subprocess
from pathlib import Path
from jira import JIRA

# Configuration
CONFIG_FILE = os.path.expanduser("~/.claude-shared-config/skills/jira/jira_config.json")
KEYCHAIN_SERVICE = "claude-jira"


def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def get_token_from_keychain(org_name):
    """Retrieve Jira token from macOS Keychain"""
    account = f"jira_{org_name}"
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
    except Exception:
        return None


def detect_organization(config):
    """Detect organization from current working directory"""
    cwd = os.getcwd()
    orgs = config.get("organizations", {})

    # Find orgs whose local_path is a parent of cwd
    matches = []
    for org_name, org_config in orgs.items():
        local_path = org_config.get("local_path")
        if local_path and cwd.startswith(local_path):
            matches.append((org_name, len(local_path)))

    if matches:
        # Return longest matching path (most specific)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0][0]

    # Fallback to default
    return config.get("default_org")


def get_org_config(org_name=None):
    """Get organization configuration with auto-detection"""
    config = load_config()

    # If no config file, use environment variables (backward compatibility)
    if not config:
        return None

    # Manual override via --org flag
    if org_name:
        if org_name not in config.get("organizations", {}):
            available = ", ".join(config.get("organizations", {}).keys())
            print(json.dumps({"error": f"Organization '{org_name}' not found. Available: {available}"}))
            sys.exit(1)
    else:
        # Auto-detect from path
        org_name = detect_organization(config)

        if not org_name:
            print(json.dumps({"error": "Could not detect organization and no default set"}))
            sys.exit(1)

    org_config = config["organizations"][org_name]
    token = get_token_from_keychain(org_name)

    if not token:
        print(json.dumps({"error": f"No token for '{org_name}'. Run: jira_config_setup.py configure {org_name}"}))
        sys.exit(1)

    return {
        "name": org_name,
        "url": org_config.get("jira_url"),
        "username": org_config.get("jira_username"),
        "token": token,
        "local_path": org_config.get("local_path"),
        "default_project": org_config.get("default_project")
    }


def display_org_disclaimer(org_config):
    """Display organization info (non-interactive disclaimer)"""
    if "--skip-disclaimer" in sys.argv:
        return

    # Print to stderr so JSON output stays clean
    print(f"ℹ️  Using organization: {org_config['name']}", file=sys.stderr)
    print(f"   Jira: {org_config['url']} ({org_config['username']})", file=sys.stderr)
    if org_config.get('local_path'):
        print(f"   Path: {org_config['local_path']}", file=sys.stderr)
    print("", file=sys.stderr)


# Initialize Jira client
url = None
username = None
token = None

# Parse --org flag if present
org_name = None
if "--org" in sys.argv:
    idx = sys.argv.index("--org")
    if idx + 1 < len(sys.argv):
        org_name = sys.argv[idx + 1]

# Try config-based approach
current_org = get_org_config(org_name)

if current_org:
    display_org_disclaimer(current_org)
    url = current_org["url"]
    username = current_org["username"]
    token = current_org["token"]
else:
    # Fallback to environment variables (backward compatibility)
    url = os.getenv("JIRA_URL")
    username = os.getenv("JIRA_USERNAME")
    token = os.getenv("JIRA_API_TOKEN")

if not all([url, username, token]):
    print(json.dumps({"error": "Missing JIRA config and environment variables"}))
    sys.exit(1)

try:
    jira = JIRA(server=url, basic_auth=(username, token))
except Exception as e:
    print(json.dumps({"error": f"Connection failed: {str(e)}"}))
    sys.exit(1)


def safe_get(obj, *attrs):
    """Safely get nested attributes"""
    for attr in attrs:
        if obj is None:
            return None
        try:
            obj = getattr(obj, attr, None)
        except:
            return None
    return obj


def get_assignee_name(assignee):
    """Get assignee name safely"""
    if not assignee:
        return None
    try:
        return assignee.displayName
    except:
        try:
            return str(assignee)
        except:
            return None


def compact_issue(issue):
    """Minimal issue format"""
    return {
        "key": issue.key,
        "summary": issue.fields.summary,
        "status": safe_get(issue.fields.status, "name") or "Unknown"
    }


def full_issue(issue):
    """Full issue details"""
    sprint_value = safe_get(issue.fields.customfield_10020)
    sprint_str = str(sprint_value) if sprint_value else None

    return {
        "key": issue.key,
        "summary": issue.fields.summary,
        "description": safe_get(issue.fields.description) or "",
        "status": safe_get(issue.fields.status, "name") or "Unknown",
        "type": safe_get(issue.fields.issuetype, "name") or "Unknown",
        "priority": safe_get(issue.fields.priority, "name"),
        "assignee": get_assignee_name(safe_get(issue.fields.assignee)),
        "reporter": get_assignee_name(safe_get(issue.fields.reporter)),
        "created": str(safe_get(issue.fields.created)) or "",
        "updated": str(safe_get(issue.fields.updated)) or "",
        "estimate": safe_get(issue.fields.customfield_10016),
        "sprint": sprint_str,
        "epic_key": safe_get(issue.fields.customfield_10014),
        "url": f"{url}/browse/{issue.key}"
    }


def list_issues(jql=None, max_results=20, full=False):
    """List issues"""
    if not jql:
        jql = "assignee = currentUser() AND status NOT IN (Done, \"Won't Do\")"
    
    try:
        issues = jira.search_issues(jql, maxResults=max_results)
        formatter = full_issue if full else compact_issue
        return [formatter(i) for i in issues]
    except Exception as e:
        return {"error": str(e)}


def get_issue(key, full=False):
    """Get single issue"""
    try:
        issue = jira.issue(key)
        return full_issue(issue) if full else compact_issue(issue)
    except Exception as e:
        return {"error": str(e)}


def get_subtasks(key):
    """List subtasks"""
    try:
        issue = jira.issue(key)
        subtasks = safe_get(issue.fields.subtasks) or []
        return [compact_issue(s) for s in subtasks]
    except Exception as e:
        return {"error": str(e)}


def get_epic(key):
    """Get parent epic"""
    try:
        issue = jira.issue(key)
        epic_key = safe_get(issue.fields.customfield_10014)
        if not epic_key:
            return None
        epic = jira.issue(epic_key)
        return compact_issue(epic)
    except Exception as e:
        return {"error": str(e)}


def get_comments(key):
    """Get all comments for an issue"""
    try:
        issue = jira.issue(key, expand='changelog')
        comments = jira.comments(issue)
        result = []
        for comment in comments:
            result.append({
                "id": comment.id,
                "author": get_assignee_name(comment.author),
                "created": str(comment.created),
                "updated": str(comment.updated) if hasattr(comment, 'updated') else None,
                "body": comment.body
            })
        return result
    except Exception as e:
        return {"error": str(e)}


def get_raw_description(key):
    """Get raw description without processing"""
    try:
        issue = jira.issue(key)
        return {
            "key": issue.key,
            "description": issue.fields.description or ""
        }
    except Exception as e:
        return {"error": str(e)}


def get_attachments(key):
    """Get all attachments for an issue"""
    try:
        issue = jira.issue(key)
        attachments = issue.fields.attachment or []
        result = []
        for attachment in attachments:
            result.append({
                "id": attachment.id,
                "filename": attachment.filename,
                "size": attachment.size,
                "created": str(attachment.created),
                "author": get_assignee_name(attachment.author),
                "content_type": attachment.mimeType,
                "url": attachment.content
            })
        return result
    except Exception as e:
        return {"error": str(e)}


def download_attachment(attachment_url, filename, output_dir="."):
    """Download a single attachment using authenticated session"""
    try:
        import os

        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)

        # Use Jira's authenticated session to download
        response = jira._session.get(attachment_url, stream=True)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "size": os.path.getsize(filepath)
        }
    except Exception as e:
        return {"error": str(e)}


def _sprint_name(sprint_field):
    """Extract human-readable sprint name from Jira sprint field."""
    if not sprint_field:
        return None
    import re
    try:
        items = list(sprint_field) if hasattr(sprint_field, '__iter__') and not isinstance(sprint_field, str) else [sprint_field]
    except Exception:
        items = [sprint_field]
    names = []
    for item in items:
        raw = str(item)
        m = re.search(r"name=([^,\]]+)", raw)
        if m:
            names.append(m.group(1).strip())
        else:
            # Try accessing .name attribute directly (next-gen sprint objects)
            name_attr = getattr(item, 'name', None)
            if name_attr:
                names.append(str(name_attr))
    return names if len(names) > 1 else (names[0] if names else None)


def get_all_metadata(key):
    """Get all available metadata for an issue"""
    try:
        issue = jira.issue(key)

        # Get all custom fields
        metadata = {
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": safe_get(issue.fields.status, "name"),
            "status_category": safe_get(issue.fields.status, "statusCategory", "name"),
            "type": safe_get(issue.fields.issuetype, "name"),
            "priority": safe_get(issue.fields.priority, "name"),
            "assignee": get_assignee_name(safe_get(issue.fields.assignee)),
            "assignee_email": safe_get(issue.fields.assignee, "emailAddress"),
            "reporter": get_assignee_name(safe_get(issue.fields.reporter)),
            "reporter_email": safe_get(issue.fields.reporter, "emailAddress"),
            "creator": get_assignee_name(safe_get(issue.fields.creator)),
            "created": str(safe_get(issue.fields.created)) or "",
            "updated": str(safe_get(issue.fields.updated)) or "",
            "resolution": safe_get(issue.fields.resolution, "name"),
            "resolution_date": str(safe_get(issue.fields.resolutiondate)) if safe_get(issue.fields.resolutiondate) else None,
            "labels": list(issue.fields.labels) if issue.fields.labels else [],
            "components": [c.name for c in issue.fields.components] if issue.fields.components else [],
            "fix_versions": [v.name for v in issue.fields.fixVersions] if issue.fields.fixVersions else [],
            "affects_versions": [v.name for v in issue.fields.versions] if issue.fields.versions else [],
            "estimate": safe_get(issue.fields.customfield_10016),
            "time_spent": safe_get(issue.fields.timespent),
            "time_estimate": safe_get(issue.fields.timeestimate),
            "sprint": _sprint_name(safe_get(issue.fields.customfield_10020)),
            "epic_key": safe_get(issue.fields.customfield_10014),
            "epic_name": getattr(issue.fields, 'customfield_10011', None),
            "parent_key": safe_get(issue.fields.parent, "key") if hasattr(issue.fields, 'parent') and issue.fields.parent else None,
            "subtasks_count": len(issue.fields.subtasks) if issue.fields.subtasks else 0,
            "watches": safe_get(issue.fields.watches, "watchCount"),
            "votes": safe_get(issue.fields.votes, "votes"),
            "environment": safe_get(issue.fields.environment),
            "due_date": str(safe_get(issue.fields.duedate)) if safe_get(issue.fields.duedate) else None,
            "project_key": safe_get(issue.fields.project, "key"),
            "project_name": safe_get(issue.fields.project, "name"),
            "url": f"{url}/browse/{issue.key}"
        }

        # Get linked issues
        if issue.fields.issuelinks:
            links = []
            for link in issue.fields.issuelinks:
                link_info = {"type": link.type.name}
                if hasattr(link, 'outwardIssue') and link.outwardIssue:
                    link_info["direction"] = "outward"
                    link_info["key"] = link.outwardIssue.key
                    link_info["summary"] = link.outwardIssue.fields.summary
                elif hasattr(link, 'inwardIssue') and link.inwardIssue:
                    link_info["direction"] = "inward"
                    link_info["key"] = link.inwardIssue.key
                    link_info["summary"] = link.inwardIssue.fields.summary
                links.append(link_info)
            metadata["links"] = links
        else:
            metadata["links"] = []

        return metadata
    except Exception as e:
        return {"error": str(e)}


def search(jql, max_results=20, full=False):
    """Search with JQL"""
    try:
        issues = jira.search_issues(jql, maxResults=max_results)
        formatter = full_issue if full else compact_issue
        return [formatter(i) for i in issues]
    except Exception as e:
        return {"error": str(e)}


def create_issue(summary, issue_type, project=None, description=None, assignee=None, labels=None):
    """Create a new issue"""
    if not project:
        return {"error": "project is required"}

    try:
        fields = {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": issue_type}
        }

        if description:
            fields["description"] = markdown_to_jira_wiki(description)

        if assignee:
            fields["assignee"] = {"name": assignee}

        if labels:
            fields["labels"] = labels if isinstance(labels, list) else [labels]

        issue = jira.create_issue(fields=fields)
        return {
            "created": True,
            "key": issue.key,
            "summary": summary,
            "project": project,
            "url": f"{url}/browse/{issue.key}"
        }
    except Exception as e:
        return {"error": str(e)}


def transition_issue(key, status_name):
    """Transition an issue to a new status"""
    try:
        issue = jira.issue(key)
        transitions = jira.transitions(issue)

        target_transition = None
        available = []
        for t in transitions:
            available.append(t['name'])
            if t['name'].upper() == status_name.upper():
                target_transition = t
                break

        if not target_transition:
            return {
                "error": f"Status '{status_name}' not available. Available: {available}"
            }

        jira.transition_issue(issue, target_transition['id'])

        updated_issue = jira.issue(key)
        return {
            "success": True,
            "key": key,
            "previous_status": safe_get(issue.fields.status, "name"),
            "new_status": safe_get(updated_issue.fields.status, "name")
        }
    except Exception as e:
        return {"error": str(e)}


def update_issue(key, description=None, summary=None):
    """Update issue fields (description, summary)"""
    try:
        issue = jira.issue(key)
        fields = {}

        if description is not None:
            fields["description"] = markdown_to_jira_wiki(description)

        if summary is not None:
            fields["summary"] = summary

        if not fields:
            return {"error": "No fields to update. Provide --description or --summary"}

        issue.update(fields=fields)

        updated_issue = jira.issue(key)
        return {
            "success": True,
            "key": key,
            "updated_fields": list(fields.keys()),
            "url": f"{url}/browse/{key}"
        }
    except Exception as e:
        return {"error": str(e)}


def markdown_to_jira_wiki(text):
    """Convert markdown to Jira wiki markup"""
    import re
    lines = text.split('\n')
    result = []
    for line in lines:
        # Headers: ## → h2., ### → h3., etc.
        line = re.sub(r'^######\s+', 'h6. ', line)
        line = re.sub(r'^#####\s+', 'h5. ', line)
        line = re.sub(r'^####\s+', 'h4. ', line)
        line = re.sub(r'^###\s+', 'h3. ', line)
        line = re.sub(r'^##\s+', 'h2. ', line)
        line = re.sub(r'^#\s+', 'h1. ', line)
        # Bold: **text** → *text*
        line = re.sub(r'\*\*(.+?)\*\*', r'*\1*', line)
        # Bullet lists: - item → * item
        line = re.sub(r'^- ', '* ', line)
        result.append(line)
    return '\n'.join(result)


def add_comment(key, comment_body):
    """Add a comment to an issue"""
    try:
        issue = jira.issue(key)
        comment = jira.add_comment(issue, markdown_to_jira_wiki(comment_body))

        return {
            "success": True,
            "key": key,
            "comment_id": comment.id,
            "comment_author": get_assignee_name(comment.author),
            "comment_created": str(comment.created),
            "comment_body": comment.body,
            "url": f"{url}/browse/{key}"
        }
    except Exception as e:
        return {"error": str(e)}


def list_transitions(key):
    """List available transitions for an issue"""
    try:
        issue = jira.issue(key)
        transitions = jira.transitions(issue)
        return {
            "key": key,
            "current_status": safe_get(issue.fields.status, "name"),
            "available_transitions": [t['name'] for t in transitions]
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# fetch: materialize a ticket (and optionally its children) to disk
# ---------------------------------------------------------------------------

def _parse_description_sections(description_text):
    """
    Split a Jira description into three logical parts:
      - overview  : context / why this ticket exists (text before any recognized section)
      - criteria  : acceptance criteria items as a list (from AC / DoD section)
      - technical : implementation / design notes (from Technical / Implementation section)

    Returns a dict with keys: overview (str), criteria (list), technical (str).
    Any part may be empty string / empty list if not found.
    """
    import re

    if not description_text:
        return {"overview": "", "criteria": [], "technical": ""}

    text = description_text.replace("\r\n", "\n").replace("\r", "\n")

    # Section header patterns — order matters (AC checked before Technical)
    SECTION_PATTERNS = {
        "ac": re.compile(
            r"(?im)^[#*_\s]*"
            r"(acceptance[\s_]criteria|ac\s*:|definition[\s_]of[\s_]done|dod\s*:|done[\s_]criteria)"
            r"[\s:*_#]*$"
        ),
        "technical": re.compile(
            r"(?im)^[#*_\s]*"
            r"(technical[\s_]?(notes?|details?|spec(ification)?|design)?|"
            r"implementation[\s_]?(notes?|details?|plan)?|"
            r"design[\s_]?(notes?|recommendations?)?|"
            r"how[\s_]to[\s_]implement)"
            r"[\s:*_#]*$"
        ),
    }

    # Find all section boundaries
    hits = []
    for section_type, pattern in SECTION_PATTERNS.items():
        for m in pattern.finditer(text):
            hits.append((m.start(), m.end(), section_type))
    hits.sort(key=lambda x: x[0])

    if not hits:
        return {"overview": text.strip(), "criteria": [], "technical": ""}

    overview = text[: hits[0][0]].strip()

    # Extract each section's raw content
    raw_sections = {}
    for i, (start, end, stype) in enumerate(hits):
        next_start = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        raw_sections[stype] = text[end:next_start].strip()

    # Parse AC items
    criteria = []
    for line in raw_sections.get("ac", "").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        item = re.sub(r"^[-*+]\s+|\[\s*[xX ]?\]\s*|^\d+\.\s+", "", stripped)
        if item:
            criteria.append(item)

    technical = raw_sections.get("technical", "")

    return {"overview": overview, "criteria": criteria, "technical": technical}


def _write_yaml(path, data):
    """Write data as YAML without depending on pyyaml being installed."""
    try:
        import yaml
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except ImportError:
        # Fallback: write as JSON with .yaml extension (still valid for most consumers)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def _sanitize_filename(text, max_len=60):
    import re
    text = re.sub(r"[^\w\s-]", "", text).strip()
    text = re.sub(r"\s+", "-", text).lower()
    return text[:max_len]


def fetch_ticket(key, output_dir, depth=1, _visited=None):
    """
    Materialize a Jira ticket to disk under output_dir/KEY/.

    Structure written:
      KEY/
        ticket-overview.md   — machine-generated summary (always refreshed)
        README.md            — only written if absent (preserved if user edited it)
        jira/
          ticket.yaml        — full metadata incl. children refs
          description.md     — verbatim raw description (backup)
          overview.md        — context / "why" section of description
          ac.yaml            — acceptance criteria items (omitted if none found)
          technical.md       — implementation / design notes (omitted if none found)
          comments/          — only created if comments exist
            index.yaml
            comment-NNN-<slug>.md
    """
    import os

    if _visited is None:
        _visited = set()
    if key in _visited:
        return {"skipped": key, "reason": "already_fetched"}
    _visited.add(key)

    ticket_dir = os.path.join(output_dir, key)
    jira_dir = os.path.join(ticket_dir, "jira")
    os.makedirs(jira_dir, exist_ok=True)

    # ── 1. Metadata ──────────────────────────────────────────────────────────
    meta = get_all_metadata(key)
    if "error" in meta:
        return meta

    # ── 2. Description → sections ────────────────────────────────────────────
    desc_data = get_raw_description(key)
    description_text = desc_data.get("description", "") if isinstance(desc_data, dict) else ""
    sections = _parse_description_sections(description_text)
    overview_text = sections["overview"]
    criteria = sections["criteria"]
    technical_text = sections["technical"]

    # ── 3. Children (subtasks + epic children) ───────────────────────────────
    children = []
    raw_subtasks = get_subtasks(key)
    if isinstance(raw_subtasks, list):
        children.extend(raw_subtasks)

    if meta.get("type") == "Epic":
        epic_children = search(f'project = {meta["project_key"]} AND "Epic Link" = {key}', max_results=100)
        if isinstance(epic_children, list):
            for c in epic_children:
                if not any(x["key"] == c["key"] for x in children):
                    children.append(c)
        parent_children = search(f'parent = {key}', max_results=100)
        if isinstance(parent_children, list):
            for c in parent_children:
                if not any(x["key"] == c["key"] for x in children):
                    children.append(c)

    # ── 4. jira/ticket.yaml — full metadata ──────────────────────────────────
    ticket_yaml = {
        "key": meta["key"],
        "summary": meta["summary"],
        "status": meta["status"],
        "type": meta["type"],
        "priority": meta.get("priority"),
        "assignee": meta.get("assignee"),
        "reporter": meta.get("reporter"),
        "created": meta.get("created"),
        "updated": meta.get("updated"),
        "parent_key": meta.get("parent_key"),
        "epic_key": meta.get("epic_key"),
        "labels": meta.get("labels", []),
        "components": meta.get("components", []),
        "resolution": meta.get("resolution"),
        "estimate": meta.get("estimate"),
        "sprint": meta.get("sprint"),
        "url": meta.get("url"),
        "links": meta.get("links", []),
    }
    if children:
        ticket_yaml["children"] = [
            {"key": c["key"], "summary": c["summary"], "status": c.get("status", "Unknown"), "local_path": f"./{c['key']}/"}
            for c in children
        ]
    _write_yaml(os.path.join(jira_dir, "ticket.yaml"), ticket_yaml)

    # ── 5. jira/description.md — verbatim backup ─────────────────────────────
    if description_text:
        with open(os.path.join(jira_dir, "description.md"), "w", encoding="utf-8") as f:
            f.write(f"# {meta['key']}: {meta['summary']}\n\n")
            f.write(description_text)

    # ── 6. jira/overview.md — context / why ──────────────────────────────────
    if overview_text:
        with open(os.path.join(jira_dir, "overview.md"), "w", encoding="utf-8") as f:
            f.write(f"# {meta['key']}: Overview\n\n")
            f.write(overview_text)

    # ── 7. jira/ac.yaml — acceptance criteria ────────────────────────────────
    if criteria:
        _write_yaml(
            os.path.join(jira_dir, "ac.yaml"),
            {"ticket": key, "acceptance_criteria": criteria},
        )

    # ── 8. jira/technical.md — implementation / design notes ─────────────────
    if technical_text:
        with open(os.path.join(jira_dir, "technical.md"), "w", encoding="utf-8") as f:
            f.write(f"# {meta['key']}: Technical Notes\n\n")
            f.write(technical_text)

    # ── 9. jira/comments/ ────────────────────────────────────────────────────
    comments = get_comments(key)
    if isinstance(comments, list) and comments:
        comments_dir = os.path.join(jira_dir, "comments")
        os.makedirs(comments_dir, exist_ok=True)
        index = []
        for i, comment in enumerate(comments, start=1):
            body = comment.get("body", "")
            preview = body.replace("\n", " ").strip()[:100]
            slug = _sanitize_filename(preview) or f"comment-{i}"
            filename = f"comment-{i:03d}-{slug}.md"
            with open(os.path.join(comments_dir, filename), "w", encoding="utf-8") as f:
                f.write(f"# Comment {i:03d} — {comment.get('author', 'unknown')}\n")
                f.write(f"**Date:** {comment.get('created', '')}\n\n")
                f.write("---\n\n")
                f.write(body)
            index.append({
                "file": filename,
                "id": comment.get("id"),
                "author": comment.get("author"),
                "created": comment.get("created"),
                "preview": preview[:100],
            })
        _write_yaml(os.path.join(comments_dir, "index.yaml"), {"ticket": key, "comments": index})

    # ── 10. ticket-overview.md — machine summary, always refreshed ───────────
    ov_lines = [
        f"# {meta['key']}: {meta['summary']}",
        "",
        f"**Status:** {meta['status']}  ",
        f"**Type:** {meta['type']}  ",
        f"**Priority:** {meta.get('priority', '—')}  ",
        f"**Assignee:** {meta.get('assignee') or '—'}  ",
        f"**Reporter:** {meta.get('reporter') or '—'}  ",
    ]
    if meta.get("parent_key"):
        ov_lines.append(f"**Parent:** {meta['parent_key']}  ")
    if meta.get("epic_key") and meta.get("epic_key") != meta.get("parent_key"):
        ov_lines.append(f"**Epic:** {meta['epic_key']}  ")
    if meta.get("sprint"):
        sprint_val = meta["sprint"]
        sprint_str = ", ".join(sprint_val) if isinstance(sprint_val, list) else str(sprint_val)
        ov_lines.append(f"**Sprint:** {sprint_str}  ")
    ov_lines += [
        f"**Updated:** {meta.get('updated', '—')}  ",
        f"**Jira:** [{meta['key']}]({meta.get('url', '')})",
        "",
    ]
    if meta.get("labels"):
        ov_lines += [f"**Labels:** {', '.join(meta['labels'])}", ""]

    if meta.get("links"):
        ov_lines.append("## Links")
        for lnk in meta["links"]:
            ov_lines.append(f"- [{lnk['type']}] [{lnk['key']}]({url}/browse/{lnk['key']}): {lnk.get('summary', '')}")
        ov_lines.append("")

    if overview_text:
        teaser = overview_text.strip()[:300].replace("\n", " ")
        ov_lines += [
            "## Context",
            f"> {teaser}{'…' if len(overview_text.strip()) > 300 else ''}",
            "",
            "_Full context: [jira/overview.md](jira/overview.md)_",
            "",
        ]

    if criteria:
        ov_lines += ["## Acceptance Criteria"]
        for c in criteria:
            ov_lines.append(f"- [ ] {c}")
        ov_lines.append("")

    if technical_text:
        ov_lines += ["## Technical Notes", "_See [jira/technical.md](jira/technical.md)_", ""]

    if children:
        ov_lines += ["## Child Tickets"]
        for c in children:
            ov_lines.append(f"- [{c['key']}](./{c['key']}/README.md): {c['summary']} _{c.get('status', '')}_")
        ov_lines.append("")

    ov_lines += [
        "## Files",
        "| File | Contents |",
        "|---|---|",
        "| [jira/ticket.yaml](jira/ticket.yaml) | Full metadata, links, children |",
    ]
    if overview_text:
        ov_lines.append("| [jira/overview.md](jira/overview.md) | Context / why this ticket exists |")
    if criteria:
        ov_lines.append("| [jira/ac.yaml](jira/ac.yaml) | Acceptance criteria |")
    if technical_text:
        ov_lines.append("| [jira/technical.md](jira/technical.md) | Implementation / design notes |")
    if description_text:
        ov_lines.append("| [jira/description.md](jira/description.md) | Verbatim Jira description |")
    if isinstance(comments, list) and comments:
        ov_lines.append(f"| [jira/comments/](jira/comments/) | {len(comments)} comment(s) |")

    with open(os.path.join(ticket_dir, "ticket-overview.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(ov_lines))

    # ── 11. README.md — only written if absent ────────────────────────────────
    readme_path = os.path.join(ticket_dir, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ov_lines))

    # ── 12. Recurse into children ─────────────────────────────────────────────
    fetched_children = []
    if depth > 1 and children:
        for child in children:
            child_result = fetch_ticket(child["key"], ticket_dir, depth=depth - 1, _visited=_visited)
            fetched_children.append(child_result)

    summary = {
        "fetched": key,
        "path": ticket_dir,
        "children_count": len(children),
        "comments_count": len(comments) if isinstance(comments, list) else 0,
        "ac_count": len(criteria),
        "has_technical": bool(technical_text),
        "files_written": {
            "ticket-overview.md": True,
            "ticket.yaml": True,
            "overview.md": bool(overview_text),
            "ac.yaml": bool(criteria),
            "technical.md": bool(technical_text),
            "description.md": bool(description_text),
            "comments/": isinstance(comments, list) and bool(comments),
        },
    }
    if fetched_children:
        summary["children_fetched"] = fetched_children

    return summary


if len(sys.argv) < 2:
    print(json.dumps({"error": "No command specified"}))
    sys.exit(1)

command = sys.argv[1]
result = None

try:
    if command == "list":
        jql_parts = ["assignee = currentUser()"]
        max_results = 20
        full = False
        
        if "--status" in sys.argv:
            idx = sys.argv.index("--status")
            if idx + 1 < len(sys.argv):
                status = sys.argv[idx + 1]
                jql_parts.append(f'status = "{status}"')
        else:
            jql_parts.append("status NOT IN (Done, \"Won't Do\")")
        
        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            if idx + 1 < len(sys.argv):
                project = sys.argv[idx + 1]
                jql_parts.append(f"project = {project}")
        
        if "--max" in sys.argv:
            idx = sys.argv.index("--max")
            if idx + 1 < len(sys.argv):
                try:
                    max_results = int(sys.argv[idx + 1])
                except:
                    pass
        
        if "--full" in sys.argv:
            full = True
        
        jql = " AND ".join(jql_parts)
        result = list_issues(jql, max_results, full=full)
    
    elif command == "get":
        if len(sys.argv) < 3:
            result = {"error": "get requires issue key"}
        else:
            key = sys.argv[2]
            full = "--full" in sys.argv
            result = get_issue(key, full=full)
    
    elif command == "subtasks":
        if len(sys.argv) < 3:
            result = {"error": "subtasks requires issue key"}
        else:
            key = sys.argv[2]
            result = get_subtasks(key)
    
    elif command == "epic":
        if len(sys.argv) < 3:
            result = {"error": "epic requires issue key"}
        else:
            key = sys.argv[2]
            result = get_epic(key)

    elif command == "comments":
        if len(sys.argv) < 3:
            result = {"error": "comments requires issue key"}
        else:
            key = sys.argv[2]
            result = get_comments(key)

    elif command == "description":
        if len(sys.argv) < 3:
            result = {"error": "description requires issue key"}
        else:
            key = sys.argv[2]
            result = get_raw_description(key)

    elif command == "metadata":
        if len(sys.argv) < 3:
            result = {"error": "metadata requires issue key"}
        else:
            key = sys.argv[2]
            result = get_all_metadata(key)

    elif command == "attachments":
        if len(sys.argv) < 3:
            result = {"error": "attachments requires issue key"}
        else:
            key = sys.argv[2]
            result = get_attachments(key)

    elif command == "download-attachment":
        if len(sys.argv) < 4:
            result = {"error": "download-attachment requires attachment_url and filename"}
        else:
            attachment_url = sys.argv[2]
            filename = sys.argv[3]
            output_dir = "."
            if "--output-dir" in sys.argv:
                idx = sys.argv.index("--output-dir")
                if idx + 1 < len(sys.argv):
                    output_dir = sys.argv[idx + 1]
            result = download_attachment(attachment_url, filename, output_dir)

    elif command == "search":
        if len(sys.argv) < 3:
            result = {"error": "search requires JQL"}
        else:
            jql = sys.argv[2]
            max_results = 20
            full = False
            
            if "--max" in sys.argv:
                idx = sys.argv.index("--max")
                if idx + 1 < len(sys.argv):
                    try:
                        max_results = int(sys.argv[idx + 1])
                    except:
                        pass
            
            if "--full" in sys.argv:
                full = True
            
            result = search(jql, max_results, full=full)
    
    elif command == "create":
        # Parse create parameters
        if "--summary" not in sys.argv or "--type" not in sys.argv or "--project" not in sys.argv:
            result = {"error": "create requires --summary, --type, and --project"}
        else:
            summary = sys.argv[sys.argv.index("--summary") + 1]
            issue_type = sys.argv[sys.argv.index("--type") + 1]
            project = sys.argv[sys.argv.index("--project") + 1]

            description = None
            if "--description" in sys.argv:
                idx = sys.argv.index("--description")
                if idx + 1 < len(sys.argv):
                    description = sys.argv[idx + 1]

            assignee = None
            if "--assignee" in sys.argv:
                idx = sys.argv.index("--assignee")
                if idx + 1 < len(sys.argv):
                    assignee = sys.argv[idx + 1]

            labels = None
            if "--labels" in sys.argv:
                idx = sys.argv.index("--labels")
                if idx + 1 < len(sys.argv):
                    labels = sys.argv[idx + 1].split(",")

            result = create_issue(summary, issue_type, project, description, assignee, labels)

    elif command == "transition":
        if len(sys.argv) < 4:
            result = {"error": "transition requires issue key and status name"}
        else:
            key = sys.argv[2]
            status = sys.argv[3]
            result = transition_issue(key, status)

    elif command == "transitions":
        if len(sys.argv) < 3:
            result = {"error": "transitions requires issue key"}
        else:
            key = sys.argv[2]
            result = list_transitions(key)

    elif command == "update":
        if len(sys.argv) < 3:
            result = {"error": "update requires issue key"}
        else:
            key = sys.argv[2]
            description = None
            summary = None

            if "--description" in sys.argv:
                idx = sys.argv.index("--description")
                if idx + 1 < len(sys.argv):
                    description = sys.argv[idx + 1]

            if "--summary" in sys.argv:
                idx = sys.argv.index("--summary")
                if idx + 1 < len(sys.argv):
                    summary = sys.argv[idx + 1]

            result = update_issue(key, description=description, summary=summary)

    elif command == "add-comment":
        if len(sys.argv) < 4:
            result = {"error": "add-comment requires issue key and --comment"}
        else:
            key = sys.argv[2]
            comment_body = None

            if "--comment" in sys.argv:
                idx = sys.argv.index("--comment")
                if idx + 1 < len(sys.argv):
                    # Join all remaining args as the comment body
                    comment_body = " ".join(sys.argv[idx + 1:])

            if not comment_body:
                result = {"error": "add-comment requires --comment parameter"}
            else:
                result = add_comment(key, comment_body)

    elif command == "delete-comment":
        if len(sys.argv) < 4:
            result = {"error": "delete-comment requires issue key and --comment-id"}
        else:
            key = sys.argv[2]
            comment_id = None

            if "--comment-id" in sys.argv:
                idx = sys.argv.index("--comment-id")
                if idx + 1 < len(sys.argv):
                    comment_id = sys.argv[idx + 1]

            if not comment_id:
                result = {"error": "delete-comment requires --comment-id parameter"}
            else:
                try:
                    issue = jira.issue(key)
                    comment = jira.comment(key, comment_id)
                    comment.delete()
                    result = {"success": True, "key": key, "deleted_comment_id": comment_id}
                except Exception as e:
                    result = {"error": str(e)}

    elif command == "fetch":
        if len(sys.argv) < 3:
            result = {"error": "fetch requires issue key"}
        else:
            key = sys.argv[2]
            output_dir = "."
            depth = 1

            if "--output-dir" in sys.argv:
                idx = sys.argv.index("--output-dir")
                if idx + 1 < len(sys.argv):
                    output_dir = sys.argv[idx + 1]

            if "--depth" in sys.argv:
                idx = sys.argv.index("--depth")
                if idx + 1 < len(sys.argv):
                    try:
                        depth = int(sys.argv[idx + 1])
                    except ValueError:
                        pass

            result = fetch_ticket(key, output_dir, depth=depth)

    else:
        result = {"error": f"Unknown command: {command}"}
    
    print(json.dumps(result, indent=2))

except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
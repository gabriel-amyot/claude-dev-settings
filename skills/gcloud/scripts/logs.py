#!/usr/bin/env python3
"""GCP Cloud Logging fetcher with summary generation. Multi-org aware."""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUTPUT_DIR = "/tmp/gcloud-logs"
MAX_FILE_SIZE_MB = 2
STACK_TRACE_LINES = 5
TOP_ERRORS = 5

CONFIG_PATH = Path(__file__).parent.parent / "gcloud_config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"ERROR: Config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def detect_organization(config: dict) -> str:
    """Longest-prefix match on $PWD vs org local_path. Falls back to default_org."""
    cwd = os.getcwd()
    best_match = None
    best_len = 0
    for org_name, org_cfg in config["organizations"].items():
        local_path = org_cfg.get("local_path", "")
        if cwd.startswith(local_path) and len(local_path) > best_len:
            best_match = org_name
            best_len = len(local_path)
    return best_match or config.get("default_org", "supervisrai")


def get_org_context(config: dict, org_name: str) -> dict:
    orgs = config["organizations"]
    if org_name not in orgs:
        available = ", ".join(orgs.keys())
        print(f"ERROR: Unknown org '{org_name}'. Available: {available}", file=sys.stderr)
        sys.exit(1)
    ctx = orgs[org_name].copy()
    ctx["name"] = org_name
    return ctx


def display_org_disclaimer(org: dict) -> None:
    print(f"[gcloud] Organization: {org['name']} ({org['gcloud_account']})", file=sys.stderr)


def resolve_project(name: str, aliases: dict) -> tuple[str, str | None]:
    """Returns (project_id, alias_or_none)."""
    if name in aliases:
        return aliases[name], name
    return name, None


def build_filter(hours: float, severity: str, text_filter: str | None, resource_type: str | None) -> str:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    parts = [f'timestamp >= "{start.strftime("%Y-%m-%dT%H:%M:%SZ")}"']
    parts.append(f'severity >= {severity}')
    if text_filter:
        parts.append(f'textPayload:"{text_filter}" OR jsonPayload.message:"{text_filter}"')
    if resource_type:
        parts.append(f'resource.type = "{resource_type}"')
    return "\n".join(parts)


def fetch_logs(project_id: str, log_filter: str, limit: int, account: str | None = None) -> list[dict]:
    cmd = [
        "gcloud", "logging", "read", log_filter,
        f"--project={project_id}",
        f"--limit={limit}",
        "--format=json",
    ]
    if account:
        cmd.append(f"--account={account}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"ERROR: gcloud logging read failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    if not result.stdout.strip():
        return []
    return json.loads(result.stdout)


def extract_message(entry: dict) -> str:
    if "textPayload" in entry:
        return entry["textPayload"].strip().split("\n")[0][:200]
    jp = entry.get("jsonPayload", {})
    if "message" in jp:
        return jp["message"].strip().split("\n")[0][:200]
    if "stack_trace" in jp:
        return jp["stack_trace"].strip().split("\n")[0][:200]
    pp = entry.get("protoPayload", {})
    if pp:
        method = pp.get("methodName", "")
        status = pp.get("status", {})
        status_msg = status.get("message", "")
        if status_msg:
            return f"{method}: {status_msg}"[:200]
        details = status.get("details", [])
        for d in details:
            if "reason" in d:
                return f"{method}: {d['reason']}"[:200]
        if method:
            return method[:200]
    return entry.get("severity", "UNKNOWN")


def extract_stack_trace(entry: dict, max_lines: int = STACK_TRACE_LINES) -> str | None:
    jp = entry.get("jsonPayload", {})
    for field in ("stack_trace", "exception", "message"):
        val = jp.get(field, "")
        if isinstance(val, str) and "\n" in val:
            lines = val.strip().split("\n")
            return "\n".join(lines[:max_lines])
    tp = entry.get("textPayload", "")
    if isinstance(tp, str) and "\n" in tp:
        lines = tp.strip().split("\n")
        if len(lines) > 1:
            return "\n".join(lines[:max_lines])
    return None


def extract_resource(entry: dict) -> str:
    labels = entry.get("resource", {}).get("labels", {})
    name = labels.get("service_name", labels.get("function_name", labels.get("configuration_name", "")))
    if name:
        return name
    pp = entry.get("protoPayload", {})
    if pp:
        return pp.get("serviceName", "unknown")
    return "unknown"


def generate_summary(entries: list[dict], project_id: str, alias: str | None,
                     hours: float, severity: str, raw_path: str) -> str:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    severity_counts: Counter = Counter()
    error_groups: dict[str, dict] = {}

    for entry in entries:
        sev = entry.get("severity", "DEFAULT")
        severity_counts[sev] += 1
        msg = extract_message(entry)
        if msg not in error_groups:
            error_groups[msg] = {
                "count": 0,
                "first_seen": entry.get("timestamp", ""),
                "resource": extract_resource(entry),
                "stack_trace_head": extract_stack_trace(entry),
            }
        error_groups[msg]["count"] += 1

    top = sorted(error_groups.items(), key=lambda x: x[1]["count"], reverse=True)[:TOP_ERRORS]

    file_size = os.path.getsize(raw_path) if os.path.exists(raw_path) else 0
    truncated = file_size > MAX_FILE_SIZE_MB * 1024 * 1024

    lines = ["# GCP Logs Summary"]
    lines.append(f"project: {project_id}")
    if alias:
        lines.append(f"alias: {alias}")
    lines.append(f'time_range: "{start.strftime("%Y-%m-%dT%H:%M:%SZ")} to {now.strftime("%Y-%m-%dT%H:%M:%SZ")}"')
    lines.append(f'severity_filter: "{severity}"')
    lines.append(f"total_entries: {len(entries)}")

    lines.append("severity_breakdown:")
    for sev in sorted(severity_counts.keys()):
        lines.append(f"  {sev}: {severity_counts[sev]}")

    lines.append("top_errors:")
    for msg, info in top:
        lines.append(f"  - count: {info['count']}")
        lines.append(f'    message: "{msg}"')
        lines.append(f'    first_seen: "{info["first_seen"]}"')
        lines.append(f'    resource: "{info["resource"]}"')
        if info["stack_trace_head"]:
            lines.append("    stack_trace_head: |")
            for st_line in info["stack_trace_head"].split("\n"):
                lines.append(f"      {st_line}")

    lines.append(f"truncated: {str(truncated).lower()}")
    if truncated:
        lines.append(f"warning: \"Raw log file exceeds {MAX_FILE_SIZE_MB}MB. Results may be incomplete.\"")
    lines.append(f'full_log: "{raw_path}"')
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Fetch GCP Cloud Logging entries with summary")
    parser.add_argument("project", help="Project alias (e.g. dev-core, dev-frontend) or full project ID")
    parser.add_argument("--org", help="Organization override (supervisrai|klever). Auto-detected from $PWD if omitted.")
    parser.add_argument("--hours", type=float, default=1.0, help="Time window in hours (default: 1)")
    parser.add_argument("--severity", default="ERROR", help="Minimum severity (default: ERROR)")
    parser.add_argument("--filter", dest="text_filter", help="Text filter for log messages")
    parser.add_argument("--resource-type", help="GCP resource type (e.g. cloud_run_revision)")
    parser.add_argument("--limit", type=int, default=500, help="Max log entries (default: 500)")
    args = parser.parse_args()

    config = load_config()
    org_name = args.org or detect_organization(config)
    org = get_org_context(config, org_name)
    display_org_disclaimer(org)

    project_id, alias = resolve_project(args.project, org["project_aliases"])
    if alias is None and args.project not in org["project_aliases"].values():
        # Check if the alias exists in another org — helpful error
        for other_name, other_cfg in config["organizations"].items():
            if other_name != org_name and args.project in other_cfg["project_aliases"]:
                print(
                    f"ERROR: Alias '{args.project}' belongs to org '{other_name}', not '{org_name}'. "
                    f"Use --org {other_name}.",
                    file=sys.stderr,
                )
                sys.exit(1)

    display_name = alias or args.project

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    raw_path = os.path.join(OUTPUT_DIR, f"{display_name}_{timestamp}.json")
    summary_path = os.path.join(OUTPUT_DIR, f"{display_name}_{timestamp}_summary.yaml")

    log_filter = build_filter(args.hours, args.severity, args.text_filter, args.resource_type)
    print(f"Fetching logs from {project_id} (last {args.hours}h, severity >= {args.severity})...")

    entries = fetch_logs(project_id, log_filter, args.limit, org["gcloud_account"])

    with open(raw_path, "w") as f:
        json.dump(entries, f, indent=2)
    print(f"Raw logs: {raw_path} ({len(entries)} entries)")

    summary = generate_summary(entries, project_id, alias, args.hours, args.severity, raw_path)
    with open(summary_path, "w") as f:
        f.write(summary)
    print(f"Summary:  {summary_path}")


if __name__ == "__main__":
    main()

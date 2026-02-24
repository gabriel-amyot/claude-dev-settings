#!/usr/bin/env python3
"""Parse a downloaded GitLab CI trace log and extract a structured YAML summary."""
import os
import re
import sys
import yaml
from datetime import datetime


# Known error patterns — extend this as new failure modes are discovered
ERROR_PATTERNS = {
    "state_lock": {
        "regex": r"Error[:\s]+Error acquiring the state lock",
        "extract": [
            (r"Lock Info:\s*\n\s*ID:\s*(\S+)", "lock_id"),
            (r"Path:\s*(gs://\S+)", "lock_path"),
        ],
    },
    "manual_deploy_required": {
        "regex": r"\[\s*ERROR\s*\]\s*Run manual deploy",
    },
    "precondition_412": {
        "regex": r"Error 412[:\s].*pre-conditions",
    },
    "stuck_or_timeout": {
        "regex": r"stuck_or_timeout_failure",
    },
}

# CI variables to extract from the ENV section
ENV_KEYS = [
    "TF_VAR_image_tag",
    "CI_COMMIT_REF_NAME",
    "CI_PIPELINE_ID",
    "CI_PROJECT_PATH",
    "CI_ENVIRONMENT_NAME",
    "CI_JOB_NAME",
    "CI_JOB_STATUS",
    "CI_JOB_ID",
    "CI_JOB_STARTED_AT",
]


def parse_sections(text):
    """Split trace into named sections using GitLab CI section markers."""
    sections = {}
    # GitLab uses: section_start:TIMESTAMP:SECTION_NAME\r\033[0K
    # and: section_end:TIMESTAMP:SECTION_NAME\r\033[0K
    pattern = re.compile(
        r"section_start:\d+:([^\r\n]+?)(?:\r|\n)"
    )
    ends = re.compile(
        r"section_end:\d+:([^\r\n]+?)(?:\r|\n)"
    )

    # Find all section boundaries
    starts = [(m.start(), m.end(), m.group(1).strip()) for m in pattern.finditer(text)]

    for i, (s_start, s_end, name) in enumerate(starts):
        # Find matching end
        end_match = ends.search(text, s_end)
        if end_match:
            content = text[s_end:end_match.start()]
        elif i + 1 < len(starts):
            content = text[s_end:starts[i + 1][0]]
        else:
            content = text[s_end:]

        sections[name] = content

    # Fallback: if no sections found, treat whole text as one section
    if not sections:
        sections["full_log"] = text

    return sections


def extract_env_vars(section_text):
    """Extract key CI/CD variables from ENV section."""
    result = {}
    for key in ENV_KEYS:
        m = re.search(rf'{key}\s*[=:]\s*["\']?([^\s"\']+)', section_text)
        if m:
            result[key] = m.group(1)
    return result


def extract_plan_stats(section_text):
    """Extract terraform plan summary line."""
    m = re.search(r"Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy", section_text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None, None, None


def extract_resources_by_action(section_text):
    """Extract resource lists grouped by terraform action type."""
    groups = {}
    current_action = None
    for line in section_text.split("\n"):
        line = line.strip()
        # Look for action headers like "Create:", "UpdateInPlace:", "Destroy:", "FilteredDestroy:"
        action_match = re.match(r"^(Create|UpdateInPlace|Destroy|DestroyFilterOut|FilteredDestroy)\s*:", line)
        if action_match:
            current_action = action_match.group(1)
            groups[current_action] = []
            continue
        # Also detect lines like "  # module.xxx will be created"
        resource_match = re.match(r"^\s*#\s*([\w\.\[\]\"_-]+)\s+will be\s+(\w+)", line)
        if resource_match:
            resource = resource_match.group(1)
            action = resource_match.group(2)
            action_key = {"created": "Create", "updated": "UpdateInPlace", "destroyed": "Destroy"}.get(action, action)
            groups.setdefault(action_key, []).append(resource)
            continue
        # Collect resources under current action header
        if current_action and line and not line.startswith("#") and not line.startswith("="):
            # Resource lines often start with "- " or are just the resource address
            cleaned = line.lstrip("- ").strip()
            if cleaned and not cleaned.startswith("(") and len(cleaned) > 5:
                groups.setdefault(current_action, []).append(cleaned)

    return groups


def extract_summary_counts(section_text):
    """Extract summary counts from the summary section."""
    counts = {}
    for key in ("Create", "UpdateInPlace", "Destroy", "DestroyFilterOut"):
        m = re.search(rf"{key}\s*[=:]\s*(\d+)", section_text)
        if m:
            counts[key] = int(m.group(1))
    return counts


def detect_auto_deploy(sections):
    """Detect auto-deploy gate status."""
    for name, content in sections.items():
        if "auto-deploy" in name.lower() or "auto_deploy" in name.lower():
            if re.search(r"\[\s*ERROR\s*\]", content):
                reason = "Destroy count > 0"
                m = re.search(r"\[\s*ERROR\s*\]\s*(.+)", content)
                if m:
                    reason = m.group(1).strip()
                return "blocked", reason
            return "allowed", None
    return "n/a", None


def detect_errors(full_text):
    """Scan full trace for known error patterns."""
    errors = []
    for err_type, config in ERROR_PATTERNS.items():
        m = re.search(config["regex"], full_text)
        if m:
            error = {"type": err_type, "message": m.group(0).strip()}
            for extract_re, field_name in config.get("extract", []):
                em = re.search(extract_re, full_text)
                if em:
                    error[field_name] = em.group(1)
            errors.append(error)
    return errors


def summarize(log_path):
    """Generate structured summary from a trace log file."""
    with open(log_path, "r") as f:
        text = f.read()

    sections = parse_sections(text)

    # Extract env vars from any section containing ENV-like content
    env_vars = {}
    for name, content in sections.items():
        if "env" in name.lower() or "before" in name.lower() or "full_log" in name:
            found = extract_env_vars(content)
            env_vars.update(found)

    # Extract plan stats from terraform-plan section
    plan_add, plan_change, plan_destroy = None, None, None
    plan_status = "skipped"
    for name, content in sections.items():
        if "plan" in name.lower() and "terraform" in name.lower():
            add, change, destroy = extract_plan_stats(content)
            if add is not None:
                plan_add, plan_change, plan_destroy = add, change, destroy
                plan_status = "success"
            if re.search(r"Error:", content):
                plan_status = "failed"

    # Extract resources from terraform-change section
    resources = {}
    for name, content in sections.items():
        if "change" in name.lower() and "terraform" in name.lower():
            resources = extract_resources_by_action(content)
        elif "plan" in name.lower() and "terraform" in name.lower() and not resources:
            resources = extract_resources_by_action(content)

    # Summary counts
    summary_counts = {}
    for name, content in sections.items():
        if name.lower() == "summary" or "summary" in name.lower():
            summary_counts = extract_summary_counts(content)

    # Auto-deploy gate
    auto_deploy, auto_deploy_reason = detect_auto_deploy(sections)

    # Errors
    errors = detect_errors(text)

    # Determine job status
    job_status = env_vars.get("CI_JOB_STATUS", "unknown")
    if errors:
        job_status = "failed"
    elif job_status == "unknown" and plan_status == "success":
        job_status = "success"

    # Build summary
    summary = {
        "job_id": env_vars.get("CI_JOB_ID", os.path.basename(log_path).split("_")[-1].replace(".log", "")),
        "job_name": env_vars.get("CI_JOB_NAME", "unknown"),
        "job_status": job_status,
        "pipeline_id": env_vars.get("CI_PIPELINE_ID", "unknown"),
        "environment": env_vars.get("CI_ENVIRONMENT_NAME", "unknown"),
        "ref": env_vars.get("CI_COMMIT_REF_NAME", "unknown"),
        "project": env_vars.get("CI_PROJECT_PATH", "unknown"),
        "image_tag": env_vars.get("TF_VAR_image_tag", "unknown"),
        "timestamp": env_vars.get("CI_JOB_STARTED_AT", datetime.now().isoformat()),
    }

    # Terraform plan
    if plan_add is not None:
        summary["plan_status"] = plan_status
        summary["plan_add"] = plan_add
        summary["plan_change"] = plan_change
        summary["plan_destroy"] = plan_destroy

    # Use summary counts if available, fall back to plan stats
    if summary_counts:
        summary["summary_counts"] = summary_counts

    # Resources by action
    if resources:
        for action, res_list in resources.items():
            key = f"resources_{action.lower()}"
            summary[key] = res_list

    # Auto-deploy gate
    summary["auto_deploy"] = auto_deploy
    if auto_deploy_reason:
        summary["auto_deploy_reason"] = auto_deploy_reason

    # Errors
    summary["errors"] = errors if errors else []

    # Warnings
    warnings = []
    if plan_destroy and plan_destroy > 0:
        warnings.append("Destroy operations detected — review carefully")
    summary["warnings"] = warnings

    # Full log reference
    summary["full_log"] = log_path

    return summary


def main():
    if len(sys.argv) < 2:
        print("Usage: pipeline_trace_summarize.py <log-file-path>", file=sys.stderr)
        sys.exit(1)

    log_path = sys.argv[1]
    if not os.path.exists(log_path):
        print(f"Error: File not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    summary = summarize(log_path)

    # Write summary YAML next to the log file
    base = log_path.replace(".log", "")
    summary_path = f"{base}_summary.yaml"
    with open(summary_path, "w") as f:
        f.write("# Pipeline Job Summary\n")
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(summary_path)


if __name__ == "__main__":
    main()

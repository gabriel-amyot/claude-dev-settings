#!/usr/bin/env python3
"""Shared terraform trace parsing utilities.

Used by both deploy_watch (in gitlab_skill.py) and pipeline_trace_summarize.py
to avoid duplicating the same regex patterns.
"""
import re

# Terraform plan summary regex
PLAN_REGEX = re.compile(
    r"Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy"
)

# Error line detection
ERROR_LINE_REGEX = re.compile(r"\[\s*ERROR\s*\]|Error:|error:")

# ANSI escape code stripping
ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*m')


def strip_ansi(text):
    """Remove ANSI escape codes from CI log output."""
    return ANSI_REGEX.sub('', text)


def extract_plan_stats(text):
    """Extract terraform plan add/change/destroy counts from log text.

    Returns (add, change, destroy) or (None, None, None) if no plan line found.
    """
    m = PLAN_REGEX.search(text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None, None, None


def extract_plan_dict(job_name, text):
    """Extract plan stats as a dict for a named job. Returns dict or None."""
    add, change, destroy = extract_plan_stats(text)
    if add is not None:
        return {
            "job": job_name,
            "plan_add": add,
            "plan_change": change,
            "plan_destroy": destroy,
        }
    return None


def extract_error_lines(text, max_lines=10):
    """Extract lines matching error patterns from log text."""
    return [
        line.strip() for line in text.split("\n")
        if ERROR_LINE_REGEX.search(line)
    ][:max_lines]

#!/usr/bin/env python3
"""Template engine for /post-comment. No external deps."""

import argparse
import re
import sys
import yaml
from pathlib import Path


def parse_draft(path: str) -> dict:
    """Read draft file with optional YAML frontmatter + body."""
    text = Path(path).read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            meta["body"] = parts[2].strip()
            return meta
    return {"body": text.strip()}


def render_template(template_path: str, variables: dict) -> str:
    """Substitute {{var}} placeholders and {{#var}}...{{/var}} conditionals."""
    content = Path(template_path).read_text()

    # 1. Process conditional sections first
    def replace_conditional(match):
        key = match.group(1)
        inner = match.group(2)
        if variables.get(key):
            return inner
        return ""
    content = re.sub(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", replace_conditional, content, flags=re.DOTALL)

    # 2. Warn on missing vars, substitute with blank
    missing = []
    for match in re.finditer(r"\{\{(\w+)\}\}", content):
        key = match.group(1)
        if key not in variables:
            missing.append(key)
    if missing:
        print(f"WARNING: Unused placeholders (left blank): {', '.join(missing)}", file=sys.stderr)
    result = re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables.get(m.group(1), "")), content)

    # 3. Clean up blank lines from removed sections
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def format_for_platform(content: str, platform: str) -> str:
    """Convert markdown to Jira wiki markup. Other platforms stay as-is."""
    if platform != "jira":
        return content
    text = content

    # Preserve Jira user mentions before any conversion
    mentions = {}
    def save_mention(match):
        key = f"__MENTION_{len(mentions)}__"
        mentions[key] = match.group(0)
        return key
    text = re.sub(r"\[~accountid:[^\]]+\]", save_mention, text)

    text = re.sub(r"^### (.+)$", r"h3. \1", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"h2. \1", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"h1. \1", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"_\1_", text)
    text = re.sub(r"```(\w*)\n(.*?)```", r"{code:\1}\n\2{code}", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"{{\1}}", text)

    # Restore Jira user mentions
    for key, val in mentions.items():
        text = text.replace(key, val)

    return text


def build_attribution(platform: str, model: str = "", session: str = "") -> str:
    """Build attribution line. Jira gets a header, others get a footer."""
    parts = ["Posted via Claude Code"]
    if model:
        parts.append(f"model: {model}")
    if session:
        parts.append(f"session: {session}")
    tag = " | ".join(parts)
    if platform == "jira":
        return f"[automated] {tag}\n\n"
    return f"\n\n_{tag}_"


def main():
    parser = argparse.ArgumentParser(description="Render a post-comment template")
    parser.add_argument("--template", required=True, help="Path to template file")
    parser.add_argument("--draft", required=True, help="Path to draft file (YAML frontmatter + body)")
    parser.add_argument("--platform", required=True, choices=["github", "gitlab", "jira", "slack"])
    parser.add_argument("--model", default="", help="Model name for attribution")
    parser.add_argument("--session", default="", help="Session ID for attribution")
    args = parser.parse_args()

    variables = parse_draft(args.draft)
    rendered = render_template(args.template, variables)
    attribution = build_attribution(args.platform, args.model, args.session)
    formatted = format_for_platform(rendered, args.platform)

    if args.platform == "jira":
        output = attribution + formatted
    else:
        output = formatted + attribution

    print(output)


if __name__ == "__main__":
    main()

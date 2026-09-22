# Skill Proposal: skill-dry-audit
Date: 2026-05-20
Source: GitLab skill hardening session

## Trigger
When improving an existing skill, or when a skill has multiple Python scripts that share logic (auth, config, parsing). "audit skill for duplication", "DRY up this skill", "skill health check".

## Scope
global

## Draft Steps
1. Scan skill directory for all `.py` files
2. Compare functions across files (signature + body similarity)
3. Identify duplicated logic (auth patterns, config loading, regex patterns, formatters)
4. Propose a `{skill}_utils.py` shared module with the deduplicated functions
5. Show import rewiring plan for each consuming file

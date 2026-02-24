# agent-os:audit-docs - Documentation Guardian Agent

## Quick Start

```bash
# Check documentation health (read-only)
/agent-os:audit-docs

# Check and auto-repair stale indexes
/agent-os:audit-docs --auto-repair

# Verbose mode
/agent-os:audit-docs --auto-repair --verbose
```

## What It Does

Comprehensive documentation integrity guardian that:
- ✓ Validates index currency (specs, architecture, standards)
- ✓ Validates `.repo-links.yaml` integrity
- ✓ Checks cross-references (CLAUDE.md, README.md, ADRs vs code)
- ✓ Enforces documentation standards (CommonMark, no time estimates)
- ✓ Validates reports folder structure
- ✓ Auto-repairs stale indexes (conservative mode)
- ✓ Generates health report in `.claude/audit-reports/`

## Blocking Behavior (CI/CD)

**CRITICAL (blocks merge):**
- Stale indexes
- Broken `.repo-links.yaml` paths
- Time estimates in documentation
- Stale ADR decisions contradicting implementation

**WARNING (doesn't block):**
- CommonMark formatting issues
- Reports folder naming violations
- Passive voice in documentation

**INFO (informational only):**
- Documentation improvement suggestions

## Files

- `skill.md` - Skill definition and implementation guide
- `README.md` - This file

## Output

Reports written to: `.claude/audit-reports/audit_{YYYY-MM-DD-HHMMSS}.md` (gitignored)

## Dependencies

Orchestrates existing skills:
- `/agent-os:index-specs`
- `/agent-os:index-architecture`
- `/agent-os:index-standards`
- `/validate-repo-links`

## Success Criteria

An agentic LLM can enter the repo and instantly understand:
- What the service does (mission, boundaries)
- Where to find information (optimized indexes)
- How to navigate related services (repo links)
- Current architectural decisions (ADRs)
- Coding standards (progressive disclosure)

**All without expensive token searches or human questions.**

## References

See `skill.md` for complete implementation details.

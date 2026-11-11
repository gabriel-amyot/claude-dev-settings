# Self-containment check (factory-style skills)

Use this on request ("is this skill self-contained", "audit the factory skills"), or after a factory-style skill was built or refactored. A factory-style skill carries a spec, a version, and usually a run ledger.

## Run

```bash
python3 ~/.claude-shared-config/skills/harness-audit/scripts/self_containment_check.py <skill-dir> [<skill-dir> ...] [--spec-glob GLOB] [--run-producing]
```

The script is read-only. It prints JSON per skill and exits 1 when any skill has a FAIL.

| Check | PASS when |
|---|---|
| `version_coupling` | SKILL.md `version:` equals the top `## X.Y.Z` entry in CHANGELOG.md |
| `carried_spec` | A spec file is inside the skill (default `docs/spec/*.md`) |
| `spec_source` | The `spec_source:` pointer resolves inside the skill (absent = WARN) |
| `external_tether` | SKILL.md and the spec do not point at an external second copy |
| `runs_ledger` | `runs/INDEX.md` exists when the skill produces runs |
| `execution_laws` | A `contracts/` folder or a `laws-of-execution.md` file exists |

## Report

Put each FAIL in the audit Findings as MEDIUM (version drift as HIGH, because a self-improvement then has no version link). Do not fix the skill in the audit. A skill can carry its spec somewhere else on purpose: re-run with `--spec-glob` before you report it.

The reference model is `service-factory`: `gates/version_guard.py` enforces the same laws for that one skill as an un-skippable gate. To give another factory the same backstop, propose a port of that gate as a separate task.

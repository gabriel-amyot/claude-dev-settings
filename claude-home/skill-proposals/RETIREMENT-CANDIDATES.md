# Retirement Candidates

Derived from USAGE-SCAN.md. Every skill here had ZERO invocations in the
scan window. This pass adds the second question: does any other skill,
agent, hook, or CLAUDE.md still point at it?

## ORPHAN (16) — zero invocations, zero references

Nothing calls these and nothing points at them. Safest to archive.

- claude-code-cost-optimization
- cloudflare-pages
- diagnose
- improve-codebase-architecture
- klever-proximity-dev-backfill
- klever-repo-rename
- post-crawl-review
- pre-crawl-repo-prep
- prototype
- research-intake
- setup-matt-pocock-skills
- to-issues
- to-prd
- triage
- vendor-question-escalation
- worktree-prune

## REFERENCED (48) — zero invocations, but still wired in

Do NOT archive on the count alone. Zero invocations plus a live reference
means either the caller is also dead, or a documented rule is not being
followed in practice. Both are worth knowing.

- **archive** (15 refs) — ~/.claude/hooks/evals/reports/2026-07-07-pm-guard-and-session-close-guard.md, ~/.claude/agents/bibliotheque-librarian.md, ~/.claude/hooks/evals/fixtures/session-close-operationalize-guard.yaml
- **tdd** (15 refs) — ~/.claude/commands/tdd.md, ~/.claude/skills/dark-factory/runs/run-2026-06-15-KTP-784.yaml, ~/.claude/skills/dark-factory/runs/run-2026-06-15-KTP-784-needs-visual.yaml
- **deploy-identity** (11 refs) — ~/Developer/grp-beklever-com/project-management/CLAUDE.md, ~/.claude/CLAUDE.md, ~/.claude/library/context/harness-architecture-textbook.md
- **skill-evals** (7 refs) — ~/.claude/skills/bibliotheque-librarian/evals/2026-07-07-eval-authoring.md, ~/.claude/hooks/INDEX.md, ~/.claude/skills/jira/evals/2026-07-07-eval-authoring.md
- **status-index** (6 refs) — ~/.claude/agents/supervisr-autopilot.md, ~/.claude/agents/sprint-crawl.md, ~/.claude/agents/autopilot-config.yaml
- **push-adr** (5 refs) — ~/.claude/agents/supervisr-autopilot.md, ~/.claude/library/context/tools-catalog.md, ~/.claude/agents/autopilot-config.yaml
- **batch-skill-pipeline** (4 refs) — ~/.claude/hooks/proposal-backlog-check.sh, ~/.claude/library/context/harness-overrides.yaml, ~/.claude/skills/operationalize-audit/SKILL.md
- **index-context** (4 refs) — ~/.claude/hooks/auto-index.sh, ~/.claude/library/context/harness-overrides.yaml, ~/.claude/library/context/tools-catalog.md
- **morning-primer** (4 refs) — ~/.claude/skills/floor-manager/SKILL.md, ~/.claude/skills/sitrep/SKILL.md, ~/.claude/skills/morning-brief/SKILL.md
- **test-adversarial** (4 refs) — ~/.claude/skills/floor-manager/SKILL.md, ~/.claude/library/context/harness-overrides.yaml, ~/.claude/skills/challenge/SKILL.md
- **um-local-seed** (4 refs) — ~/Developer/grp-beklever-com/project-management/CLAUDE.md, ~/.claude/skills/um-local-grant/SKILL.md, ~/.claude/skills/klever-local-stack/doc/local-stack-orchestrator-design.md
- **validate-repo-links** (4 refs) — ~/.claude/agents/mother-base-housekeeper.md, ~/.claude/skills/agent-os:audit-docs/skill.md, ~/.claude/skills/agent-os:audit-docs/README.md
- **autonomous-ticket-ship** (3 refs) — ~/.claude/skills/floor-manager/SKILL.md, ~/.claude/skills/sprint-factory/SKILL.md, ~/.claude/skills/dark-factory/SKILL.md
- **bibliotheque-refresh** (3 refs) — ~/Developer/grp-beklever-com/project-management/CLAUDE.md, ~/.claude/library/context/tools-catalog.md, ~/.claude/skills/floor-manager/SKILL.md
- **bq-schema-preflight** (3 refs) — ~/.claude/skills/gcloud/SKILL.md, ~/.claude/skills/bq-table-wiring-audit/SKILL.md, ~/.claude/skills/klever-bq-store-lookup/SKILL.md
- **context-audit** (3 refs) — ~/.claude/skills/operationalize-audit/SKILL.md, ~/.claude/skills/harness-audit/SKILL.md, ~/.claude/skills/wiki-lint/SKILL.md
- **klever-bq-store-lookup** (3 refs) — ~/.claude/skills/klever-data-pipeline/SKILL.md, ~/.claude/skills/geocode-bq-locations/SKILL.md, ~/.claude/skills/_archive/klever-proximity-dev-backfill/SKILL.md
- **leo-ac-scaffold** (3 refs) — ~/.claude/skills/brownfield-sbe-audit/SKILL.md, ~/.claude/skills/create-tickets/SKILL.md, ~/.claude/skills/autonomous-ticket-ship/references/when-not-to-use.md
- **morning-brief** (3 refs) — ~/.claude/skills/floor-manager/SKILL.md, ~/.claude/skills/morning-primer/SKILL.md, ~/.claude/skills/meeting-to-action/SKILL.md
- **pre-flight** (3 refs) — ~/.claude/agents/night-crawl.md, ~/.claude/agents/dev-crawl.md, ~/.claude/skills/ralph-loop-preflight/SKILL.md
- **sitrep** (3 refs) — ~/.claude/skills/floor-manager/SKILL.md, ~/.claude/skills/morning-brief/SKILL.md, ~/.claude/skills/morning-primer/SKILL.md
- **epic-reorganization** (2 refs) — ~/.claude/skills/_archive/ticket-cross-linker/SKILL.md, ~/.claude/skills/batch-skill-pipeline/SKILL.md
- **mb-doc-housekeeping** (2 refs) — ~/.claude/agents/mother-base-housekeeper.md, ~/.claude/library/context/harness-overrides.yaml
- **pre-ship-check** (2 refs) — ~/.claude/skills/_archive/post-crawl-review/SKILL.md, ~/.claude/skills/bmad-epic-lifecycle/SKILL.md
- **ralph-loop-blocked-external** (2 refs) — ~/.claude/skills/_archive/ralph-loop-blocked-external/SKILL.md, ~/.claude/skills/_archive/ralph-loop-blocked-external/functional-test-report.md
- **ralph-loop-preflight** (2 refs) — ~/.claude/skills/_archive/ralph-loop-blocked-external/SKILL.md, ~/.claude/skills/pre-flight/SKILL.md
- **scout-probe** (2 refs) — ~/.claude/skills/_archive/scout-probe/SKILL.md, ~/.claude/skills/_archive/scout-probe/functional-test-report.md
- **spillover-scan** (2 refs) — ~/.claude/skills/_archive/ticket-from-rca-pipeline/SKILL.md, ~/.claude/skills/sprint-close/SKILL.md
- **agent-debate-review** (1 refs) — ~/.claude/skills/_archive/agent-debate-review/SKILL.md
- **agent-os:audit-docs** (1 refs) — ~/.claude/skills/bmad-repo-onboarding/SKILL.md
- **batch-api-crawl-wrapper** (1 refs) — ~/.claude/skills/_archive/batch-api-crawl-wrapper/SKILL.md
- **batch-pr-consolidation** (1 refs) — ~/.claude/skills/klever-mr/SKILL.md
- **bmad-debrief** (1 refs) — ~/.claude/skills/meeting-to-action/SKILL.md
- **bmad-epic-lifecycle** (1 refs) — ~/.claude/skills/floor-manager/SKILL.md
- **bmad-repo-onboarding** (1 refs) — ~/.claude/skills/agent-os:audit-docs/skill.md
- **bq-table-wiring-audit** (1 refs) — ~/.claude/skills/bq-schema-preflight/SKILL.md
- **crawl-adversarial-review-cascade** (1 refs) — ~/.claude/skills/bmad-epic-lifecycle/SKILL.md
- **dashboard-enhancement** (1 refs) — ~/.claude/skills/_archive/dashboard-enhancement/SKILL.md
- **data-source-cross-examination** (1 refs) — ~/.claude/skills/_archive/data-source-cross-examination/SKILL.md
- **inbox-writer** (1 refs) — ~/.claude/skills/skill-evals/SKILL.md
- **klever-demo-seed** (1 refs) — ~/.claude/skills/_archive/klever-demo-seed/docs/scale/v2-guided-onboarding.md
- **slack-pr-listener** (1 refs) — ~/.claude/skills/_archive/slack-pr-listener/SKILL.md
- **sprint-screenshot-capture** (1 refs) — ~/.claude/skills/_archive/sprint-screenshot-capture/SKILL.md
- **ticket-cross-linker** (1 refs) — ~/.claude/skills/_archive/ticket-cross-linker/SKILL.md
- **ticket-from-rca-pipeline** (1 refs) — ~/.claude/skills/_archive/ticket-from-rca-pipeline/SKILL.md
- **ticket-inventory-refresh** (1 refs) — ~/.claude/skills/_archive/ticket-inventory-refresh/SKILL.md
- **tribal-knowledge** (1 refs) — ~/.claude/skills/_archive/tribal-knowledge/SKILL.md
- **vendor-api-ingest** (1 refs) — ~/.claude/skills/api-spike/SKILL.md

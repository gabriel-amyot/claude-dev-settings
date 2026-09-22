# Skill Usage Scan

Window: last 90 days. Transcripts scanned: 3025.
Installed skills with a SKILL.md: 89.

Counts combine Skill-tool calls and slash-command invocations. A zero means
the skill was never reached in the window by either path. Treat zero as a
retirement CANDIDATE, not a verdict: a skill can be new, seasonal, or invoked
only by another skill's internals.

Excluded as cron-invoked (0): none.
A launchd/cron job runs outside any session and writes no transcript, so
counting those as unused is a false negative.

Excluded as too new (19): bibliotheque-librarian, cloudflare-pages, dark-factory, gab-operationalize, ghostty-recover-sessions, gitlab, java-quality, jira, klever-dev-portal, klever-mr, klever-test, notion, post-comment, service-factory, skill-evals, transcript-knowledge-miner, um-local-grant, wiki-lint, writing-claude-code-hooks.
Modified within 30 days, so the 90-day window cannot judge them.

## Never invoked (35) — retirement candidates

- agent-os:audit-docs
- archive
- autonomous-ticket-ship
- batch-pr-consolidation
- batch-skill-pipeline
- bibliotheque-refresh
- bmad-debrief
- bmad-epic-lifecycle
- bmad-repo-onboarding
- bq-schema-preflight
- bq-table-wiring-audit
- context-audit
- crawl-adversarial-review-cascade
- deploy-identity
- epic-reorganization
- inbox-writer
- index-context
- klever-bq-store-lookup
- leo-ac-scaffold
- mb-doc-housekeeping
- morning-brief
- morning-primer
- pre-flight
- pre-ship-check
- push-adr
- ralph-loop-preflight
- sitrep
- spillover-scan
- status-index
- tdd
- test-adversarial
- um-local-seed
- validate-repo-links
- vendor-api-ingest
- vendor-question-escalation

## Invoked 1-2 times (15) — low use

- api-spike (1)
- brownfield-sbe-audit (1)
- geocode-bq-locations (1)
- klever-data-pipeline (1)
- meeting-to-action (1)
- slack (1)
- sprint-estimation (1)
- thermo-nuclear-code-quality-review (1)
- ticket-init (1)
- transcript-knowledge-miner (1)
- wiki-lint (1)
- zoom-out (1)
- grill-me (2)
- pr-review (2)
- ticket-to-pr-analyst (2)

## Actively used (31)

- gab-operationalize (292)
- bibliotheque-librarian (100)
- dark-factory (98)
- klever-mr (87)
- post-comment (82)
- jira (73)
- gitlab (42)
- ui-probe (37)
- dev-status (19)
- notion (17)
- service-factory (16)
- sprint-factory (11)
- klever-terraform-infra (11)
- operationalize-audit (10)
- klever-local-stack (10)
- grill-with-docs (10)
- gcloud (10)
- adversarial-cascade (10)
- graphify (9)
- floor-manager (7)
- challenge (7)
- wth-just-happened (6)
- investigate (6)
- har-diagnostic (5)
- feedback-to-spec (4)
- create-tickets (4)
- write-a-skill (3)
- sprint-close (3)
- klever-local-stack-real-bq (3)
- harness-audit (3)
- caveman (3)

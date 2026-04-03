# Operations

Running the system: setup, troubleshooting, infrastructure reference, and known issues.

## Files

| File | Summary |
|------|---------|
| `setup-snapshot-plugins-agents-skills-backlog.md` | Current setup: 9 plugins, 16 agents, 35+ skills, 8 hook types. Priority optimization backlog. |
| `supervisr-datastore-topology-environments.md` | Cross-service Datastore map: databases, namespaces, GCP projects per environment (dev/UAT/prod/R&D). Includes operational tools (nuke, extract). |
| `supervisr-auth0-topology-m2m-apps.md` | Auth0 tenants, M2M apps (leadAdmin, Clarifying sellers), JWT claims, and authentication guardrails per environment. |
| `supervisr-infrastructure-guardrails.md` | Hard-won rules: Cloud Armor, auth on shared envs, service code integrity, R&D isolation, JIB builds, PubSub self-provisioning. Every rule from a real incident. |
| `supervisr-service-graph-deployment.md` | Service topology (10 services), DAC repo mappings, full deploy sequence (tag → JIB → DAC pipeline), partner context (Clarifying). |
| `supervisr-test-harness-gotchas.md` | DTU architecture, shell scripting pitfalls, Datastore emulator quirks, GraphQL API gotchas, harness lifecycle rules. |

## Sections

### troubleshooting/ — Known problems with solutions
| File | Summary |
|------|---------|
| `git-iap-push-device-not-configured-tty-fix.md` | Git push behind IAP fails: "device not configured". Root cause: TTY needed for credential helper. Fix: push from local terminal. |

### known-issues/ — Open problems without full solutions
| File | Summary |
|------|---------|
| `pickup-ticket-phase6-missing-jira-comments.md` | pickup-ticket agent skips `jira/comments/` in Phase 6; misses spec clarifications |
| `test-harness-false-completion-path-divergence.md` | False completion anti-pattern: agent shortcuts verification using alternate code path (9 KB analysis) |

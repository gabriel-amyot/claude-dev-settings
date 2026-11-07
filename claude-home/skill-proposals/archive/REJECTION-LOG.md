# Skill Proposal Rejection Log

Why archived proposals were not built. Read this before re-proposing a similar skill.

## Audit 2026-08-18 — auto-rejected (duplicate or superseded)

Context: 118 skills installed at audit time. The drift alarm is 120. A proposal must
now displace something or fold into an existing skill to earn a slot.

| Proposal | Superseded by |
|---|---|
| 2026-05-20-debug-fix-ship | skill `service-factory`, built later as the Fix Factory |
| 2026-05-28-sprint-close-batch | skill `sprint-close`, which already batches |
| 2026-05-29-ticket-adversarial-gate | skill `leo-ac-scaffold` plus agent `story-quality-gate` |
| 2026-05-17-dispatch-readiness-gate | `dark-factory` concierge gate plus `ralph-loop-preflight` |
| 2026-05-20-post-deploy-smoke | `pre-ship-check` plus `klever-sprint-exit` |
| 2026-06-10-session-crash-recovery-map | skill `ghostty-recover-sessions` |
| 2026-06-08-capture-ui-screenshots-for-jira | `sprint-screenshot-capture` plus `ui-probe` proof mode |
| 2026-06-15-klever-frontend-deploy-verify | project CLAUDE.md rule on the DAC "apply in dev" bridge job |
| 2026-05-21-self-improving-skill-template | `write-a-skill` and `skill-creator` |
| 2026-06-02-render-paste-ready-html-card | memory rule `feedback_slack_html_format` |
| 2026-08-12-codex-adversarial-pass | `adversarial-cascade`, whose phase 2 is the Codex framing |

Rejection is not a judgement on the underlying lesson. Each lesson already lives
somewhere. The rejection prevents a second home for it.

## Audit 2026-11-06: adversarial triage (Claude first pass, Codex second pass)

Context: 119 skills installed, drift alarm at 120. Each proposal was checked for overlap and for
recurrence in transcript history, then re-attacked by Codex. Report: /tmp/skill-proposals-review/index.html
(save copy in project-management sessions). Verdict ARCHIVE on both passes or Codex final.

| Proposal | Covered by | Why archived |
|---|---|---|
| 2026-06-01-proximity-geocode | mapping:geocode, geocode-bq-locations, mapping:location-scrape | Archive as implemented; do not conflate the sheet workflow with the distinct BQ writeback workflow. |
| 2026-06-04-klever-dev-autostop | klever-dev-portal, dev-status, nightly 20:00 EDT auto-shutdown scheduler | Archive the duplicate and keep timed shutdown behavior under klever-dev-portal. |
| 2026-06-11-non-expert-interview-depth-probe | grilling (stress-test pattern) | Archive the standalone skill while preserving the useful evidence-parity advice as ordinary knowledge. |
| 2026-07-02-klever-add-ci-test-check | bibliotheque stack/ci-cd/gitlab-ci-patterns.md, project CLAUDE.md 'Read shared CI templates' rule, gitlab | Archive because the SOP already covers the procedure, while recognizing verified recurrence across repositories. |
| 2026-07-03-goldfish-delivery-enrichment | adtech:goldfish, KTP-830 production DOOH report FaaS, bibliotheque vendors/goldfish/goldfish-ads.md | Archive the proposal, with narrower claims about what the production report demonstrably supersedes. |
| 2026-07-03-klever-cfg-app-onboard-repo | bibliotheque sops/klever-faas-service-creation.md, bibliotheque stack/klever-cfg-branch-and-repo-conventions.md, klever-terraform-infra | Archive because the proposed SOP additions are already present. |
| 2026-07-07-proposal-factcheck | bibliotheque sops/pre-meeting-stakeholder-proposal-fact-check.md, investigate, challenge | Archive because the exact SOP exists and the cited later fact-check does not establish the same workflow recurring. |
| 2026-07-08-datasophia-rename-orphaning-recovery | _archive/klever-repo-rename, klever-terraform-infra, git | Archive the duplicate recovery proposal, while retaining the operational importance of its existing SOP. |
| 2026-07-19-crit-adversarial-loop | crit:crit-cli, crit:crit, adversarial-cascade | Archive because the claimed remaining SOP work is already documented. |
| 2026-07-29-measurement-map-datafix-validation | bibliotheque sops/autonomous-workflows/dark-factory-verification-patterns.md, klever-bq-store-lookup, ui-probe | Archive because the exact procedure already exists, not because variable predicates make reuse impossible. |
| 2026-08-07-question-elimination-pass | bibliotheque sops/autonomous-workflows/deferred-ac-must-surface-to-po.md (section at line 176), vendor-question-escalation, memory explain-options-before-asking | Archive the duplicate proposal, while rejecting the first pass's loose overlap and recurrence accounting. |
| 2026-08-09-sprint-mission-control | klever-sprint-exit, sprint-close, klever-sprint-mgmt | Keep ARCHIVE, but base it on missing independent demand and orchestration cost rather than unverified sprint-skill coverage. |
| 2026-08-10-agent-money-write-safety | documentation/bibliotheque/sops/autonomous-workflows/agent-design-verification-patterns.md, documentation/bibliotheque/operations/security-findings.md, documentation/bibliotheque/vendors/equativ/equativ-mcp-design-principles.md | Archive the duplicate skill proposal while preserving the existing design checklist and discounting echoed recurrence counts. |
| 2026-08-10-klever-repo-manifest | git, validate-repo-links, ~/.claude/library/context/workspace-map.yaml | Archive the parked wrapper because its knowledge is discoverable and its operational pieces already have owners. |
| 2026-08-12-validation-battery-workflow | workflow-authoring, klever-test, dark-factory (QA) | Archive the skill proposal while retaining the ticket script as an example, without relying on an unverified workflow-authoring installation. |
| 2026-08-24-tool-description-lint | app-ttd-trading-mcp test suite, bibliotheque 'tool descriptions as prompts' section | Archive the standalone skill while retaining repository tests and avoiding the claim that fixed-string assertions implement a general semantic linter. |
| 2026-08-24-zero-dependency-deck | frontend-design, anthropic-skills:pptx, stack/prd-authoring-tooling-gotchas.md | Archive because the useful offline-rendering rule already exists and the proposed SOP addition adds preferences rather than a demonstrated missing control. |
| 2026-08-25-review-a-reconciled-plan | challenge, grilling, tech-doc-review-flow | Archive the separate skill because the specific lesson is already documented and an existing review entry point covers invocation. |
| 2026-09-01-no-agent-extraction-cron | ~/.hermes/scripts/memory_curator.py, ~/.hermes/scripts/people_curator.py, bibliotheque stack/proxi-personalization-and-ops-findings.md | Archive the skill proposal, while correcting the unverified claim that its reference scripts remain at the advertised paths. |
| 2026-09-14-spec-drift-check | SOP deferred-ac-must-surface-to-po.md, proposal 2026-08-19-spec-contradiction-sweep, klever-sprint-exit | Archive because the exact lesson is already documented and the proposed integration owner is unavailable. |
| 2026-09-14-unattended-task-prompt | schedule (built-in), loop (built-in), SOP authoring-unattended-scheduled-prompts.md | Archive the duplicate proposal without claiming that SOP recall proves the underlying problem is solved. |
| 2026-10-25-big-picture-overview-page | sitrep, wayfinder-viewer, frontend-design:frontend-design | Archive the standalone proposal because its distinct artifact has no demonstrated recurrence and its broad triggers already collide. |
| 2026-10-27-klever-backend-local-loadtest | klever-local-stack-real-bq, bq-schema-preflight, bibliotheque inbox/archive/2026/2026-10-27-ktp-1358-zip-limit-map-endpoint-and-ship-path.md | Archive the standalone skill, but do not claim the existing startup skill or archived findings already implement its measurement method. |
| 2026-11-03-colleague-message-draft | memory colleague-message-style, memory open-artifacts-in-browser, post-comment | Archive the duplicate drafting skill while correcting the first pass's unsupported global-memory and posting-overlap claims. |
| 2026-11-05-klever-professional-story-research | research, transcript-knowledge-miner, bibliotheque inbox/2026-11-05-klever-story-research-evidence-and-delivery.md | Archive the separate skill because its reusable lessons are captured, without treating publication as an automatic step. |

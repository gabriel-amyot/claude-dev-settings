# Recall hook measurement (45 days, Klever transcripts)

- **transcripts**: 43
- **real_prompts**: 210
- **prompts_with_injection**: 134
- **injection_rate**: 0.638
- **pointers_injected**: 782
- **avg_pointers_when_fired**: 5.84
- **machine_prompts**: 157
- **machine_prompts_with_injection**: 94
- **machine_pointers_injected**: 513
- **pointers_opened_same_turn**: 20
- **pointer_consumption_rate**: 0.026
- **turns_that_opened_any_library_page**: 54
- **of_those_with_no_pointer_injected**: 11
- **auto_memory_writes**: 10
- **library_writes**: 35

## ALIASES structure
```json
{
  "klever": {
    "alias_rows": 1651,
    "rows_with_keyword_column": 9,
    "distinct_pages_aliased": 362,
    "pages_on_disk": 514,
    "pages_with_no_alias_row": 189,
    "max_rows_for_one_page": [
      "stack/ci-cd/gitlab-ci-patterns.md",
      41
    ],
    "aliases_md_bytes": 301929
  },
  "global": {
    "alias_rows": 64,
    "rows_with_keyword_column": 56,
    "distinct_pages_aliased": 56,
    "pages_on_disk": 140,
    "pages_with_no_alias_row": 87,
    "max_rows_for_one_page": [
      "context/llm-tool-design-safety-patterns.md",
      5
    ],
    "aliases_md_bytes": 20538
  }
}
```

## Most injected aliases
- worktree-env-local-force-delete (17)
- claude-code-cli-harness-gotchas (10)
- working-with-this-system (9)
- cold-drop-test (7)
- harness-state-dashboard-premise-audit (6)
- llm-tool-design-safety-patterns (6)
- worktree-fleet-ops (6)
- ac-narrowing (6)
- windows-only-path-needs-source-guard (6)
- timeout-not-on-macos (6)
- schema-field-stronger-than-free-text (6)
- proxi (5)
- mr-review-request-format (5)
- generated-vocabulary-outlives-source-data (5)
- piped-pytest-exit-status (5)
- shared-python-libraries (5)
- pending-folder-retired (5)
- build-tooling-silent-side-effects (5)
- slug-collision-ledger-check (5)
- canada-map-architecture (5)

## Pages injected often but never opened
- documentation/bibliotheque/~/.claude/library/context/build-tooling-silent-side-effects.md (24)
- documentation/bibliotheque/stack/ci-cd/gitlab-ci-patterns.md (16)
- documentation/bibliotheque/stack/gitlab-iap-devtools.md (16)
- documentation/bibliotheque/sops/autonomous-workflows/agent-design-verification-patterns.md (12)
- documentation/bibliotheque/sops/qa-review/guard-test-validity-and-falsification.md (11)
- documentation/bibliotheque/stack/local-dev/claude-code-cli-harness-gotchas.md (10)
- documentation/bibliotheque/sops/qa-review/diagnostic-probe-validity-and-symptom-discipline.md (10)
- documentation/bibliotheque/stack/local-dev/localhost-debugging-gotchas.md (10)
- documentation/bibliotheque/sops/autonomous-workflows/dark-factory-verification-patterns.md (10)
- documentation/bibliotheque/stack/frontend-map-gotchas.md (10)
- documentation/bibliotheque/sops/external-message-workflow.md (9)
- documentation/bibliotheque/sops/klever-faas-service-creation.md (9)
- documentation/bibliotheque/sops/autonomous-workflows/single-terminal-sprint-orchestration-patterns.md (9)
- ~/Developer/grp-beklever-com/project-management/documentation/process/working-with-this-system.md (9)
- documentation/bibliotheque/sops/qa-review/rerun-the-probe-before-accepting-unknown.md (9)
- documentation/bibliotheque/sops/autonomous-workflows/inbox-is-github-issues-not-pending-files.md (8)
- .claude/library/context/build-tooling-silent-side-effects.md (8)
- .claude/library/context/llm-tool-design-safety-patterns.md (7)
- documentation/bibliotheque/sops/qa-review/reviewing-external-artifacts-and-handover-discipline.md (7)
- documentation/bibliotheque/sops/sprint-management-dispatcher.md (7)

## Pages opened without a pointer (recall misses, proxy)
- documentation/bibliotheque/INDEX.md (10)
- documentation/bibliotheque/stack/proxi-gcp-home-architecture.md (10)
- documentation/bibliotheque/operations/proxi-operator-runbook.md (9)
- documentation/bibliotheque/ALIASES.md (9)
- documentation/bibliotheque/operations/klever-repository-map.md (4)
- documentation/bibliotheque/inbox/INDEX.md (4)
- documentation/bibliotheque/stack/bigquery/salesforce-mirror-analysis-traps.md (3)
- documentation/bibliotheque/sops/gabriel-voice-issue-and-review-posts.md (3)
- documentation/bibliotheque/stack/proxi-read-list-contract.md (3)
- .claude/library/context/jira-skill-gotchas.md (2)
- documentation/bibliotheque/agent-hub/media-planning-agent-reference.md (2)
- documentation/bibliotheque/sops/superwhisper-multilingual-transcription.md (2)
- documentation/bibliotheque/inbox/2026-10-27-proxi-gmail-restore-and-0-2-12-release.md (2)
- documentation/bibliotheque/stack/proxi-hermes-slack-integration-gotchas.md (2)
- documentation/bibliotheque/sops/autonomous-workflows/codex-cli-adversarial-review-patterns.md (2)
- documentation/bibliotheque/inbox/2026-10-22-proxi-gmail-oauth-discovery.md (2)
- documentation/bibliotheque/stack/proxi-hermes-agent-platform-gotchas.md (2)
- documentation/bibliotheque/sops/autonomous-workflows/wayfinder-map-lifecycle-close-and-persist.md (2)
- documentation/bibliotheque/development/github-cli-issues-reference.md (2)
- documentation/bibliotheque/people/profiles/sisi-yao.md (1)

## Auto-memory dirs (file counts)
- memory: 8

# Skill Proposal: validation-battery-workflow
Date: 2026-08-12
Source: KTP-1062/1065 validation ladder (session fierce-ibis)

## Trigger
Any environment validation that must be deterministic and repeatable across environments
(local → dev → prod): API guard verification, refusal-path testing, post-deploy smoke batteries.
User says "validate deterministically", "probe battery", "workflow-gate the checks".

## Scope
Global (harness-level pattern; org-agnostic).

## Draft Steps
1. Pin a battery JSON per rung: probes as `{id, method, url, headers, body, expect:{status, bodyMustContain[]}}`, expected values extracted from the test suite's assertions, secrets as placeholders substituted from env at invoke.
2. Generalize `tickets/KTP/no-epic/KTP-1062/tools/ttd-validation-rung.workflow.js` into a shared script: one low-effort agent per probe (dumb pipe, no retries), JS gate computes PASS/BLOCKED, tiered escalation (tier N+1 only after tier N clean), throws on any mutation-endpoint probe expecting 2xx.
3. Evidence agent writes a deterministic markdown file per run + INDEX line.
4. Caller contract: EXIT criterion = returned `{verdict:"PASS"}`; BLOCKED means stop and report, never quiet-fix-and-rerun.

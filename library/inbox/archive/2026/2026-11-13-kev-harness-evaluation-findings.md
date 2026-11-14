# Tribal Knowledge: Kev pilot and shared harness evaluation

**Source:** Kev read-only pilot and cross-host harness-health planning, study dated 2026-10-31, archived 2026-11-13. Applies across the shared harness, including Klever, Codex, and Claude Code. These findings do not authorize deployment.

## 1. Separate apparatus checks from effectiveness evidence

Passing regression tests, authentication checks, and authored probes demonstrates only their tested scope. The native study completed 728 measured requests with no request failures, but its recall decision remained `INSUFFICIENT_EVIDENCE`. Blind regrading of authored cases does not turn them into independent held-out queries. Missing labels remain unknown. Retain disputes rather than silently adjudicating them in favor of a headline score.

## 2. Measure complete operations and retain cache conditions

Report new-state, repeated-state, priming, individual request, and whole-query measurements separately. In this study, a controlled 20-candidate operation took a median 18.615 seconds across six queries; the authored 20-candidate replay median was 25.304 seconds across fourteen queries. Small-cell p95 is exploratory. Hosted Jev latency or pricing claims are not measurements of local Kev. This pilot used pinned native MLX, not Ollama.

## 3. Preserve the actual baseline and independent recall reference

Use three separate arms: actual operational retrieval, a full-text lexical control, and Kev reranking over the same controlled pool. Reranking cannot recover essential documents excluded by candidate generation. Pooled relevance judgments do not measure general recall without an independent essential-document reference. Reserve independent sessions and topics before tuning thresholds or inspecting locked comparison results.

## 4. Qualify repeatable evals before scoring the harness

An existing eval registry is reusable infrastructure, not a qualified health score. Verify registration, failure exit propagation, source versions, runtime identity, and whether assertions encode intended policy or characterize a known defect. Keep safety, quality, efficiency, human effort, and coverage/freshness separate; unknown is not zero. Critical safety failures must remain visible and veto a favorable overall summary. No numeric overall score was qualified here.

## 5. Establish isolation and scope before collection

Prevent writes and network access before an experiment runs; post-run checks alone do not prevent damage. Admit known and authorized project scope before opening session history. Unknown context is denied. Shared source files do not establish equal host enforcement. Qualify Codex and Claude Code separately on representative tasks before passive capture or schedules. Preserve project-management's single-trunk rule.

## 6. Archive incomplete work without claiming completion

Preserve exact report revisions, aggregate results, private evidence hashes, uncertainty, next actions, and restart requirements. Park unqualified evaluation and implementation work; do not close their issues as complete or resume automatically. Keep credentials, raw prompts, and library bodies out of public evidence. Check process ownership before any cleanup; never signal a historical PID based only on an old receipt.

**Evidence:** [archived pilot report](https://github.com/gabriel-amyot/claude-dev-settings/blob/GH-1-kev-pilot-review/experiments/kev-pilot/results/2026-11-13-archive.md), [reviewed harness-health plan](https://github.com/gabriel-amyot/claude-dev-settings/blob/bca3929/docs/plans/harness-health/PLAN.md), and [adversarial review](https://github.com/gabriel-amyot/claude-dev-settings/blob/bca3929/docs/plans/harness-health/REVIEW.md).

**Curator notes:** Global shared-library scope. Promote as a dated evidence and evaluation reference. Do not turn pilot measurements or unimplemented plan requirements into claims about current production behavior. No new skill is needed for this capture.

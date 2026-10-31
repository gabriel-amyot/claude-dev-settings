# Adversarial review

Status: independent review and targeted resolution check completed. Four required revisions applied and verified.

Final disposition: **ready for foundation implementation; no remaining must-fix plan blockers**.

The independent reviewer inspected the written plan, actual eval registry/runner, observatory contract/schema/collector, priority documents, calibration procedure and completed pilot summaries. It ran no evaluations and made no changes.

Initial disposition: **not ready as written; ready after four bounded revisions**.

## Required revisions

| Finding | Evidence audited | Applied resolution |
|---|---|---|
| Scratch paths and post-run diffs do not contain external/live writes | Sweep executes shell commands and has hardcoded live outputs; hook fixtures inherit environment and run setup/teardown | Phase 0 now requires a qualified disposable execution boundary, fixture HOME, minimal environment, no production credentials, explicit write/network policy, process-tree cleanup and deliberate escape controls. Unsupported isolation blocks execution. |
| Unknown context can leak into global collection | Current collector opens Codex histories before per-event filtering; path-name scope matching is too weak | Privacy admission is deny-by-default before source access. Unknown contexts produce anonymous capture-gap counts only. Current broad refresh cannot be reused unchanged. Allowlisting covers errors, logs, spools and reports. |
| A stronger lexical candidate could silently replace the operational baseline | Current comparator searches metadata while Kev reads document text | Phase 3 names A as the frozen incumbent, B as a stronger full-text control, and C as Kev on B's identical pool. Deployment-effect and reranking-effect claims remain separate. |
| Pooled returned labels do not establish a recall denominator | Pilot retains incomplete relevance metrics rather than treating unjudged pages as irrelevant | Phase 3 now requires independent essential-document references or an explicitly limited judged-pool recall metric. Larger sample counts cannot repair missing reference judgments. |

## Additional improvements applied

- Define a useful scoped version-zero status before waiting for a machine-wide numeric score. Missing optional human-effort data need not invalidate unrelated narrow claims.
- Make the first outcome milestone one knowledge/continuity comparison across both CLIs. Desktop, any-cwd qualification and scheduling remain later bounded milestones; a full combinatorial matrix is unnecessary.
- Distinguish changes that invalidate affected qualification from proven non-behavioral annotations. Preserve stale results and missing coverage in denominators.

## Assumption audit

The dirty/untracked observatory concern was verified. A clean remote checkout does not reproduce the inspected system. The completed pilot establishes transport completion and recorded latency, while retaining `INSUFFICIENT_EVIDENCE` for quality. Hook configuration and shared skills do not establish runtime enforcement. Project-management's single-trunk rule remains intact.

The reviewer recommended extending the existing observatory without a new dashboard database or more conceptual phases. No implementation approval or operational deployment is implied by plan readiness.

## Resolution check

The independent reviewer reread the revised sections and confirmed all four required changes. It also verified the early scoped status, small first outcome tracer and drift policy. No further plan blockers remained.

Execution dependencies remain: preserve/version the intended source, pin dependencies, qualify the disposable execution boundary, prove the isolated producer tracer with pass/failure controls, register study tradeoffs before locked trials, and qualify each host surface with native hook trust where required. None has been represented as implemented by this plan.

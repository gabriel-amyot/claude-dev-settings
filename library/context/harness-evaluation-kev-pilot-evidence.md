---
title: Kev pilot evidence and harness evaluation limits
type: context
created: 2026-11-13
updated: 2026-11-13
tags: [harness, evaluation, kev, evidence]
aliases: [kev-pilot-evidence, harness-health-evidence]
related:
  - "[[shared-skills-harness-observatory]]"
  - "[[harness-self-management]]"
  - "[[session-lifecycle-skills]]"
  - "[[context-engineering]]"
provenance:
  epistemic: inferred
  confidence: medium
  primary_sources:
    - ref: calm-moth
      kind: session-capture
      path: ../inbox/archive/2026/2026-11-13-kev-harness-evaluation-findings.md
      captured: 2026-11-13
    - ref: kev-pilot-archive
      kind: report
      url: https://github.com/gabriel-amyot/claude-dev-settings/blob/GH-1-kev-pilot-review/experiments/kev-pilot/results/2026-11-13-archive.md
  raw_pages:
    - "curate:calm-moth:kev-health:n1"
    - "curate:calm-moth:kev-health:n2"
    - "curate:calm-moth:kev-health:n3"
    - "curate:calm-moth:kev-health:n4"
    - "curate:calm-moth:kev-health:n5"
    - "curate:calm-moth:kev-health:n6"
  verified_against: null
  status: active
---

# Kev pilot evidence and harness evaluation limits

This page distills the 2026-10-31 local study and the reviewed harness-health plan, archived on 2026-11-13. It records evidence limits and proposed qualification requirements. It does not establish current production behavior or authorize deployment. The [source capture](../inbox/archive/2026/2026-11-13-kev-harness-evaluation-findings.md) and [bronze excerpts](../_archive/curate-pages.jsonl) retain the provenance.

## Apparatus checks and effectiveness are separate

The capture reports 728 completed measured requests without a request failure, while the recall decision remained `INSUFFICIENT_EVIDENCE`. Regression tests, authentication checks, and authored probes cover only their tested scope. Blind regrading does not make authored queries an independent holdout. Missing labels and unresolved grading disputes remain unknown. [INFERRED ← [[kev-harness-capture]] · page:curate:calm-moth:kev-health:n1]

**How to apply:** Keep test and request success separate from evidence of better real-task outcomes. Consult [[shared-skills-harness-observatory]] for the distinction between catalog entries, activity, and verified outcomes.

## Measure the complete operation

The capture reports a controlled 20-candidate median of 18.615 seconds across six queries. Its authored 20-candidate replay median was 25.304 seconds across fourteen queries. Small-cell p95 estimates are exploratory. Hosted Jev claims do not measure local Kev. This pilot used pinned native MLX rather than Ollama. [INFERRED ← [[kev-harness-capture]] · page:curate:calm-moth:kev-health:n2]

**How to apply:** Record new-state, repeated-state, priming, request, and whole-query timings separately. Treat these numbers as dated local observations. Use [[context-engineering]] when assessing the cost of the complete retrieval operation.

## Preserve the actual baseline and recall reference

The reviewed plan requires three arms: actual operational retrieval, a full-text lexical control, and Kev over the same controlled pool. A reranker cannot recover essential documents omitted by candidate selection. General recall claims need independent essential-document references beyond pooled judgments. Independent sessions and topics must be reserved before tuning or inspecting locked results. [INFERRED ← [[kev-harness-capture]] · page:curate:calm-moth:kev-health:n3]

**How to apply:** Freeze each arm and its evidence contract before comparing outcomes. These controls remain qualification work, not completed pilot acceptance.

## Qualify the evals before assigning a score

An existing eval registry provides infrastructure rather than a qualified health score. Check suite registration, failure exits, source versions, runtime identity, and whether assertions express intended policy. The plan keeps safety, quality, efficiency, human effort, and coverage/freshness separate. Unknown evidence is not zero. Critical safety failures veto a favorable summary. No overall numeric score was qualified. [INFERRED ← [[kev-harness-capture]] · page:curate:calm-moth:kev-health:n4]

**How to apply:** Read coverage and provenance beside each result. Use [[harness-self-management]] for the related cautions about usage and cost evidence.

## Establish isolation and scope before collection

The reviewed plan requires prevention of writes and network access before tests run. A post-run comparison alone does not prevent side effects. Authorized project scope must be established before reading history. Unknown scope is denied. Shared files do not establish equal host enforcement. Codex and Claude Code need separate representative-task qualification before passive capture or schedules. [INFERRED ← [[kev-harness-capture]] · page:curate:calm-moth:kev-health:n5]

**How to apply:** Qualify each host and preserve project-management's single-trunk rule. Do not enable broad collection based on shared source identity alone.

## Park unfinished work with a restart contract

The capture requires exact report revisions, aggregate results, private evidence hashes, uncertainty, next actions, and restart conditions. Unqualified evaluation and implementation remain parked, not complete. Public evidence excludes credentials, raw prompts, and library bodies. A historical PID alone is insufficient authority for a cleanup signal. [INFERRED ← [[kev-harness-capture]] · page:curate:calm-moth:kev-health:n6]

**How to apply:** Use [[session-lifecycle-skills]] to preserve the parked handoff. Resume only on an explicit request, then recheck environment identity and evidence freshness.

## Retained reports

- [Pilot archive](https://github.com/gabriel-amyot/claude-dev-settings/blob/GH-1-kev-pilot-review/experiments/kev-pilot/results/2026-11-13-archive.md)
- [Reviewed harness-health plan](https://github.com/gabriel-amyot/claude-dev-settings/blob/bca3929/docs/plans/harness-health/PLAN.md)
- [Adversarial review](https://github.com/gabriel-amyot/claude-dev-settings/blob/bca3929/docs/plans/harness-health/REVIEW.md)

The measurements are not a population benchmark. The plan is not operational qualification. This page does not resolve label disputes or verify cross-host behavior.

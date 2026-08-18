---
name: data-source-cross-examination
description: "Compare external data sources to determine if they should share infrastructure. Fills a standardized dimension matrix per source, assesses convergence. Trigger: 'compare data sources', 'cross-examine', 'should we share infrastructure?', 'unified vs separate pipeline'. Global scope. Input: 2+ data source descriptions. Returns: comparison matrix + recommendation."
nav:
  bay: plan
  when: "Compare external data sources to assess infrastructure sharing viability."
  when_not: "Already decided on architecture. Single data source."
---

# Data Source Cross-Examination

Structured comparison of external data sources to determine whether they should share pipeline infrastructure.

## When to Use

- Evaluating whether two vendor APIs should share a data pipeline
- Deciding between a unified framework vs independent integrations
- Onboarding a new data source and checking if it fits an existing pattern

## Steps

### 1. Identify Sources

Ask the user to name the 2+ data sources to compare. For each, gather:
- Existing documentation (bibliotheque, vendor docs, spike reports)
- API docs or integration code
- Any existing pipeline code

### 2. Fill Dimension Matrix

For each source, research and fill this matrix. Use Grep/Read on existing code and docs to find evidence.

| Dimension | Description | Source A | Source B |
|---|---|---|---|
| **Data sourcing pattern** | sync/async, batch/stream, pull/push | | |
| **Query trigger** | scheduled/user-driven/event-driven | | |
| **Volume per run** | records per call + growth trajectory | | |
| **Transformation complexity** | raw pass-through vs heavy ETL | | |
| **BQ storage needs** | append/snapshot/none/materialized view | | |
| **Freshness tolerance** | real-time / hourly / daily / weekly | | |
| **Scheduling mechanism** | cron / on-demand / webhook / polling | | |
| **Auth model** | API key / OAuth / service account / none | | |
| **Error handling** | retry strategy, partial failure, idempotency | | |
| **Tenant scoping** | per-advertiser / global / per-org | | |
| **Retention model** | TTL / append-only / sliding window | | |
| **Idempotency strategy** | upsert / dedup key / timestamp-based | | |

### 3. Compare Dimensions

For each row, mark:
- **Same infra? Yes** — identical pattern, trivially shared
- **Same infra? No** — fundamentally different, sharing would create complexity
- **Same infra? Depends** — could share with an adapter layer, but adds abstraction cost

Include reasoning for each assessment.

### 4. Assess Convergence

Count Yes/No/Depends across all dimensions:
- **>70% Yes on critical dimensions** (sourcing, trigger, auth, error handling) = strong case for unified framework
- **<40% Yes** or **fundamentally different sourcing patterns** = independent pipelines
- **Between 40-70%** = hybrid (shared infra layer with source-specific adapters)

Identify:
- Which shared dimensions enable the most reuse (auth, scheduling, BQ sink)
- Which divergent dimensions would force the most complexity if shared (volume, freshness, error model)

### 5. Output Recommendation

One of three:
1. **Unified framework** — shared pipeline with configurable source adapters
2. **Independent pipelines** — separate implementations, no shared code
3. **Hybrid** — shared infrastructure layer (auth, scheduling, BQ sink) with independent data-specific logic

Write the report to `tickets/{PREFIX}/{TICKET-ID}/reports/architecture/data-source-cross-examination-{date}.md` if ticket context exists.

Include:
- The filled dimension matrix
- Per-dimension convergence assessment
- Final recommendation with evidence
- Risk factors for the recommended approach
- Migration path if sources diverge over time

## Notes

- This is an analysis skill, not an implementation skill. It produces a recommendation document.
- The matrix is intentionally comprehensive. Skip dimensions that truly don't apply, but err on the side of filling them.
- Prior art: KTP-130/KTP-131 cross-examination compared Placer CBG data vs Goldfish DOOH billboard data.

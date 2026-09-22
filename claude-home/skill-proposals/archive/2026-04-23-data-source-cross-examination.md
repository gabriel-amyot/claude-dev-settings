# Skill Proposal: data-source-cross-examination
Date: 2026-04-23
Source: KTP-130/KTP-131 cross-examination document

## Trigger
"compare data sources", "cross-examine", "should we share infrastructure?", or when evaluating whether two external data sources should share a pipeline.

## Scope
global

## Draft Steps
1. Identify the two (or more) data sources to compare
2. For each source, fill a standardized dimension matrix:
   - Data sourcing pattern (sync/async, batch/stream)
   - Query trigger (scheduled/user-driven/event-driven)
   - Volume per run + growth trajectory
   - Transformation complexity
   - BQ storage needs (append/snapshot/none)
   - Freshness tolerance
   - Scheduling/triggering mechanism
   - Auth model
   - Error handling patterns
   - Advertiser/tenant scoping
   - Retention model
   - Idempotency strategy
3. Compare dimensions: mark each as "Same infra? Yes/No/Depends"
4. Assess convergence: what CAN be shared vs what CANNOT
5. Output: recommendation (unified framework / independent pipelines / hybrid) with evidence

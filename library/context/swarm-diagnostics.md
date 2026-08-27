# Swarm Diagnostics — Multi-Service Debugging

On-demand context: load when debugging across multiple services, running parallel investigations, or triaging blockers.

## When to Use Swarm Diagnostics
- Bug spans multiple services (frontend + backend + BQ)
- Multiple independent hypotheses need parallel investigation
- Blocker triage requires checking several systems simultaneously

## Protocol

### Step 1: Isolate the symptom
Identify which layer is failing: frontend rendering, API response, BQ query, infrastructure.

### Step 2: Dispatch parallel investigation agents
Launch 2-3 Sonnet agents, each investigating one hypothesis:
- Agent 1: Check API response shape (curl endpoint, inspect JSON)
- Agent 2: Check BQ query directly (bq query, verify data exists)
- Agent 3: Check infrastructure state (COS running, logs, health endpoints)

Each agent returns a condensed finding (under 500 tokens).

### Step 3: Synthesize findings
Opus orchestrator reads all agent findings and identifies the root cause.

### Step 4: Fix or escalate
- If fixable: create the fix, run tests, commit
- If infrastructure: document the finding, escalate to user
- If data issue: document in `tickets/{ID}/reports/status/` and flag

## Common Multi-Service Issues (Klever)

| Symptom | Likely Cause | Check |
|---|---|---|
| Frontend shows empty map | Backend returns empty array | curl the API endpoint directly |
| API returns 500 | BQ query fails | Check BQ logs, verify SA permissions |
| BQ returns no rows | Wrong dataset/project or missing data | `bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM ...'` |
| COS returns 502/503 | Instance TERMINATED or restarting | `gcloud compute instances list` |
| Health check fails | Backend not started or wrong profile | Check Spring profile, verify port 8097 |
| IAP 403 on API call | Expired IAP cookie | `git fetch` on any Klever repo to refresh |

## Blocker Classification

| Category | Action |
|---|---|
| Code bug | Fix immediately |
| Missing data | Document, check if test data needs seeding |
| Infrastructure | Document, escalate (COS, IAM, networking) |
| Permissions | Document in `reports/architecture/`, check DAC terraform |
| Spec ambiguity | Post question to Jira via `/post-comment` |

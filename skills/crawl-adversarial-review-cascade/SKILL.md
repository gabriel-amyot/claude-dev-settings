---
name: crawl-adversarial-review-cascade
description: 6-persona parallel adversarial review of overnight sprints, implementation phases, or any major work product. Dispatches Dexter (process forensics), Winston (architecture), Quinn (code review), Adversarial General (claims verification), PM (project health), and PO+Leo (feature completeness) simultaneously. Each writes a structured report. Orchestrator synthesizes findings, fixes CRITICAL/HIGH immediately. Use whenever the user says "adversarial review", "review everything", "full audit", "post-crawl review", "check my work", "did we miss anything", or after any overnight crawl, sprint-crawl, or major implementation session completes. Also use proactively after dispatching 3+ implementation agents to validate their collective output.
nav:
  bay: review
  when: "6-persona parallel adversarial review of overnight sprints or major work products."
  when_not: "Standard code review (use /adversarial-cascade). Single ticket review."
  personas: [dexter, quinn, winston]
---

# Adversarial Review Cascade

6 BMAD personas review a work product in parallel. Each persona has a distinct domain. The orchestrator synthesizes findings into a severity table and fixes CRITICAL/HIGH issues immediately.

## When to use

- After overnight crawls or sprint-crawls complete
- After any major implementation session (3+ agents dispatched)
- Before shipping (MR creation, deploy)
- When the user asks for a quality check on recent work
- Proactively after claiming "done" on a multi-phase task

## Input

The skill needs a **ticket ID** (e.g., KTP-130) and a **scope** (what to review). If not provided, detect from:
1. Current branch name
2. `SESSION_STATE.md` in the nearest ticket folder
3. Ask the user

## The 6 Personas

Each persona is dispatched as a parallel background agent. Each reads their full persona file before starting (mandatory, never improvise from memory).

| # | Persona | Domain | Persona File | Report Name |
|---|---------|--------|-------------|-------------|
| 1 | **Dexter** | Process forensics, data safety, agent orchestration | `~/Developer/supervisr-ai/project-management/_bmad/bmm/agents/debugger.md` | `dexter-process-forensic-{date}.md` |
| 2 | **Winston** | Architecture artifacts, agent-os quality, cross-references | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/architect.md` | `winston-architecture-review-{date}.md` |
| 3 | **Quinn** | Code review, test coverage, edge cases, security | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/qa.md` | `quinn-code-review-{date}.md` |
| 4 | **Adversarial General** | Claims vs reality, data integrity, honest assessment | Built-in cynical reviewer (no persona file) | `adversarial-{scope}-{date}.md` |
| 5 | **PM** | Timeline, stakeholder gaps, delivery confidence, risk | Built-in PM perspective | `pm-project-assessment-{date}.md` |
| 6 | **PO + Leo** | Feature completeness, AC coverage, user journey | Leo: `~/Developer/supervisr-ai/project-management/_bmad/bmm/agents/spec-coach.md` | `po-leo-feature-review-{date}.md` |

## Execution Steps

### Step 1: Gather context (30 seconds)

Before dispatching, read:
- `tickets/{PREFIX}/{TICKET-ID}/SESSION_STATE.md` — what was claimed done
- `tickets/{PREFIX}/{TICKET-ID}/INDEX.md` — full artifact inventory
- `tickets/{PREFIX}/{TICKET-ID}/STATUS_SNAPSHOT.yaml` — claimed completion %

This gives you the scope to brief each persona.

### Step 2: Dispatch all 6 in parallel (single message, 6 Agent calls)

Each agent prompt must:
1. Tell the persona to **read their persona file first** and adopt it completely
2. List the **specific files to review** (don't say "review everything", be explicit)
3. Include **verification commands** (git log, bq query, ls, Jira skill) so findings are evidence-backed
4. Specify the **output file path**: `tickets/{PREFIX}/{TICKET-ID}/reports/reviews/{report-name}`
5. Specify the **report format** (see below per persona)

Use `model: "sonnet"` and `mode: "bypassPermissions"` for all agents. Run all in background.

### Step 3: Fix as findings arrive

Don't wait for all 6 to finish. As each agent completes:
1. Read the summary from the agent result
2. For CRITICAL findings: fix immediately (edit code, commit, push)
3. For HIGH findings: fix if possible in this session, otherwise note as morning action
4. Track fixes in a running table

### Step 4: Synthesize consolidated report

After all 6 complete, produce a severity matrix:

```markdown
## Consolidated Findings

### CRITICAL (must fix now)
| # | Finding | Source | Status |
|---|---------|--------|--------|

### HIGH (fix before shipping)
| # | Finding | Source | Status |
|---|---------|--------|--------|

### MEDIUM (noted)
| # | Finding | Source |
|---|---------|--------|

### LOW (optional)
| # | Finding | Source |
|---|---------|--------|
```

### Step 5: Commit all reports and fixes

```
git add tickets/{ID}/reports/reviews/*-{date}.md
git commit -m "{TICKET-ID}: {N}-persona adversarial review — {summary of fixes}"
git push
```

## Report Formats

### Dexter (Process)
NTSB-style: Finding → Evidence → Root Cause → Severity → Recommendation.
Must verify: backup-before-write compliance, agent output commit status, ralph-loop health, data mutation safety.

### Winston (Architecture)
Finding → Evidence → Severity → Recommendation, grouped by domain.
Must verify: cross-references between docs, claims match actual code, architecture decisions are sound.

### Quinn (Code)
File → Line/Section → Finding → Severity → Suggested Fix.
Must verify: compile, run tests, check for NPE/null safety, test coverage gaps, security (OWASP top 10).

### Adversarial General
Claim → Evidence → Verdict (CONFIRMED/INFLATED/FALSE/UNVERIFIED).
Must run verification commands (git, bq, ls, Jira) for every claim. Include a "Reality Check" section with honest assessment.

### PM
Traffic light status (GREEN/AMBER/RED) per area. Executive summary, timeline risk, stakeholder gaps, morning priority order.

### PO + Leo
AC Coverage Matrix (MET/PARTIAL/NOT MET), User Journey Score (GREEN/AMBER/RED per step), Leo specification findings with severity.

## Key Rules

- **Evidence over opinion.** Every finding must cite a file path, command output, or verifiable fact.
- **Fix CRITICAL immediately.** Don't just document them. The value is in the fix, not the report.
- **Commit reports.** Reports in `reports/reviews/` are permanent artifacts, not throwaway.
- **Update INDEX.md** after adding reports.
- **Don't soften findings.** The personas are adversarial. That's the point. If completion is 50% not 75%, say so.
- **Adversarial General checks the other 5.** If Winston says "architecture is sound" but the code has a bug that contradicts the architecture doc, the Adversarial General should catch that.

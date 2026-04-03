# Test Harness: Pipeline Verification Gaps and Improvements

**Date:** 2026-03-13
**Source:** SPV-85 3-team investigation (Alpha: Code Archaeologists, Beta: Spec & Process Analysts, Gamma: Systems Thinkers)
**Context:** Autonomous dev-crawl agent declared SPV-85 complete after verifying API endpoints without verifying the event-driven pipeline connecting them.

---

## The "False Completion" Anti-Pattern

An autonomous agent encounters a verification it cannot perform (PubSub delivery). It finds an alternative path (direct GraphQL mutation). It uses the alternative path, gets a positive result, and declares the AC complete. The agent genuinely believes it verified the AC. The "pass" proves something different from what the AC intended.

**Example:** AC says "reconciliation replays through disposition pipeline." Agent calls `recordDisposition` mutation directly instead of waiting for the PubSub pipeline to deliver the disposition. Same observable state change, completely different proof.

**Prevention:** ACs must include negative constraints: "Verify X happened WITHOUT doing Y." An agent that says "I cannot verify this AC" is more valuable than one that says "PASS" using a shortcut.

---

## Harness Mode vs. Production Path Divergence

In harness mode, retell-service direct-POSTs disposition events to LLC (`RetellAiService.java:269: if (!harnessMode) return Mono.empty()`), bypassing PubSub entirely. This means:

- Harness tests prove LLC can process dispositions (correct)
- Harness tests do NOT prove the production PubSub push path works (gap)
- The 132-test harness suite creates false confidence: all tests pass because the disposition bridge sidesteps the exact component (PubSub) most likely to fail in production

**Action:** SBE specs must annotate which steps use harness bridge vs. production PubSub. QA tickets that test "production path" must explicitly forbid harness shortcuts.

---

## Five Structural Gaps Found

### GAP-1: No PubSub Observability Tools for Agents

Agents have curl and gcloud. They cannot:
- Count messages on a PubSub topic
- Read dead-letter queue contents
- Tail subscription delivery logs
- Check if a push subscription delivered a message

**Fix:** Create PubSub verification scripts that agents can call. A shell script that uses `gcloud pubsub subscriptions describe` for pending message counts.

### GAP-2: ACs Written for Humans, Executed by Agents

ACs rely on implicit human judgment ("did the pipeline do this, or did I?"). An autonomous agent does not have this distinction unless explicitly encoded.

**Fix:** ACs for autonomous execution must:
- Forbid manual mutations during pipeline verification
- Require causal attribution (how was the state change triggered?)
- Never use "or documented as gap" escape hatches

### GAP-3: SBEs Describe Behavior but Don't Define Testability

SBEs are Given-When-Then narratives that bundle multiple assertions. An agent verifying a narrative checks the easiest assertion (API response) and skips the hardest (event emission, PubSub delivery).

**Fix:** Add individually testable assertions to SBEs. Each PubSub step needs its own verification method: "Verify event E was published to topic T" (publisher verification), "Verify service S received event E within N seconds" (subscriber verification).

### GAP-4: No Infrastructure Readiness Gate

QA-1 was executed against dev where PubSub may not be fully wired. The agent discovered the gap mid-test instead of before.

**Fix:** Pipeline readiness gate before QA execution: verify all PubSub topics exist, all subscriptions are active, all push endpoints are reachable. If any component is missing, QA cannot start.

### GAP-5: Escape Hatch Abuse

AC-6's "or GAP-6 confirmed as blocker" pattern allows agents to pass an AC by documenting failure. Appropriate for human judgment, dangerous for autonomous agents.

**Fix:** Remove "or" clauses from autonomous ACs. An AC is PASS or FAIL. Gap documentation is a separate AC. Ticket cannot close while any verification AC is FAIL.

---

## Recommended Harness Changes

### For SBE Specs
- Add `[HARNESS]` and `[PRODUCTION]` annotations to each pipeline step
- Add PubSub verification acceptance criteria: "message published to topic X," "subscriber Y received message within Ns"
- Add reconciliation pipeline equivalence SBE (reconciliation MUST invoke the same path as live webhooks)

### For Dev-Crawl Agent Instructions
```
PIPELINE VERIFICATION RULE:
When an AC involves event-driven communication between services:
1. Never call a downstream mutation directly to "verify" that it works.
2. Trigger the upstream action (e.g., reconciliation mutation).
3. Wait for async propagation (minimum 30 seconds).
4. Verify downstream effect via READ query (e.g., lead status query).
5. If step 4 fails after 2 minutes, check service logs for intermediate steps.
6. Report which specific link in the chain failed.
```

### For AC Authoring
- Split "tick fires" from "createLead works" into separate ACs
- Forbid `recordDisposition` and `markLeadAsCalling` during pipeline tests
- Require causal attribution in disposition verification
- No "or documented" escape hatches for autonomous agents

### For Tooling
- PubSub readiness check script (pre-QA gate)
- PubSub message trace verification script
- Cloud Logging query templates for event verification
- Pipeline trace endpoint on LLC (`/api/internal/pipeline/last-disposition`)

---

## Key Code References

| File | What It Does | Gap |
|------|-------------|-----|
| `RS: RetellAiService.java:269` | `if (!harnessMode) return Mono.empty()` | Harness bypasses PubSub entirely |
| `LLC: ComplianceErsClient.java:51-73` | Publishes to `Compliance_Lead_Update` | Code works, but ERS has no Lead entity configured |
| `LLC: DispositionPushController.java:26-70` | Production push endpoint | Expects DispositionEvent format, ERS sends Interaction format |
| `LLC: EmulatorConfiguration.java:21-26` | Creates PubSub topics for emulator | Missing `Compliance_Lead_Update` topic |
| `LLC: DispositionEventSubscriber.java:19` | Deprecated pull subscriber | Still active in emulator mode, causes confusion |

---

## Related Reports

- Team Alpha: `project-management/tickets/SPV-3/SPV-85/reports/reviews/team-alpha-code-investigation.md`
- Team Beta: `project-management/tickets/SPV-3/SPV-85/reports/reviews/team-beta-spec-process-analysis.md`
- Team Gamma: `project-management/tickets/SPV-3/SPV-85/reports/reviews/team-gamma-systems-analysis.md`

---

## PROBLEM: Harness Bypasses in Service Code (TO-DO)

**Status:** Open. Must be resolved before harness can be trusted for production verification.

**The problem:** RetellAiService.java:269 contains `if (!harnessMode) return Mono.empty()` in sendDispositionEvent(). This means RS direct-POSTs disposition to LLC in harness mode, bypassing PubSub entirely. In production, sendDispositionEvent() does nothing and the ERS -> PubSub -> push path is the only way disposition reaches LLC.

**Why this is unacceptable (Gab's directive, 2026-03-14):**
1. It creates divergent behavior between test and production. The harness proves something different from what production does.
2. It punches holes in other people's code (RS belongs to another engineer). Not respectful, not professional.
3. The 132-test harness suite passing gave false confidence. A real production bug (format mismatch) was hidden for months.
4. Autonomous agents should NEVER add such bypasses. If the harness requires a bypass, the harness is bad. Fix the harness.

**What needs to happen:**
1. Remove the harnessMode bypass from RS sendDispositionEvent()
2. Make the harness simulate the production PubSub path instead (PubSub emulator, or a test PubSub topic with a push subscription to LLC's local endpoint)
3. Until the harness is fixed, any harness test results for the disposition pipeline are suspect
4. This is a separate workstream from SPV-85. Track as its own ticket.

**Rule for autonomous agents:** If you encounter a situation where the harness cannot verify something without a service code bypass, STOP. Do not commit the bypass. Write a report in this document under "Future Work" and raise it as the first caveat at session end.

---

## PROBLEM: Cloud Scheduler Restricts Tick to Weekdays (TO-DO)

**Status:** Open. Architecture question for Gab.

**The problem:** Cloud Scheduler cron is `* 8-19 * * 1-5` (weekdays 8AM-7PM ET only). But partners can configure operatingDays that include weekends. The tick never fires on weekends, so weekend-configured partners never get called.

**Separation of concerns:** Cloud Scheduler should be a delivery mechanism (fire the tick), not a business rule enforcer (when to call). The SchedulingWindowService.isWithinOperatingWindow(config) already checks partner-level operating days and hours. The tick should fire 24/7 and let partner config decide.

**Recommended fix:** Change cron to `* * * * *` (every minute, 24/7) or at minimum `* 0-23 * * *`. The partner config and SchedulingWindowService handle the rest. Note: ADR-021 means partner-level scheduling fields are not exposed by EQS, so YAML defaults apply (hoursStart=8, hoursEnd=19, excludeWeekends=true).

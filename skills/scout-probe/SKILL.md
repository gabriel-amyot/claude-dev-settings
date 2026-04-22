---
name: scout-probe
description: Generates single-record probe scripts to validate pipeline operations. Use when an API claims success but state doesn't change, or when debugging multi-service mutations end-to-end.
---

# Scout Probe

## Purpose

A scout probe is a controlled, single-record experiment that validates whether a pipeline operation (mutation, reconciliation, ingestion, etc.) actually works end-to-end in a target environment. It is not a unit test. It is not a smoke test. It is a precision instrument: extract one real record, run the operation, verify the outcome through the same read path consumers use, emit a PASS/FAIL verdict with evidence.

The core discipline this skill enforces:

1. **Validate downstream, not the mutation response.** An HTTP 200 from an API means the request was accepted. It does not mean the data landed. Always verify state through the read path (EQS via Gateway, LLS direct query, Datastore entity, etc.) after the operation completes.
2. **Micro-test before full pipeline runs.** One record costs five minutes. Running a full reconciliation against 35,000 records on a broken pipeline costs two hours and leaves a mess. Always scout first.

---

## When to Use

Invoke this skill when any of the following are true:

- A mutation API returns success but the dashboard/UI shows no change.
- A reconciliation or ingestion pipeline claims N records processed but the read path shows no updates.
- You are about to trigger a bulk operation (batch reconcile, mass update, pipeline replay) and want to verify the operation is wired correctly before running it at scale.
- You are debugging a multi-service flow (e.g., LLS → ERS → EQS, Retell → reconciler → Lead entity) and need to isolate which hop is broken.
- You need a controlled experiment against a live environment (dev or UAT) without risk of polluting production data.

Do not use a scout probe when:
- The issue is clearly a local/R&D auth problem not related to data flow.
- You are writing unit tests (use the test harness instead).
- The operation has no read path to verify against.

---

## Skill Steps

### Step 1: Identify the operation under test

Before writing any code, define the three components of the probe:

1. **Source system** — where real data lives (Retell API, ERS Datastore, LLS, etc.)
2. **Target system** — the service receiving the mutation or ingestion (LLS, ERS, EQS, retell-service, etc.)
3. **Read path** — how consumers actually observe the result (EQS GraphQL via Gateway, LLS REST, Datastore entity read, etc.)

Write these down explicitly before proceeding. If you cannot identify the read path, stop and find it before continuing. Verifying through a shortcut path (e.g., direct Datastore read instead of EQS) will give a false positive: the data may be in Datastore but fail to materialize in the view the UI uses.

### Step 2: Extract one real record from the source

Pull a single real record from the source system. Do not synthesize data. Real records exercise the same code paths as production:

- Real identifiers (phone numbers, UUIDs, call IDs) match existing entities.
- Real payloads expose serialization issues that synthetic data masks.
- Real records test the full mapping/transformation pipeline.

Capture the record's key identifiers (phone, UUID, interactionId, etc.) as variables. You will need them for baseline verification and post-operation comparison.

### Step 3: Create the scout entity in the target system (if needed)

For reconciliation or update operations, a target entity must exist. Create one with minimum required fields using the record's identifiers from Step 2. This is the entity the operation will act on.

Log the entity's key identifier. If the target system assigns its own ID (e.g., Datastore auto-ID), capture it now.

For ingestion operations where the operation itself creates the entity, skip this step. The operation IS entity creation.

### Step 4: Establish baseline state

Before executing the operation, capture the current state of the target entity through the read path. This is your "before" snapshot.

Query through the exact same path the UI or consumers use:

- If consumers read through EQS → Gateway GraphQL, query EQS via the Gateway.
- If consumers read through LLS REST, query LLS directly.
- Do not read Datastore directly unless the read path IS Datastore.

If the read path has a materialization delay (EQS poll propagation, MV rebuild, etc.), retry with backoff until you get a stable baseline. A missing entity is a valid baseline (capture it as `null` or `not_found`).

### Step 5: Execute the operation under test

Run the operation for the single scout record only:

- If the operation is a REST call, make the request with the scout record's identifiers.
- If the operation is a batch job with a filter parameter, scope it to the scout record.
- If the operation has no scoping capability, run it — one record in a clean environment is harmless.

Capture the full response: HTTP status, body, any error messages. This is evidence but NOT your verdict. The verdict comes from Step 6.

### Step 6: Poll-retry for materialization

Many pipelines involve async propagation. EQS materializes views on a poll cycle. PubSub delivery has latency. Scheduled jobs run on intervals.

After executing the operation, poll the read path with exponential backoff until one of:

- The state has changed (expected update visible).
- A timeout is reached (default: 60 seconds with 5-second intervals, adjust per pipeline).

Do not declare failure on the first poll. Log each retry attempt.

### Step 7: Compare before/after and emit verdict

Compare the baseline state (Step 4) against the final state (Step 6 last poll):

- **PASS** — the expected field(s) changed to the expected value(s).
- **FAIL** — the state did not change, or changed to an unexpected value.

Emit a structured JSON verdict block:

```json
{
  "verdict": "PASS|FAIL",
  "operation": "description of what was tested",
  "record_id": "identifier of the scout record",
  "baseline": { ...before snapshot... },
  "final": { ...after snapshot... },
  "diff": { ...changed fields... },
  "evidence": {
    "operation_response_status": 200,
    "operation_response_body": "...",
    "polls": 3,
    "elapsed_seconds": 12
  }
}
```

Print the verdict block to stdout at the end of the script. This makes it greppable and parseable by downstream tools.

### Step 8: Leave the scout entity in place

Do not delete the scout entity after the probe. One record in dev/UAT is harmless. Deletion adds complexity (another operation that could fail) and removes evidence if you need to investigate further. Document the record's identifier in the verdict output so it can be found and cleaned up manually if needed.

---

## Using the Template

The bundled template lives at `templates/scout-probe.py.template`. Copy it to the ticket's tools directory and fill in the `# === CONFIGURE: {section} ===` placeholders.

```bash
cp ~/.claude/skills/scout-probe/templates/scout-probe.py.template \
   tickets/{TICKET-ID}/tools/scout-{operation}-probe.py
```

Then fill in:
- `SOURCE_SYSTEM` — API base URL or client import for the source.
- `TARGET_SYSTEM` — API base URL or client import for the target.
- `READ_PATH_URL` — Full URL (including Gateway if applicable) for the read path query.
- The extraction query in `extract_source_record()`.
- The entity creation payload in `create_scout_entity()`.
- The baseline query in `read_baseline()`.
- The operation call in `execute_operation()`.
- The state comparison logic in `compare_states()`.

Run with:

```bash
python tickets/{TICKET-ID}/tools/scout-{operation}-probe.py --env dev
python tickets/{TICKET-ID}/tools/scout-{operation}-probe.py --env dev --dry-run
python tickets/{TICKET-ID}/tools/scout-{operation}-probe.py --env dev --verbose
```

---

## Auth Pattern

All probe scripts source `auth-helper.sh` to self-provision tokens. Never require manual token environment variables. The script must be runnable autonomously without asking the user for credentials.

```python
import subprocess
result = subprocess.run(
    ["bash", "-c", "source ~/.claude/scripts/auth-helper.sh && echo $TOKEN"],
    capture_output=True, text=True
)
token = result.stdout.strip()
```

Adjust the token variable name to match what `auth-helper.sh` exports for the target environment.

---

## Existing Instances

The first scout probe was written during SPV-92 reconciliation debugging:

- `tickets/SPV-92/tools/scout-reconciliation-probe.py` — Retell → LLS reconciliation probe. Tests whether `retell-service` reconciliation actually updates the Lead entity in LLS and materializes in EQS.

When generalizing to a new operation, read that file as a reference implementation before filling in the template.

---

## Common Failure Modes

**False positive from wrong read path.** You read Datastore directly and see the entity updated, but EQS still shows stale data. The materialization pipeline is broken between Datastore and EQS. Always verify through the read path consumers use.

**Poll timeout too short.** EQS poll cycle can be 10-30 seconds in dev. If you poll for 15 seconds and stop, you may declare FAIL on a PASS. Set timeout to at least 90 seconds for EQS-materialized views.

**Scout entity missing required fields.** The operation may silently skip records with incomplete entities. When creating the scout entity, include ALL fields the operation checks (status, partnerId, phone, etc.). Check the operation's source code for filter conditions before creating the entity.

**Operation filters out the scout record.** Some reconciliation jobs filter by status, date range, or partner. Verify the scout record's attributes satisfy the operation's filter before running it. If the operation skips the record, you learn nothing.

**Auth token scoped to wrong tenant.** In multi-tenant systems (Supervisr), the token's tenant determines which leads are visible. Verify you're using a token scoped to the same tenant as the scout record's partner.

---

## Reference

- Feedback: `feedback_micro_test_before_full_pipeline.md` — One record saves two hours.
- Feedback: `feedback_validate_downstream_not_response.md` — API success != data landed.
- Existing probe: `tickets/SPV-92/tools/scout-reconciliation-probe.py`
- Template: `~/.claude/skills/scout-probe/templates/scout-probe.py.template`

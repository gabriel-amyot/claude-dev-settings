# Scout Probe Skill — Functional Test Report

**Date:** 2026-04-21
**Tester:** Claude Code (dry-run assessment)
**Skill:** `scout-probe`
**Skill file:** `~/.claude/skills/scout-probe/SKILL.md`
**Template:** `~/.claude/skills/scout-probe/templates/scout-probe.py.template`
**Reference implementation:** `tickets/SPV/SPV-92/tools/scout-reconciliation-probe.py`

---

## Scenario

**"Generate probe for EQS sort validation"** — verifying that EQS returns leads sorted by `createdAt` descending after a pipeline operation (e.g., after a batch reconciliation or ingestion creates new leads).

**Input concern:** After a pipeline completes, EQS `LeadReportResults` should return leads with the most recently created appearing first (i.e., sorted by `createdAt` DESC). There is suspicion that sort order is not guaranteed or may be broken.

---

## Template Assessment

### Completeness

The template is structurally complete. All phases of the skill's 8-step methodology are represented:

| Phase | Template Section | Present? |
|---|---|---|
| Auth self-provisioning | `get_token()` | Yes |
| Source extraction | `extract_source_record()` | Yes (stub with examples) |
| Scout entity creation | `create_scout_entity()` | Yes (stub) |
| Baseline state read | `read_baseline()` / `_query_read_path()` | Yes (with GraphQL and REST options) |
| Operation execution | `execute_operation()` | Yes (stub) |
| Poll-retry with backoff | `poll_for_state_change()` | Yes (full implementation) |
| Verdict comparison | `compare_states()` / `is_pass()` | Yes |
| Structured JSON verdict output | `main()` verdict block | Yes |

### Placeholder Marking

All configure sections are explicitly marked with `# === CONFIGURE: {section} ===` delimiters. The eight configure points are:

1. `ENV_CONFIG` — base URLs for dev/uat
2. `AUTH_TOKEN_ENV_VAR` — the auth-helper.sh export variable name
3. Source extraction endpoint and response parsing
4. Entity creation payload and endpoint
5. Read path query implementation (GraphQL option A / REST option B both stubbed)
6. Change detection field in `poll_for_state_change()`
7. PASS condition field and expected value in `is_pass()`
8. Operation request payload and endpoint in `execute_operation()`

All placeholders use a consistent `{UPPER_SNAKE_CASE}` convention in braces, making them visually distinct and grep-able.

### Coverage

- **Auth:** Covered. `get_token()` sources `auth-helper.sh`, self-provisions, fails fast with stderr message, respects the "scripts must self-provision auth tokens" rule.
- **Polling:** Covered. `POLL_TIMEOUT_SECONDS = 90` is pre-set to the correct value for EQS materialization (skill doc warns that EQS can take 10–30 seconds in dev; 90 seconds provides adequate headroom). Interval is 5 seconds.
- **Verdict:** Covered. Structured JSON block includes `verdict`, `operation`, `record_identifiers`, `baseline`, `final`, `diff`, `evidence` (with poll count and elapsed seconds). Matches the exact schema specified in SKILL.md Step 7.
- **Dry-run and verbose flags:** Both present and wired through all steps.
- **Scout entity left in place:** Yes, explicit `note` field in verdict output says so.

### Gap: `_query_read_path` raises NotImplementedError

The template's `_query_read_path()` function raises `NotImplementedError` by design. This is correct behavior — it forces the filler to implement the read path explicitly rather than silently no-oping. However it means the script will crash at runtime if the section is not filled in. This is intentional and documented; it is not a defect.

---

## Skill Instructions Clarity

### Would an agent following the skill steps produce a working probe?

**Mostly yes, with one gap.**

Steps 1–3 (identify operation, extract source record, create scout entity) are clear and actionable. Steps 4–7 map directly to template sections. The configure markers make it easy to scan for what needs filling.

**The gap:** For the EQS sort validation scenario specifically, Steps 2 and 3 of SKILL.md assume there is a *mutation* to run and a *target entity* to create. EQS sort validation is a **read-path correctness** probe — not a mutation probe. The scenario is:

1. No "source system" to extract a real record from (or the source is EQS itself)
2. No "target entity" to create (leads already exist)
3. No single operation to fire — the test is "does EQS return results in the correct order?"
4. The "before" and "after" are both EQS query results; the "operation" is either a no-op or an ingestion that creates a lead with a known `createdAt`

The skill's steps and template are optimized for mutation+materialization probes (Retell → LLS → EQS). For a pure read-path ordering probe, an agent following the steps verbatim would get confused at Step 3 ("create scout entity in target") because there is nothing to create — or would misidentify the target system.

The skill does not address this probe type in its "When to Use" section. An agent reading the skill would need to adapt:

- Skip `create_scout_entity()` (return empty dict)
- Treat `execute_operation()` as the second EQS query (the "after" sort check)
- Redefine "baseline" as the initial EQS result set (first N items, capturing their `createdAt` order)
- Define "changed" as: the results are ordered `createdAt DESC` (or not)

The template accommodates this adaptation — `create_scout_entity()` has a documented skip path, and `compare_states()` / `is_pass()` are fully configurable. But the skill's narrative does not guide the agent to make this adaptation. An agent following SKILL.md literally would likely create an unnecessary lead and test mutation side-effects rather than sort order.

---

## Output Quality: Filled Template for EQS Sort Validation

Below is an assessment of what the filled template would look like for this scenario, without actually running it.

### What gets filled in

**ENV_CONFIG:**
```python
"dev": {
    "gateway_url": "https://run-usce1-gateway-service-uqwv5h3wnq-uc.a.run.app/graphql",
    # source/target/read_path all point to gateway for a read-only probe
}
```

**Auth token variable:** `AUTH0_TOKEN` (from auth-helper.sh, as used in the reference implementation)

**`extract_source_record()`:** For sort validation, there is no source system to extract from. An agent would likely skip this or query EQS itself for an initial snapshot of the first page of results.

**`create_scout_entity()`:** Skipped (return empty dict). The probe does not mutate.

**`_query_read_path()`:** This is the core of the probe. It executes a GraphQL `LeadReportResults` query via the Gateway and captures the `createdAt` values of the first N results in their returned order.

**`execute_operation()`:** For a post-pipeline sort check, this would either be a no-op (checking order after an already-completed pipeline run) or would trigger a minimal ingestion (create one lead, then verify it appears first in subsequent sorted results). The template accommodates both.

**`poll_for_state_change()`:** Change detection logic would compare `results[0].createdAt >= results[1].createdAt >= ...` rather than a single field flip. This is a non-trivial adaptation — the template's single-field change detection pattern in `poll_for_state_change()` does not directly map to an ordering assertion.

**`is_pass()`:** PASS condition would be: `all(results[i].createdAt >= results[i+1].createdAt for i in range(len(results)-1))`. This replaces the single-field equality check in the template.

### Quality of the generated output

The filled template would produce a runnable script. The verdict JSON block, auth wiring, dry-run flag, verbose flag, and poll loop are all mechanical fills that work correctly for this scenario. The sort-assertion logic requires the agent to deviate from the template's single-field change detection model, but the template's structure does not block this deviation — it just doesn't guide it.

**The output would be approximately 80% correct** for this scenario: auth, structure, verdict format, and CLI flags are solid. The 20% gap is the sort-specific assertion logic in `poll_for_state_change()` and `is_pass()`, which the agent must derive from first principles rather than template guidance.

---

## Reference Implementation Comparison

The SPV-92 reference (`scout-reconciliation-probe.py`) deviates from the template in three ways worth noting:

1. **Auth self-provisioning is incomplete.** It calls `get_env_tokens()` which reads from environment variables and fails if they are missing — it does not source `auth-helper.sh` autonomously. This contradicts the "scripts must self-provision auth tokens" rule codified in SKILL.md's Auth Pattern section and in MEMORY.md. The template is correct; the reference is the older pattern.

2. **No structured JSON verdict block.** The reference prints a human-readable table and exits. The template produces a machine-parseable JSON verdict block. The template is the superior pattern for downstream tool integration.

3. **Poll timeout is shorter.** Reference uses 30 seconds for baseline materialization (6 × 5s polls). Template defaults to 90 seconds. Template is correct per the SKILL.md "Common Failure Modes" warning about EQS poll cycle length.

These deviations are documented discrepancies between an older hand-written probe and the formalized template. They do not affect the functional test grade.

---

## Grade

**PARTIAL**

### Rationale

The skill and template are well-designed for their primary use case: mutation+materialization probes where a real source record is extracted, a scout entity is created in a target system, an operation is executed, and EQS materialization is polled. For that class of probe, the template is complete, placeholder marking is thorough, auth and polling patterns are correct, and the verdict format matches the spec.

The PARTIAL grade reflects a specific gap: the skill does not guide an agent through adapting the template for **read-path correctness probes** (ordering, pagination, filtering behavior) where there is no mutation to execute and no entity to create. An EQS sort validation probe is this type. An agent following the skill steps without modification would produce a probe that tests mutation side-effects rather than sort order. The template accommodates the adaptation but the skill instructions do not describe it.

### To upgrade to PASS

Add a section to SKILL.md covering read-path correctness probes as a recognized probe variant:

```markdown
### Read-Path Correctness Probes

When the operation under test is a query behavior (sort order, pagination, filter
correctness) rather than a mutation:

- Skip Step 3 (create_scout_entity — return empty dict, no entity needed).
- Treat `execute_operation()` as a second read-path query (the "after" snapshot).
- Redefine "baseline" as the initial query result set.
- Redefine "changed" as the ordering/filter invariant you are asserting.
- In `is_pass()`, replace the single-field equality check with the ordering assertion.
- Polling is still useful if the query behavior depends on eventual consistency.
```

This addition would make the skill complete for the EQS sort validation scenario and similar read-path probes.

---

*Report generated: 2026-04-21. Dry-run only. No live environment queries executed.*

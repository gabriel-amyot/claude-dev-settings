---
name: feedback-to-spec
description: "Transform visual feedback (screenshots + narration) into precise, structured specifications, then autonomously update tickets and delegate implementation. Use this skill whenever the user is reviewing a UI, giving feedback on what they see, narrating issues while looking at screenshots, triaging UX problems, processing visual review notes, or saying things like 'here is what I see', 'look at this', 'this is wrong', 'let me show you what happened'. Also triggers on: 'feedback', 'ux feedback', 'triage feedback', 'review screenshots', 'feedback triage', 'process feedback', 'process my notes', 'turn this into specs'. This skill is the bridge between a stakeholder's visual observations and the engineering pipeline. If someone is looking at a screen and talking about what needs to change, this is the skill."
nav:
  bay: plan
  when: "Transform visual feedback (screenshots + narration) into structured specs and tickets."
  when_not: "No visual feedback. Text-only requirements (use /create-tickets)."
  personas: [leo]
---

# Feedback to Spec

Transforms visual feedback (screenshots, screen observations, natural language narration) into structured specifications, then drives ticket updates and implementation through BMAD agents.

The skill has two distinct modes with a hard gate between them:

- **Phase 1 (Interactive):** You and the user collaborate to extract, structure, and confirm specifications. Nothing leaves this phase until the user says the specs are right.
- **Phase 2 (Autonomous):** Once specs are locked, the pipeline runs without intervention: diff against existing tickets, create/update Jira, delegate implementation, review, test.

**Usage:** `/feedback-to-spec [epic-key]`

**Examples:**
```
/feedback-to-spec KTP-130           # Process feedback for proximity map epic
/feedback-to-spec                    # Interactive: ask for epic context
```

---

## Inputs

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| Epic key | Yes (can ask) | None | Parent epic for all findings (e.g., KTP-130) |
| Screenshots | Yes | None | File paths or folder. Read with the Read tool (multimodal). |
| Narration | Yes | None | User's natural language description of what they see and what should change |
| Frontend repo | No | `~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal` | For code tracing |
| Backend repo | No | None | For full-stack traces when relevant |

---

## Phase 1: Interactive Specification

This phase is a conversation. The user narrates, you extract. Mary (Business Analyst) helps structure the extraction. Leo (Spec Coach) validates the specs. The user confirms before anything goes autonomous.

### Step 1: Ingest

Read every screenshot the user provides using the Read tool. For each one:

1. **Observe** what the screenshot shows (UI state, data, layout, interactions visible)
2. **Listen** to the user's narration about that screenshot. Their words are the primary signal. Pay attention to:
   - What they say is wrong ("this shouldn't be here", "this is too wide")
   - What they expect instead ("it should scroll", "the number should be X")
   - Implied requirements they don't state explicitly (if they say "this panel is too wide", the implicit spec is a max-width constraint)
   - Severity cues ("this is a blocker" vs "nice to have" vs "when we get to it")
3. **Extract** each discrete observation as a raw finding:

```
FINDING-N:
  screenshot: <file reference>
  quote: "<user's exact words>"
  observation: <what the screenshot shows>
  issue: <what's wrong, in one sentence>
  expected: <what should happen instead>
  category: BUG | UX | DATA | LAYOUT | PERFORMANCE | MISSING_FEATURE
  severity: P0_BLOCKER | P1_HIGH | P2_MEDIUM | P3_LOW
```

Write findings to `tickets/{PREFIX}/{EPIC}/reports/drafts/feedback-extraction-{date}.md` as you go.

**Discipline: findings = user observations, not code archaeology.**
A finding is something the user said or pointed at. Technical sub-causes discovered during code trace belong in `code_trace.notes`, not as separate findings.

- "This panel is way too wide and I can't scroll the filters" = two findings (panel width, scroll behavior). The user described two distinct problems.
- "These circles look broken" = one finding, even if the code trace reveals 3 contributing factors (icon load, minZoom, text-size). Those are root cause details within the finding, not separate findings.
- **Counting guard:** If the user described N distinct issues, produce N findings (±1). If your finding count exceeds the user's observation count by 2x or more, you're confusing code details with user feedback. Collapse back.
- Don't merge distinct issues. Don't add issues the user didn't mention.

**Severity comes from the user's tone, not your technical assessment:**
- P0_BLOCKER = user said "blocker", "can't ship", "urgent", "this breaks everything"
- P1_HIGH = user said "problem", "wrong", "needs to change", "look at this"
- P2_MEDIUM = user said "could be better", "polish", "when we get to it"
- P3_LOW = user implied but didn't state explicitly, or said "minor", "nitpick"

If you think the technical severity is higher than the user's tone suggests, note it in `code_trace.notes` as a `[SEVERITY_NOTE]` but keep the finding at the user's assigned level. The confirmation loop (Step 4) is where the user can upgrade.

### Step 2: Code Trace

For each finding, grep the frontend repo (and backend if relevant) for component names, CSS classes, or data patterns visible in the screenshot. Pin the responsible file:line. Classify as `FRONTEND_ONLY`, `FULL_STACK`, `DATA_ONLY`, or `CONFIG`.

Attach to each finding: `code_trace: { file, lines, component, fix_scope, notes }`. If you can't find the code, mark as `TRACE_PENDING`. Never fabricate paths.

Technical sub-causes discovered here (e.g., "minZoom not enforced" or "helper function exists but isn't imported") go in `notes`, not as new findings.

### Step 3: Specification Draft (with Mary's Discipline Check)

Before drafting SBEs, run Mary's audit (Business Analyst lens). Mary does NOT write the SBEs. She challenges the extraction:

1. **For each finding, ask:** "Did the user actually say this, or did the agent infer it from the screenshot?" If inferred, demote to a `[NOTED]` annotation on the nearest real finding. Do not promote it to its own SBE.
2. **Count check:** Compare finding count to the number of distinct issues the user described. If findings > observations × 1.5, collapse the extras into `code_trace.notes`.
3. **Business intent check:** For each finding, can you state in one sentence what the user wants to change from a user's perspective (not a developer's)? If you can only describe the technical fix, the finding is missing its business rationale.

After Mary's audit, draft SBEs from the surviving findings. For each finding (or group of related findings), write an SBE:

```markdown
### SBE-N: {descriptive title}

**Context:** {what the user was doing when they noticed this}

GIVEN the user is viewing {specific page/panel/component}
  AND {relevant data state or precondition}

WHEN {the trigger — what action or state exposes the issue}
THEN {the observable outcome that SHOULD happen}
  AND {any secondary expectations}

**Current behavior:** {what actually happens now — from the screenshot}
**Root cause:** {from code trace}
**Fix scope:** {FRONTEND_ONLY | FULL_STACK | DATA_ONLY | CONFIG}
```

Write the full SBE catalog to `tickets/{PREFIX}/{EPIC}/reports/drafts/sbe-extraction-{date}.md`.

Guidelines for writing SBEs:
- Each SBE maps to exactly one testable behavior change
- Use concrete values from the screenshot, not placeholders ("panel width should not exceed 320px", not "panel should be appropriately sized")
- If the user said something ambiguous, flag it with a `[CLARIFY]` tag and propose a specific interpretation
- Group related findings into a single SBE only if they share the same root cause AND fix
- **Proportionality:** Match output volume to input complexity. Single focused observation = 1 SBE (with root cause details in notes). Multi-issue burst = 1 SBE per finding. If your SBE count exceeds your finding count by more than 50%, you're over-decomposing. Collapse technical sub-causes back into the parent SBE's notes.

### Step 4: Confirmation Loop (Leo's Gate)

This is the critical gate. Present the complete SBE catalog to the user with Leo's analytical framing.

For each SBE, present:

> **SBE-N: {title}**
> 
> **What you said:** "{user's original words}"
> **What I understood:** {the spec in plain language}
> **What I suggest:** {the Given/When/Then, plus any edge cases Leo would flag}
> 
> **Questions (if any):**
> - {specific question about threshold, behavior, scope}

Then ask the user to confirm, correct, or expand each SBE. Use `AskUserQuestion` if needed.

**Rules for this gate:**
- Never assume confirmation. Wait for explicit "yes", "correct", "confirmed", or equivalent.
- If the user corrects something, update the SBE and re-present the corrected version.
- If the user adds new observations, loop back to Step 1 for those.
- If the user says "that's everything" or "looks good", the gate is passed.

Once confirmed, write the locked specs to `tickets/{PREFIX}/{EPIC}/reports/specs/confirmed-sbes-{date}.md` with a header noting the confirmation timestamp.

### Step 4b: Persist Specs to agent-os

Confirmed SBEs are durable specifications, not just session artifacts. Persist them to the frontend repo's agent-os folder so future development sessions and agents can reference them:

1. Write each confirmed SBE to `{frontend_repo}/agent-os/sbe/sbe-{epic}-{N}-{slug}.md` using the standard SBE format (Given/When/Then with metadata header).
2. If `agent-os/sbe/` doesn't exist, create it with an `INDEX.md`.
3. Update `agent-os/sbe/INDEX.md` with the new entries.
4. If a backend repo is involved (FULL_STACK scope), write relevant SBEs to that repo's `agent-os/sbe/` as well.

This ensures specs survive session boundaries and are discoverable by any agent working in the repo.

### Step 4c: Handoff Decision

Before leaving Phase 1, the user chooses how far the pipeline should go. Present these four modes:

| Mode | Ticket impact | Implementation | When to use |
|------|--------------|----------------|-------------|
| **Full auto** | Create/update tickets now, then implement | Yes | User reviewed specs, trusts the plan, wants to walk away |
| **Review first** | Show ticket plan, wait for selective approval | Yes (after approval) | Default. User wants to see sprint impact before committing |
| **Comment only** | Add informational comments to tickets, no AC changes | No | Scope is sensitive. Specs are recorded, tickets get a heads-up, but nothing changes structurally. Last resort. |
| **Park it** | No Jira interaction at all | No | Not the right time. Specs are saved locally + agent-os. Resume later. |

Ask the user to pick a mode. If they don't specify, default to **Review first**.

The selected mode determines how Phase 2 and Phase 3 execute. Store the selection in the confirmed-sbes file header.

**Phase 1 is complete. The user's intent is now crystal clear.**

---

## Phase 2: Diff and Ticket Planning (Autonomous Research, Interactive Decision)

Read `references/phase2-autonomous.md` for the detailed delegation protocol.

### Step 5: Requirement Diff (autonomous)

Fetch existing ticket ACs from Jira (via `/jira` skill) for all tickets under the epic. Compare each confirmed SBE against existing ACs:

| Result | Action |
|--------|--------|
| SBE matches existing AC exactly | Skip. Note as "already covered." |
| SBE partially covered by existing AC | Flag the gap. Prepare AC amendment. |
| SBE is entirely new | Prepare new ticket creation. |
| SBE conflicts with existing AC | Flag as CONFLICT for user review. |

Write the diff report to `tickets/{PREFIX}/{EPIC}/reports/drafts/requirement-diff-{date}.md`.

### Step 6: Ticket Operations

Behavior depends on the mode selected in Step 4c:

#### Mode: Park it
Skip this step entirely. Specs are persisted (Step 4 + 4b). Write the diff report with "PARKED" status. Skip to Step 10 (Report).

#### Mode: Comment only
For each SBE that maps to an existing ticket, post an **informational comment** (no AC changes):

```
[automated] — Message from Leo, Gab's Specification Specialist

h3. Spec Note: {SBE title}

Visual feedback review on {date} identified a related specification.
This comment is informational only — no AC changes are being made.

*Observation:* {one-line summary of what was found}
*Proposed spec:* {the Given/When/Then, collapsed}
*Persisted to:* agent-os/sbe/sbe-{epic}-{N}-{slug}.md

When this ticket is next in scope, incorporate the above into the AC.
```

Post via `/post-comment`. For SBEs with no matching ticket, note them in the report as "unattached specs" but do NOT create tickets. Skip to Step 10 (Report).

#### Mode: Full auto
Execute all ticket operations without further interaction:
- AC updates: draft comment, post via `/post-comment` with Leo's voice
- New tickets: create via `/create-tickets`, scaffold via `/ticket-init`
- Conflicts: surface to user via `AskUserQuestion` (conflicts are always interactive, even in full auto)

Proceed to Phase 3.

#### Mode: Review first (default)
Present the full ticket operation plan and wait for approval.

| # | SBE | Action | Target Ticket | Impact |
|---|-----|--------|---------------|--------|
| 1 | SBE-1 | UPDATE AC | KTP-617 | Adds scroll behavior to existing UX ticket |
| 2 | SBE-3 | NEW TICKET | (to create) | New story: store count data binding |
| 3 | SBE-5 | CONFLICT | KTP-610 | Contradicts existing filter behavior AC |

For each proposed action, show:
- What changes (AC text, ticket summary)
- Sprint impact: does this add scope to the current sprint? Could it be deferred?
- Dependencies: does this block or unblock other tickets?

**Wait for the user to:**
- Approve all (`go ahead`, `approve all`)
- Approve selectively (`do 1 and 2, skip 3`, `defer the new tickets`)
- Switch mode (`just comment`, `park it` — user can downgrade at this point)

Only after explicit approval, execute the approved operations:
- For AC updates: draft comment, post via `/post-comment` with Leo's voice: `[automated] — Message from Leo, Gab's Specification Specialist`
- For new tickets: create via `/create-tickets`, scaffold via `/ticket-init`
- For conflicts: resolve per user's direction

Proceed to Phase 3 with only the approved tickets.

---

## Phase 3: Implementation (Autonomous)

Everything below runs without intervention, but only for tickets the user approved in Step 6.

### Step 7: Implementation Delegation

Dispatch to BMAD agents via subagents. Read `references/phase2-autonomous.md` for the full delegation matrix.

Summary of who does what:
- **Amelia** (Dev): Implementation plan, code changes, unit tests
- **Winston** (Architect): Architecture review if fix_scope is FULL_STACK or introduces new patterns
- **Quinn** (QA): Test plan, Playwright E2E tests, regression check

Each agent loads their persona from the actual file (see persona paths in `references/phase2-autonomous.md`). Never improvise personas.

### Step 8: Adversarial Review

Run `/challenge` on all code changes. Verify:
- Every confirmed SBE from Phase 1 is addressed by a code change
- No code change introduces behavior the user didn't ask for
- No existing functionality is broken by the changes

### Step 9: Test Suite Update

For each SBE, ensure test coverage exists at every relevant layer:
- **Unit tests** for logic changes
- **Integration tests** for data flow changes
- **Playwright E2E tests** for visual/interaction changes (via `/klever-test`)

### Step 10: Report

Write the final report to `tickets/{PREFIX}/{EPIC}/reports/feedback-triage-report-{date}.md`:

```markdown
# Feedback Triage Report — {date}

## Input
- Screenshots processed: N
- Narration segments: N

## Extraction
- Raw findings: N
- SBEs confirmed: N (list with titles)
- Code traces: N successful, N pending

## Ticket Operations
- Existing tickets updated: [list with keys]
- New tickets created: [list with keys]
- Conflicts surfaced: [list if any]

## Implementation
- Code changes: [summary per ticket]
- Tests added: [count by type]
- Adversarial findings: [count, with severity breakdown]

## Open Items
- [anything unresolved, pending user input, or deferred]
```

---

## Integration with Existing Skills

This skill calls other skills internally. It does NOT replace them.

| Skill | When called | Purpose |
|-------|-------------|---------|
| `/jira` | Step 5, 6 | Fetch tickets, post comments |
| `/post-comment` | Step 6 | All Jira comment posting |
| `/create-tickets` | Step 6 | New ticket creation with Leo ACs |
| `/ticket-init` | Step 6 | Local folder scaffolding |
| `/klever-test` | Step 9 | Playwright E2E test execution |
| `/challenge` | Step 8 | Adversarial review of changes |

---

## Important Constraints

1. **Screenshots are first-class.** The Read tool can view images. Always read every screenshot before extracting findings.
2. **User's words are primary.** Don't invent issues the user didn't mention. Don't downgrade severity the user assigned. Transform their words into specs, don't reinterpret them.
3. **The gate is sacred.** Phase 2 never starts until Phase 1 confirmation is explicit. If the user wanders off or the session ends, the draft SBEs are saved but not acted on.
4. **No refactoring.** If you notice pre-existing issues during code trace, note them but do not add SBEs for them. Only the user's feedback becomes specs.
5. **Persona files are loaded, never improvised.** See `references/phase2-autonomous.md` for exact file paths.
6. **All external posts go through /post-comment.** No raw API calls to Jira, Slack, or GitHub.
7. **Reports live in the ticket tree.** All output goes to `tickets/{PREFIX}/{EPIC}/reports/`. Never to project root.

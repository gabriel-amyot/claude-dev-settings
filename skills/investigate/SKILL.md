---
name: investigate
description: "Investigation-first workflow for 'something not working.' Routes Quinn (investigate root cause) -> Amelia (fix) -> Quinn (validate). Triggers on: 'not working', 'broken', 'bug', 'something wrong', 'circles are empty', 'this isn't right', 'visual bug', 'misbehavior', 'unexpected behavior', 'fix this'. Klever org."
user_invocable: true
nav:
  bay: fix
  when: "Something isn't working. Quinn investigates root cause, Amelia fixes, Quinn validates."
  when_not: "You already know the exact fix. Forensic autopsy (use dexter agent)."
  personas: [quinn, amelia]
  org: [klever]
---

# Investigation-First Workflow

**Trigger:** Something isn't working as expected, whether during development or after deploy. Does NOT require a formal bug ticket.

**Usage:** `/investigate [description]` or `/investigate KTP-XXX`

**Full protocol:** `~/.claude/library/context/ticket-quality-standards.md` (Section: "Something Not Working")

## Trivial Fix Gate

Before starting the full workflow, apply the one-liner test:

> "Can I name the exact line and explain why it's wrong without reading any other file?"

- **YES** (typo, wrong import, config value, off-by-one visible in stack trace) → Skip to Phase 2 (Amelia fixes directly). Commit with root cause in the message.
- **NO** (especially UI rendering, visual layout, component interaction, multi-layer issues) → Full workflow below.

If uncertain, default to the full workflow. KTP-628 happened because "I know the fix" was wrong.

## Phase 1: Investigate (Quinn)

Quinn owns investigation. Before anyone touches code:

0. **Library first (KTP-939 F19).** Check the org bibliothèque (`documentation/bibliotheque/INDEX.md` + `ALIASES.md`, or `bibliotheque-librarian` query mode) for the failing system's documented behavior, topology, and known gotchas. Carry what it establishes into the investigation; never re-derive documented mechanisms. Any probe dispatched from here carries a `Library:` line (citations or "silent").
1. **Invoke `superpowers:systematic-debugging`** — complete its Phase 1 (Root Cause Investigation) and Phase 2 (Pattern Analysis)
2. Identify the **specific** file, layer, component, or endpoint causing the issue
3. If frontend/visual: capture screenshot evidence of the current broken state
4. If a ticket exists: post investigation findings (Quinn-signed comment via `/post-comment`)

**Rules:**
- No guessing. No "it's probably X." Find the actual root cause.
- Read the code. Grep for the behavior. Trace the data flow.
- If frontend: check the component tree (which component renders the broken element?), then check the data feeding it.

## Phase 2: Fix (Amelia)

Amelia implements the fix that Quinn's investigation identified:

1. Fix **only** what Quinn identified. Do not expand scope.
2. Apply the fix directly. No proposals, no "Option A or Option B." Gabriel sees results, not menus.
3. Commit with root cause in the message: what was wrong, why, what changed.
4. Push, create MR (via `/klever-mr`), deploy.

## Phase 3: Validate (Quinn)

Quinn validates the fix on dev (or locally if dev is down):

1. **Invoke `superpowers:verification-before-completion`** before any completion claim
2. For frontend: use `/klever-test` (option #2: AC Validation) or direct browser observation
3. Capture after-fix screenshot evidence (before/after comparison)
4. If ticket exists: post validation result (Quinn-signed comment): PASS with evidence, or FAIL with what's still broken

**If FAIL** → back to Phase 1. Quinn re-investigates. The root cause was wrong or incomplete.

## Phase 4: Close

Only after Phase 3 PASS. If a ticket exists, post closing comment via `/post-comment` with:
- Root cause
- Fix reference (commit SHA + MR link)
- Before/after evidence

## Persona Boundaries

| Persona | Does | Does NOT |
|---------|------|----------|
| Quinn | Investigate root cause, validate fix, capture evidence | Write production code, propose fixes, write AC |
| Amelia | Implement the fix Quinn identified, commit, push | Investigate (Quinn's job), validate own fix, skip to fixing |
| Leo | Rewrite AC when it's wrong or ambiguous | Debug, investigate, validate, propose implementation |

Leo speaks only if the AC itself is wrong. Restating existing AC adds noise.

## Anti-Patterns (from KTP-628)

- Guessing the fix without investigation
- Posting "Fix Shipped" without Phase 3 validation
- Leo doing investigation/QA work (wrong persona)
- Proposing options instead of applying and testing
- Stopping at "needs visual verification on dev" without doing the verification

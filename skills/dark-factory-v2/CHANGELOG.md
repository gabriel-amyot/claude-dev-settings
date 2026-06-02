# Dark Factory v2 — Changelog

Every SKILL.md / workflow.js / contract change bumps the version and adds an entry.

## 0.2.0 (2026-06-02)

**Adversarial-cascade + prompt-specialist fixes; back-half restructure from verified Workflow API.**

Reviews: adversarial-cascade (Quinn + Codex-framed) and an independent prompt-engineering specialist.
API behavior verified via claude-code-guide. Full triage in `docs/review-findings-v0.1.0.md`.

Code (workflow.js):
- Null-guard every `agent()` return (skip → `HALT_AGENT_SKIPPED`).
- Enforce `status:'stuck'` halts for design, grill, implement, ship-prep (previously swallowed).
- Add missing `phase('Design')`.
- `capQaVerdict`: canonicalize `execution_verified` to string, drop dead boolean check, warn on
  unrecognised values. Add `evidenceCappedOverall` (a PASS AC with no code_ref+test_ref caps to PARTIAL).
- `preShipBlockers`: execution gate now explicitly rejects `infra_blocked`/`false`/missing, and
  requires the branch to have been pushed.
- Resume loop guard: `BLOCKED_NEEDS_HUMAN_AGAIN` instead of re-looping the concierge.
- Schema tightening: required `repos`, `ticket_folder`, `summary` (concierge); `minimum:0` on
  `criticals_open`/`ac_count`; `minLength:1` on `branch`; pattern on `execution_verified`; `notes` added
  to PHASE_SCHEMA.
- Remove unused `ticketFolder` arg; concierge now RESOLVES and returns `ticket_folder`; absolute
  contracts path (no `~`).

Structure (from verified API limits):
- Skills not callable inside a workflow agent → **Ship is code-prep only**; MR + Jira + transition move
  to the main loop. New terminal state `READY_TO_SHIP`.
- Sibling agents can't see each other's worktree → **Implement pushes the feature branch**; Review/QA/
  Ship-prep run with `isolation:'worktree'` and fetch+checkout it; Implement also writes a diff artifact.
- Single worktree owner: removed `git worktree add` from contract 4 (runtime owns it).
- No native wait → **Validate removed from the auto-run**; main loop runs it post-merge.

Contracts: all 8 updated — concierge returns `ticket_folder` + example open_question; design/grill add
reason-before-file + artifact paths; implement pushes branch + writes diff + dependent-AC stuck;
review defines `demonstrated` + severity rubric + fetch/checkout; qa adds Inputs + example row +
evidence rule; ship-prep is prep-only; validate is a post-merge main-loop step.

## 0.1.0 (2026-06-01)

Initial seed build: workflow spine + 8 backend-floor contracts + SKILL.md. Never run.

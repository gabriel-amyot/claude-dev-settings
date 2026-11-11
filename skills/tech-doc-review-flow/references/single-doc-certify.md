# Single-document certification mode

**Invocation: explicit only.** Use it when the user asks to make one how-to, runbook or architecture
doc trustworthy before a human reads it ("certify this doc", "review this doc before I look at it",
"make this guide high-confidence"). It dispatches two fresh agents, so do not start it on your own.
For a whole `agent-os/` tree, use the three-pass flow in SKILL.md instead.

Source proposal: `doc-quality-cascade` (2026-06-16, Marc-André knowledge transfer). Three guides each
had 3 to 4 verified blockers that a draft written from transcripts had shipped.

## Rule

Never hand a human a raw draft plus a findings list. The human reads a certified doc, or a doc whose
open items are marked as open.

## Steps

1. **Adversarial pass.** Dispatch a FRESH agent with only the doc and read access to the repo or data
   it describes. No build context, no transcript. It must:
   - verify every factual claim against the live source (`git show origin/<deploy-branch>:<path>`,
     `bq show`, grep), and label each claim CONFIRMED, CONTRADICTED or UNVERIFIABLE;
   - run one concrete newcomer scenario: "could someone new do <the task> with only this doc?", and
     list each step where they would stop;
   - write severity-tagged findings (BLOCKER / MAJOR / MINOR) with evidence and a concrete fix to
     `<ticket>/doc-review/<doc>-adversarial.md`.
   Use the real Codex CLI for this pass when available, with the invocation rules in SKILL.md.
2. **Address.** Apply every finding. Re-verify each fix against the source yourself. Heavy errors
   (wrong schema, wrong IDs, wrong branch) need a real source check, not trust in the reviewer. When a
   reviewer says "not in code", keep a true vendor fact and attribute it to its source; do not delete it.
3. **Certify.** Dispatch a SECOND fresh agent with only the fixed doc and the same access. It
   re-verifies that the fixes hold and that no new error came in, judges followability and structure,
   proposes surgical polish, and ends with exactly one line:
   `CERTIFICATION: SHIP` | `CERTIFICATION: SHIP WITH FIXES` | `CERTIFICATION: NO`.
4. **Apply the polish.** On `NO`, go back to step 2 once. A second `NO` goes to the human with the
   open items listed at the top of the doc.
5. **Hand over** the certified doc, with the certification line and any open UNVERIFIABLE claims named.

Rules from the tree flow still apply: style never changes meaning, and each round after the first is
told what the previous round changed.

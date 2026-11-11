# Skill Proposal: review-a-reconciled-plan
Date: 2026-08-25
Source: session `plain-lynx` — two adversarial review rounds on the dev MCP CI artifact proposal

## Trigger

An author (agent or human) returns a plan, spec, or proposal that was revised **in response to your
own review**, and asks for approval or a second pass. Phrases: "reconciled", "took the feedback and
addressed the issues", "the plan is now accurate", "do another pass".

Not for a first-pass review of an unfamiliar document — that is ordinary adversarial review. This
skill exists for the second pass, where the failure modes are specific and different.

## Scope

Global. The failure modes are properties of the revise-then-reapprove loop, not of any one org.

## Why it needs a skill

A second pass is where a reviewer is most likely to rubber-stamp. The blockers you raised are
visibly fixed, the document now uses your vocabulary, and it reads as settled. Three failure modes
recur, and all three were live in the session that produced this proposal:

1. **Phantom-approved nouns.** A loose phrase from your own round-1 review comes back promoted into
   an authoritative noun ("the release machine" → "the **approved** macOS release machine that
   already builds the trader package"). No such thing exists. It then gets selected *because* it
   reads as already approved.
2. **A resolved blocker's neighbour.** Fixing the named blocker often exposes a sibling in the same
   class that the reconciliation inherited unexamined (e.g. platform blocker resolved; build
   *reproducibility* blocker never raised, though the evidence was already in the same package).
3. **A status label ahead of the work.** A section titled "review complete" that answers a different
   category of question than its title claims, or an item marked "ready" whose gate is unlisted.

## Draft Steps

1. **Diff the ask, not just the doc.** Confirm each round-1 finding is *resolved*, not *relabelled*.
   A finding moved into a "gates" list is deferred, not fixed. Say which it is.
2. **Grep every authoritative noun.** For each phrase asserting an approved, existing, or already-in-use
   thing, search the repo, its `agent-os/` tree, and the surrounding evidence package. Treat your own
   round-1 wording as a likely source of a phantom.
3. **Re-scan the fixed blocker's class.** For each resolved blocker, ask what else in that same class
   the document still assumes. Check the sibling evidence files in the same package first — the
   counter-evidence is often already written down.
4. **Verify status labels against content.** For every "complete", "ready", "verified", read the
   section and confirm it answers the question its title claims.
5. **Check control ownership on anything being retired.** When the plan retires a mechanism, find
   which ADR/spec actually carries that control, and read the named ADR's Context for the human
   decision behind it. A decision that was a PO's needs the PO, not an ADR task.
6. **Report substantively, drop nitpicks.** A second pass under time pressure earns 4-6 findings that
   change what gets built tomorrow, not a re-litigation of round 1.

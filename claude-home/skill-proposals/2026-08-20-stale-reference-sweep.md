# Skill Proposal: stale-reference-sweep
Date: 2026-08-20
Source: session agile-pike — KTP-869, one decision required six edits found only by grep

## The gap

When a decision changes a value or a claim, nothing tells you where else that value is asserted.
Two measurements from one session:

- Approving a fifth MCP tool required editing six places (a runtime script's `EXPECTED_TOOLS`, a
  contract page, a safety-invariants table, a README heading, a test docstring, an input-schema
  golden). Found by `git grep` after a human happened to notice, not by following a link.
- A correction written into `known-limits.md` on 2026-08-19 did not reach three other copies of the
  same claim (an ADR's decision section, that ADR's index line, and a javadoc) for over a day.

Gabriel's framing: *"Spec is king in any system we build. and being confused about the spec is my
diagnosis on the chaos we had so far on those many sessions."*

This is not a search problem. `grep` works. It is a **noticing** problem: nobody knows to sweep.

## Trigger

Invoke after any decision that changes a fact likely to be asserted in more than one place:
- a count or an enumeration ("exactly four tools", a list of allowed seats)
- a version, a URL, a host, an id
- a mechanism claim ("X is derived from Y") that ADRs, contracts, javadoc and READMEs may repeat
- reversing or correcting a previously documented claim

Also as a gate before closing any ticket whose AC changed a documented behaviour.

## Scope

Global. The pattern is repo-agnostic, though the sweep list is per-repo.

## Draft steps

1. **Take the old value and the new value** from the user, plus the decision's one-line reason.
2. **Sweep, widening from literal to semantic:** `git grep` the old literal across the repo
   including `agent-os/`, `README*`, `scripts/`, `tests/` (docstrings count) and any golden fixture.
   Then sweep the *spelled-out* form (`four`, `4`, `FOUR`) and the claim's distinctive phrasing.
   Then sweep the org's `project-management` tree for ADRs, contracts and index lines repeating it.
3. **Classify each hit**, because not every copy should collapse: `SOURCE` (the one a human edits),
   `DERIVED` (should be generated or stamped, never hand-edited), `ENFORCEMENT` (a deliberate
   duplicate that catches a different reader at a different moment — keep it, update the number),
   `STALE` (a copy with no purpose — fix or delete).
4. **Report the classified list before editing.** Enforcement duplicates must survive; a proposal
   that reads "delete the duplicates" is wrong and should be rejected.
5. **Offer the derivation upgrade** where a `DERIVED` hit is hand-maintained: name one source, derive
   or stamp the rest, and add a guard that resolves against the source and cannot be skipped by a
   missing artifact. Working precedent shipped 2026-08-20 in `app-ttd-trading-mcp`:
   `agent-os/standards/versioning-and-bundle-release.md` plus
   `tests/test_version_is_single_sourced.py`.

## Open question this skill does not answer

Whether the sweep can run *without* being invoked — a mechanical trigger on commit, rather than a
human remembering to ask. That is question 4 of RCA S-8 and probably the more valuable half.

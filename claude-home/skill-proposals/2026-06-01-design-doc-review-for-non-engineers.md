# Skill Proposal: design-doc-review-for-non-engineers
Date: 2026-06-01
Source: Reviewing the Media Planning Agent Notion design doc (KTP-536)

## Trigger
User wants to review a design/architecture doc authored by a non-engineer (PM, junior dev, designer) and produce collaborative feedback that nudges toward better architecture without being heavy or adversarial. Triggers: "review this design", "give feedback on this Notion doc", "comment on this architecture", "help me respond to this design".

## Scope
Global (any org).

## Draft Steps
1. Ingest everything: the doc + the real ticket tree + the actual integration/repo reality (don't trust the doc's TBDs; verify what exists).
2. Synthesize feedback points. For each: failure mode if left as-is → alternative → trade-off → honest effort estimate. Never a hard no.
3. Adversarially vet your OWN recommendations before presenting. Cut anything not worth the effort or where you lack a real solution. Catch your own over-engineering (e.g. defaulting to BQ when Notion+validation is cheaper).
4. Open with a warm-up "you already nailed this" comment to set a collaborative tone.
5. Output as a self-contained HTML file: one card per comment, per-comment copy button (plain text), anchor location ("where to paste in Notion"), and ticket hyperlinks. No em-dashes, tight language.
6. Park follow-up tickets and AC edits as a separate proposal doc; never create tickets without explicit go-ahead.

## Notes
Related existing skill: `feedback-to-spec` (but that's for visual/screenshot feedback, not doc review). This is doc-review-specific. Consider whether to extend feedback-to-spec or stand up a sibling.

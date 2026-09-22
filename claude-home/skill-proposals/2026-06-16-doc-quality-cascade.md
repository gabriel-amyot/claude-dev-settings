# Skill Proposal: doc-quality-cascade
Date: 2026-06-16
Source: Marc-André KT — producing 3 high-confidence guides

## Trigger
About to hand a human a how-to / runbook / architecture doc that must be trustworthy and followable ("review this doc before I look at it", "make this guide high-confidence", after drafting any procedural doc). The docs analogue of `adversarial-cascade` (which is for code).

## Scope
Global / harness pattern.

## Draft Steps
1. **Adversarial pass** — dispatch a FRESH agent with ONLY the doc + repo/BQ access (no build context). It verifies every factual claim against live code/data and pressure-tests a concrete "could a newcomer actually do this task" scenario → severity-tagged findings (BLOCKER/MAJOR/MINOR) with evidence + fixes, written to disk.
2. **Address** — apply every finding, re-verifying against the source (`bq show`, `git show origin/<deploy-branch>:`, grep). Heavy errors (wrong schema/IDs) need real source checks, not trust.
3. **Tech-writer certify** — a second no-context agent re-verifies the fixes hold (no new errors), judges followability/structure, proposes surgical polish; emits a CERTIFICATION verdict (ship / with-fixes / no).
4. Apply polish; only THEN route to the human.
Rule: never hand a human a raw draft + a findings list; gate it so they review a certified doc. (This run caught 3–4 verified blockers per doc that a transcript-only draft had shipped.)

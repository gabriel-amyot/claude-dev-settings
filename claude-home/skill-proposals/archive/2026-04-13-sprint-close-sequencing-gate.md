# Skill Proposal: sprint-close sequencing gate
Date: 2026-04-13
Source: Overnight sprint-close session 2026-04-02

## Trigger
When `/sprint-close` launches adversarial review agents in parallel

## Scope
Global (skill update to existing sprint-close)

## Problem
Sprint-close skill describes correct phases (adversarial → draft → post → transition) but does not enforce ordering. The 2026-04-02 session launched adversarials in background and closed tickets before verdicts returned. 5/6 closures were premature.

## Draft Steps
1. Launch adversarial agents in FOREGROUND (not background), or if background, explicitly WAIT for all to complete
2. Collect verdicts into a summary table
3. Present table to user (or apply autonomously): PASS tickets proceed, FAIL/BLOCKED tickets are skipped
4. Only THEN draft closing comments for PASS tickets
5. Post and transition sequentially

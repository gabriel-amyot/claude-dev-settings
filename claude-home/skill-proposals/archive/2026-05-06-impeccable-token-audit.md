# Skill Proposal: impeccable-token-audit
Date: 2026-05-06
Source: Housekeeper facelift session, @theme gap discovery

## Trigger
After any `/impeccable` design session, `@theme` modification, or DESIGN.md update. Also: when user reports "looks wrong", "colors missing", "too black", or similar visual regression complaints.

## Scope
repo-local (runs against the project's DESIGN.md and compiled CSS)

## Draft Steps
1. Parse DESIGN.md frontmatter for all declared color, font, shadow, and spacing tokens
2. Run `npx vite build` (or detect build tool)
3. Grep compiled CSS output for each declared token name
4. Report: tokens found vs tokens missing, with severity (missing color = critical, missing spacing = warning)
5. If missing tokens detected, check index.css for `@theme` block presence and completeness

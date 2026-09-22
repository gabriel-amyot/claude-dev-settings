# Skill Proposal: persona-panel-to-crit
Date: 2026-07-17
Source: Session peppy-beaming-fountain — KTP-571 Planning Map PRD review

## Trigger
"get the personas to review this", "have Winston/Leo/Amelia comment on X in crit", reviewing a written artifact (PRD, architecture doc, plan) where the user wants multiple expert lenses as inline comments in a live crit session — low-noise, converged, attributed.

## Scope
global (works on any doc set; crit + BMAD personas are org-agnostic)

## Draft Steps
1. Launch crit on the target doc(s) if not already open; capture the review file path.
2. Dispatch the requested BMAD personas as PARALLEL subagents. Each prompt: read the real persona file first; review the docs with its lens; be told which facts are VERIFIED (attack proposals, not facts); return a small JSON array of `{path, lines, body}` inline comments + an explicit stance (AGREE/DISAGREE/CONDITIONAL).
3. Orchestrator dedupes/converges the returns; where personas genuinely disagree, fold it into ONE synthesis comment rather than three noisy ones.
4. Post via `crit comment "<path>:<line>" "<body>" --author "<Persona (Role)>"` (arg-list via a script to avoid shell-mangling backticks/quotes). Optionally one review-level synthesis comment.
5. Report a one-line converged verdict to the user; wait for their Finish Review.

## Gotchas to bake in
- `crit comment --help`/`--list` posts the flag AS a comment — use `crit --help` for usage.
- `crit comment` is headless (works without a running daemon).
- `crit comment --clear` wipes ALL comments (including the human's) — only use when a stray is the sole comment.
- Do NOT have subagents post to crit themselves (noise); they return JSON, orchestrator curates + posts.

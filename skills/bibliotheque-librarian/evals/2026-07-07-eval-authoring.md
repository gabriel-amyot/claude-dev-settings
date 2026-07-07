# Eval authoring note — bibliotheque-librarian (Layer B, behavioral)

**Date:** 2026-07-07
**Suite:** `evals/evals.json` (5 evals, skill_name `bibliotheque-librarian`)
**Runner:** skill-creator benchmark — see `/skill-evals` SKILL.md
**Threshold:** default pass-rate >= 0.75

## What's covered

| id | Mode | Behavior under test | Grounded in |
|----|------|--------------------|-------------|
| 1 | shelve | Classify to correct section (operations/sops for a procedure), write enriched page (frontmatter + 3-5 wikilinks + "How to apply:"), update section INDEX, do NOT touch inbox. | agent shelve protocol + curate-workflow Step 4/5 |
| 2 | shelve | Cross-cutting failure symptom also earns a root INDEX Blocked-lane row with a specific service+error symptom (not "401 error"). This is the wiki's cross-cutting cross-reference surface. | three-lane-catalog Lane 2 + "What Does NOT Get a Root INDEX Row" |
| 3 | lint | Phantom-pending reconcile: grep verbatim phrases to confirm content already on disk, flip Status to promoted (reconciled), archive it, create NO duplicate page. | agent check 8.5 + GC sweep |
| 4 | query | Progressive search, answer WITH citations, zero writes, synthesized (not a file dump). | agent query protocol |
| 5 | curate | Plan-then-execute: read inbox + entry, present placement plan before writing, route both nuggets, mark promoted + archive (Step 7b), update section/root INDEX + ALIASES/LOG. | agent curate protocol + curate-workflow Steps 1-8 |

## Fixtures

- `files/nugget-dac-branch-model.md` — operational procedure nugget (eval 1).
- `files/nugget-gateway-401.md` — Blocked-lane failure-symptom nugget (eval 2).
- `files/phantom-inbox-entry.md` — pending inbox entry whose content is already on disk; curator note points at the existing page (eval 3).
- `files/curate-inbox-entry.md` — pending entry with two nuggets + curator note (eval 5).

## Notes / caveats / contradictions surfaced

- **CATALOG.md vs root INDEX.** The Wave-3 spec said "CATALOG.md cross-ref when cross-cutting." That phrasing comes from the user-level `~/.claude/library/` Librarian Protocol in CLAUDE.md. The org wiki this skill operates on (`documentation/bibliotheque/`) has NO CATALOG.md — its cross-cutting surface is the root `INDEX.md` three-lane table. Eval 2 therefore asserts a root INDEX Blocked-lane row, which is the correct equivalent for this skill. Flagging so the two "Librarian Protocols" are not conflated.
- **Wiki-mutating evals (1, 2, 3, 5) write to the real Klever wiki** (org auto-detected from cwd `grp-beklever-com`). Run them against a scratch clone or `git stash`/reset the wiki afterward. Better still, point the runner at a throwaway wiki copy; the fixtures are self-contained enough to seed one.
- Eval 3 relies on the target page (`stack/gateway-dual-header-401.md`) actually existing on disk for the grep-verify to succeed. The prompt states this as a given; if the live wiki lacks that page the "already on disk" branch cannot fire and the eval should be run against a seeded wiki where it does.
- Eval 5 "presents a plan before writing" is the load-bearing assertion (plan-then-execute); the downstream INDEX/ALIASES/LOG updates are secondary and may partially pass.

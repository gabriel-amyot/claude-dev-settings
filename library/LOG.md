# Wiki Log — Harness Library

Chronological record of wiki operations. Append-only.

---

## 2026-05-01

- **SCHEMA** — Created SCHEMA.md, LOG.md, ALIASES.md (LLM Wiki pattern adoption)
- **ALIASES** — Seeded with 13 aliases from CATALOG.md topic cross-reference
- **REGISTRY** — Wiki already registered in WIKI_REGISTRY.yaml (self-referential)

## 2026-09-17

- **PROMOTE** — Added `context/protected-module-change-isolation.md` from the Klever bibliothèque
  curate run (inbox entry `2026-09-17-o06-map-reuse-grilling.md`, session `bold-newt`, KTP-571
  O-06, nugget 6). The nugget generalizes beyond Klever, so it was routed here instead of the
  Klever wiki: a blanket "never touch module X" guardrail expires once reuse turns symmetric, a
  diff-shape replacement rule blocks the good case, and the working form fences by packaging
  (one MR, reviewed alone, plus a visible aggregate count) plus one narrow no-internal-refactors
  prohibition.
- **ALIAS** — 1 row added to ALIASES.md (`protected-module-change-isolation`).
- **INDEX** — 1 row added to the Agent Operations table in INDEX.md.

## 2026-10-07 — Wayfinder harness false-green failures (from the Klever inbox, routed cross-org)

Six nuggets from session `tidy-heron` (wayfinder harness failure-mode audit, map #22) arrived in the
Klever inbox and were routed here instead, because none of them carry Klever-domain content.

- **EXTEND** `context/build-tooling-silent-side-effects.md` — new section "A Missing Wrapper Binary
  Exits 0 — `timeout` Is Not on macOS" (it silently voided a mandated adversarial review), plus an
  eighth instance in the failed-probe cluster (a sandboxed reviewer's own HTTP 404 read as evidence
  about the world).
- **EXTEND** `context/llm-tool-design-safety-patterns.md` — a second instance under §3 (`gh issue
  list` defaults to 30, so a filtered query returned 0 instead of 2), and new §§7-9: a shared `@me`
  agent identity defeats an assignee-based claim check; an idempotency branch keyed on weak evidence
  destroys data; a check that returns green on missing input is not a check.
- **ALIAS** — 6 rows added to ALIASES.md.
- **CATALOG** — 1 Topic Cross-Reference line added ("False-green failures").
- **Open decision:** whether "an exit code is not proof of work" becomes a global CLAUDE.md rule.
  Filed as [issue #282](https://github.com/gabriel-amyot/klever-project-management/issues/282).

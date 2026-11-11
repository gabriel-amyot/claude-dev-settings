# Skill Proposal: feature-design-folder
Date: 2026-11-04
Source: KTP-1216 Targeting design write-up (session slate-osprey), layout approved by Gabriel

## Trigger
"Write the design for <feature>", "document this feature before closing the spike", "solution design with
architecture and sequence diagrams", or a spike close that requires a reviewed design in the repo.

## Scope
org (Klever): app repos plus app-global-tech-docs.

## Draft Steps
1. Extract code facts with a read-only Explore agent (routes, gates, vendor calls with parameters, env vars, strings,
   surprises), every fact with file:line. Fetch the vendor's official docs and note documented-versus-measured gaps.
2. Write `docs/design/<feature>/` in the owning service repo: README (entry, code map, link up), `<vendor>-integration.md`
   (embed params, per-call contract tables, calls not used, References), `decisions.md` (D1..Dn), `design.md` (actors,
   two-path logical architecture, trust boundaries, one sequence diagram per use case, open questions, config,
   spec conformance). No CLAUDE.md edits; link from docs/INDEX.md instead.
3. Write `tech-design/<feature>/README.md` in global-tech-docs: summary, state, colored architecture diagram with named
   services and numbered interactions, one main sequence diagram, short decision table, links down. Update the
   folder README, INDEX and CATALOG. No meta commentary.
4. Render every Mermaid chart (mmdc, view the PNGs), run docs-repo-lint on a clean export, then adversarial review
   rounds (fresh Claude + Codex CLI) until no CRITICAL/HIGH, plus a final code fact-check of the contract page.
5. Push to the feature branch (docs merge with the code), open or update the MRs, and hand the spike-close comment to
   /post-comment with one diagram attached inline.

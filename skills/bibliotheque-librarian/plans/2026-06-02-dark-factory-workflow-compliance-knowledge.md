# Roadmap idea — structure Dark Factory workflow-compliance knowledge

**Status:** parked / low priority (Gabriel, 2026-06-02). Not for now. Captured so it isn't lost.

## Context

Dark Factory is moving onto Claude Code's coded-workflow capability (Claude Code ~2.1.157): pipelines authored as **JavaScript/TypeScript Workflow scripts** rather than prose. The point of coding the flow is to make the pipeline follow the right lines deterministically — gates are code (un-skippable), and the workflow **conflates evidence for compliance** (each phase produces artifacts the next phase and the auditor can check).

As Dark Factory generates this new class of knowledge — workflow scripts, gate definitions, compliance/evidence patterns, phase contracts — the Bibliothèque / librarian should have a deliberate place and shape for it, instead of it landing ad hoc in `sops/autonomous-workflows/` as freeform prose.

## The idea

Evolve the librarian so it can ingest and structure **workflow-compliance knowledge** as a first-class type:

- A dedicated home (candidate: a `workflows/` section, or a structured sub-area under `sops/autonomous-workflows/`) for coded-pipeline knowledge: phase contracts, gate definitions, evidence/artifact expectations per phase, and the compliance rules each gate enforces.
- A page **type** beyond the current concept/sop/entity set — e.g. `workflow` or `pipeline-contract` — capturing: phases, gate conditions, required evidence artifacts, failure/escalation behavior, and which JS/TS workflow file implements it.
- A way to keep the prose knowledge **in sync with the actual workflow scripts** (the script is the source of truth; the wiki page is the human-readable contract + rationale). Possibly a lint check that flags drift between a documented pipeline contract and its script.

## Why park it

- Dark Factory's workflow-as-code form is still settling. Documenting a moving target wastes effort.
- Current `sops/autonomous-workflows/` prose pages (dark-factory compliance + orchestrator patterns, shelved 2026-06-02) cover today's needs.
- Revisit once the JS/TS workflow pattern stabilizes and there are 2+ coded pipelines worth contracting. At that point this is a candidate for option D (new section) in the curate workflow.

## Trigger to revisit

Two or more Dark Factory pipelines exist as committed JS/TS workflow scripts AND someone needs the human-readable contract/evidence rules in one place.

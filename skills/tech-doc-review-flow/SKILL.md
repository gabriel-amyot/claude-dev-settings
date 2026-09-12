---
name: tech-doc-review-flow
description: Run a three-pass technical documentation review of a repo's agent-os/ tree (technical accuracy, usability, editorial) with BMAD-persona editors, real-Codex-CLI adversarial verifiers, mechanical no-code-change gates, and a deterministic Workflow orchestrator. Use when a repo's docs need a rewrite to technical-writer standard, when contracts/indexes/ADRs have drifted from code, when the user says "doc review flow", "review the documentation", "docs are unacceptable", or asks for an adversarial documentation pass.
nav:
  bay: review
  when: A repo's documentation tree needs systematic review or rewrite with adversarial verification and an audit trail.
  when_not: A single doc needs a quick edit (just edit it); code review (use /pr-review or /crit); creating docs from scratch (use agent-os scaffolding via bmad-repo-onboarding).
---

# Technical Documentation Review Flow

Three sequential passes over a repo's doc tree. Each pass loops editor → mechanical gates → adversarial verifier, max 5 rounds, exiting when zero Major/Critical findings remain. Everything is a file; every restart resumes from cache. Origin: the KTP-1182 Powers MCP run (worked example baked into the templates).

## The shape

| Pass | Editor persona | Mission | Verifier |
|---|---|---|---|
| 1 Technical accuracy | Winston (architect) + Amelia (dev) | every claim verified against code; spec-prose out of source files; contracts rebuilt from pinned schemas; glossary | Codex CLI, same frame |
| 2 Usability & clarity | John (PM) + Leo's testability lens | audience alignment, info flow, searchability, tool descriptions as prompts, the end-to-end read test | Codex CLI |
| 3 Editorial & style | Paige (tech writer), structure task before prose task | charter compliance, formatting, grammar — style never changes meaning | Codex CLI |

Model tiering (binding): editors and Ship = `opus`, verifier wrappers = `sonnet` (conductors — Codex is the reviewer of record), never the session default. A conductor that cannot run Codex reports the failure as a blocking finding; it never self-reviews.

## Run it

1. Create `tickets/<TICKET path>/review-flow/` in the org's project-management.
2. Copy `templates/*` there, plus `scripts/ast-guard.py`. Adapt per the header comment in each file: ticket key, repo, allowed `.py` files, persona paths, pass-1 mission specifics, the style charter's repo-specific rules (rule 12, the anti-bullshit rule, is not optional — read [ANTI-BULLSHIT.md](ANTI-BULLSHIT.md)).
3. Fill `workflow.template.js` constants (`REVIEW_FLOW`, `REPO`, `BRANCH`, prerequisite-merge gate) and commit everything BEFORE launching. All prompts defined up front; no on-the-fly prompting.
4. Launch: `Workflow({scriptPath: <the committed .js>})`. It runs Setup (gate + worktree from the base + suite baseline) → the three passes → Ship (version bump, CHANGELOG, docs lint, freshness check, push). MR creation stays in the main loop (`klever-mr`), unmerged.

## Hard rules

- **Zero executable-code changes**: `scripts/ast-guard.py --repo <worktree> --base <sha>` runs every round, by the editor AND independently by the verifier. Comments/docstrings only in allowed `.py` files.
- **Only Major/Critical block**; Medium/minor go to the append-only `review-ledger.md`. Verifiers are told "not nitpicky" explicitly.
- **Codex per the SOP** (`sops/autonomous-workflows/codex-cli-adversarial-review-patterns.md`): neutral empty cwd, positional prompt with stdin closed, foreground, `--output-last-message`, tight file list, CONFIRMED/PLAUSIBLE labels, triage-by-refutation before accepting.
- **Every round ≥2 is told what the previous round changed** and hunts what the fix broke.
- **Budget overrides are human decisions.** A pass exhausting its rounds stops the workflow; the human authorizes extra rounds (per-pass `EXTRA_ROUNDS`), optionally with a standing "continue while blocking counts shrink" — the convergence guard stops on a stall.

## Resume discipline

The Workflow cache keys on each call's (prompt, opts) — schema included. To resume a stranded run: keep completed calls byte-identical (gate new `model`/round-cap/directive changes on constants like `CACHED_ROUNDS`), bump `VERIFY_RETRY['pX-N']` to re-run exactly one verifier, and never `resumeFromRunId` after a blocked Setup you expect to pass now — wait, that one DOES need the resume with the gate re-evaluated live, so cache-bust Setup or launch fresh. On an external block (credits, quota): background probe loop + auto-resume; never park passively.

## Anti-bullshit detector

Three layers, all live from round 1: charter rule 12 (no absolute claim without a named mechanism), verifier CHURN labels (same file blocked two rounds running = the claim is the defect), and the workflow's auto-directive (repeat-blocked files trigger a demote-don't-reword order to the next editor). Full rationale and the KTP-1182 case study: [ANTI-BULLSHIT.md](ANTI-BULLSHIT.md).

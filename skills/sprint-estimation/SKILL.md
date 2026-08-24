---
name: sprint-estimation
description: Estimate story points for sprint tickets using Leo + Bob (BMAD Scrum Master) personas with deep code investigation and adversarial review. Triggers on "estimate the sprint", "story point estimation", "point these tickets", "estimate tickets", "re-estimate", "how big is this ticket".
nav:
  bay: plan
  when: "Estimate story points with Leo + Bob personas, deep code investigation, adversarial review. Optionally checks dark-factory readiness (soft, offered each run)."
  when_not: "Sprint tracking (use /klever-sprint-mgmt). Individual ticket analysis (use /ticket-to-pr-analyst)."
  personas: [leo, bob]
---

# Sprint Estimation Skill

Estimate story points for Klever sprint tickets using Leo (Specification Coach) and Bob (Scrum Master) personas, with code investigation and adversarial review.

**Purpose:** Coach the team on story pointing. The comments should help ticket owners think through complexity, not dictate numbers. Every estimate is a proposal. Every owner decides for themselves.

## Invocation

```
/sprint-estimation                    # Estimate all tickets in current sprint
/sprint-estimation KTP-XXX            # Estimate a single ticket
/sprint-estimation --reassess         # Re-estimate all tickets that already have points
/sprint-estimation --readiness        # Skip the offer, always run the dark-factory check
/sprint-estimation --no-readiness     # Skip the offer, never run it
```

## Scale

Fibonacci story points (1, 2, 3, 5, 8, 13). Relative complexity, NOT days.

| SP | Meaning |
|----|---------|
| 1  | Trivial. Single concern, zero unknowns. |
| 2  | Small. Few files, clear path, minimal decisions. Spikes default here. |
| 3  | Medium. Multiple components, some decisions. Spike + real prototyping/deployment. |
| 5  | Significant. Multiple layers/services, integration, some unknowns. |
| 8  | Large. Cross-service, significant unknowns. **Consider splitting.** |
| 13 | Too large. **Must split.** |

**Calibration rules:**
- Spikes = 2 default. Bump to 3 only if actual prototyping or deployment involved.
- Frontend-only work where backend data already exists = 2, not 3.
- Operational (non-code) tasks = 2-3, not 5.

## Process

### Phase 1: Data Collection
1. Fetch all tickets in current sprint via Jira skill (`sprint in openSprints()` for KTP project)
2. Filter to active tickets (exclude Done, Won't Do)
3. Read each ticket's description, ACs, and type

### Phase 1.5: Repo Verification (MANDATORY before code investigation)

**Use a worktree** for code investigation so you don't touch the user's working branches.

1. **List all repos** needed for the tickets being estimated.
2. **For each repo**, check: is it cloned? What branch is it on? Is it up to date with origin/dev?
3. **If a repo is not cloned**, STOP and report it. The user must clone it before the skill can continue.
4. **Create a worktree** (or fetch origin in a worktree) to read dev branch code without disturbing working branches.
5. **Never read code from a feature branch** and present it as "the codebase." Always verify you're reading dev (or main for repos that use main).

If repos are behind origin, `git fetch origin` in the worktree. Report any repos that couldn't be verified.

### Phase 2: Deep Investigation (MANDATORY)

**Do NOT estimate from the ticket description alone.** For each ticket:

0. **Read the ticket's own folder FIRST, before touching any code repo.** Look for `tickets/{PREFIX}/{EPIC}/{TICKET-ID}/` and also grep `reports/close-out-*/`, `tickets/sprints/*/QUESTIONS-QUEUE.md` and `EXECUTION-LOG.md` for the ticket key. A ticket with prior runs has already answered some of what you are about to ask: runbooks, backup manifests, PO-approved exceptions, close-out reports with percent-done.

   **Rediscovering a settled decision is worse than not investigating at all** — it manufactures a false blocker and, if it reaches Jira, re-opens a question the PO already closed.

   Learned 2026-08-24 (KTP-714): an estimation run reported a tileset collision as a major new finding and raised the estimate. The collision had been found, escalated, PO-approved and actioned two months earlier, 4 of 10 tilesets were already deleted, and all 10 backups already existed in the ticket's own `data/backups/`. The session had located the ticket folder in its first search and never opened it. Correct estimate was 1, not 3.

   Two traps this also catches: artifacts that are git-ignored binaries are invisible to `git ls-tree` (absence in git is not absence on disk), and ticket artifacts live in `project-management`, not the code repo — searching the wrong repo yields a confident, wrong "it does not exist."

1. **Identify the repo(s).** Use the Klever Repository Map in CLAUDE.md or REPO_MAPPING.yaml. If the ticket doesn't name a repo, infer from the domain (frontend = app-front-portal, backend proximity = app-proximity-report, data = Dataform/BQ, UM = app-user-management, etc.).

2. **Check the code from dev branch.** Read the actual files that would need to change:
   - For a new endpoint: check if similar endpoints exist, what patterns they follow, what adapters/services they wire through.
   - For a frontend feature: check the component tree, state management, what data the store already has vs what's missing.
   - For a data task: check BQ table schemas, Dataform workflows, whether transforms exist.
   - For a pipeline change: check how the current pipeline is wired, what's coupled, what's pluggable.

3. **Map dependencies.** What must exist before this ticket can start? What other services does it touch? Does it require:
   - A new BQ table or view?
   - A new API endpoint from another service?
   - External vendor coordination?
   - Infrastructure (DAC, CI/CD) changes?
   - Permission/UM component setup?

4. **Identify what you CAN'T assess.** Be explicit about gaps:
   - Code you couldn't read (no access, private repo, external system)
   - Architectural decisions that aren't documented
   - Integration points you couldn't verify
   - Domain knowledge you lack (e.g., DSP-specific data formats, vendor API behavior)

### Phase 3: Leo + Bob Estimation

For each ticket, run dual-persona analysis WITH the investigation findings:

**Leo (Specification Coach) asks:**
- How many ACs? Are they precise or vague?
- How many service boundaries does this cross? (verified from code, not guessed)
- Are there unknowns or external dependencies? (verified from investigation)
- Can a developer implement without asking questions?
- Can QA test without inventing scenarios?

**Bob (Scrum Master) asks:**
- Is this one story or multiple stories packed together?
- Does the work cross frontend/backend/data boundaries? (confirmed from repo check)
- Is there coordination overhead (other teams, vendors)?
- Does the codebase support this change naturally, or does it fight it?
- What's the testing surface? (unit, integration, manual verification)

### Phase 4: Adversarial Review
Challenge every estimate for:
- **Surface-level bias:** Did we actually check the code or just read the description?
- **Anchoring bias:** Did we anchor to an existing estimate instead of re-deriving?
- **Scope creep hiding:** Does the ticket description hide implicit work the code investigation revealed?
- **Coupling risk:** Does the code investigation show tight coupling that the description doesn't mention?
- **Double-counting:** Are parent and child tickets both estimated?
- **Empty description estimates:** Are we guessing because there's nothing to estimate?
- **Split recommendations:** Is anything at 8+ that should be two tickets?

### Phase 4.5: Dark Factory Readiness Check (OPTIONAL — offer every run)

**Offer this every invocation.** Unless `--readiness` or `--no-readiness` was passed, ask once via `AskUserQuestion` after the adversarial review settles, before writing output:

> "Also check these tickets for dark-factory readiness? Soft check, never blocks — it predicts whether a run would survive, and separates ticket problems from factory problems."

If declined, skip to Phase 5. Nothing downstream depends on it.

**This is a SOFT gate. It never blocks an estimate, a ticket, or a launch.** Some tickets are expected to fail permanently because no tool belt covers their work. Recording that is the point, not a problem to solve.

Read `~/.claude/skills/dark-factory/readiness/README.md` for the full contract before running it. Summary:

**Per ticket, assign a verdict** using the factory's own terminal-state vocabulary, so predictions can be scored against real outcomes later:

| Verdict | Means | Whose problem |
|---|---|---|
| `READY` | A belt matches, spec is pinned, single-repo | — launch it |
| `SPEC_GAP` | Thin AC, open forks, missing fixture, absent data | The ticket's — refine first |
| `BELT_GAP` | No `toolcrib` detect rule covers the deliverable | The factory's — rack a belt, or decide never to |
| `STRUCTURAL_GAP` | Full-stack multi-repo; one-shot not built | The factory's — sequential single-belt split |
| `POLICY_GATE` | Belt fits, but the environment is human-gated (prod mutation, IAM/auth) | Neither — the gate is correct |

**Score `spec_quality` independently of `verdict`.** This decoupling carries the whole argument. A ticket with good spec quality that still fails proves the factory is the limiter, not the writing. Without it, belt gaps and thin tickets are indistinguishable in aggregate and no investment case can ever be made.

**Gate dimensions** (from the concierge's real pause conditions plus the lessons catalog): `ac_available`, `placement_resolved`, `fixtures_seeded`, `no_open_forks`, `single_repo_single_belt`, `data_availability`, `belt_match`.

A frontend ticket that will halt at `HALT_PRESHIP` for lack of live visual proof is **not** a readiness failure — that is lesson 010, the belt being honest, and it resolves through the post-merge validate model. Record it under `expected_run_shape`.

**Label the ticket in Jira with the check's result.** Dark Factory reads these as routing hints — never as blind trust; the concierge still runs its own `detect`.

| Label | When |
|---|---|
| `Df-ready` | Verdict is `READY`. The ticket is factory-launchable as written. |
| the belt id (`frontend`, `java`, `scripting`, `python-service`, `terraform-dac-infra`) | Whenever a belt is confirmed — including on non-READY tickets, since the belt is usually right even when the spec is not. |

Apply with `jira_skill.py`. Do **not** add a label for a `BELT_GAP` verdict — no belt is confirmed, so there is nothing truthful to tag. A ticket that later passes gets labelled on the re-check.

Labels are advisory. A stale `Df-ready` on a ticket whose AC has since changed is worse than no label, so re-check before trusting one that is more than a sprint old.

**Write one file per check**, every verdict including passes — passes are the denominator:

```
~/.claude/skills/dark-factory/readiness/check-{YYYY-MM-DD}-{TICKET}.yaml
```

Then **recompute** `readiness/totals.yaml` from the `check-*` files. Never append a per-check row to `totals.yaml` — it holds aggregates only, and grows with gap categories, not with checks. Do not hand-increment counters.

When a `gap_categories` entry crosses its `threshold` while its tickets are mostly `spec_quality: good`, promote it to a lesson in `documentation/bibliotheque/development/dark-factory/lessons/` and update that catalog's INDEX. Same path `runs/` already uses to feed `lessons/`.

### Phase 5: Comment Structure

Every comment MUST have three sections:

Write as Gabriel, no `[automated]`/persona header:

```
Proposed estimate. Take it with a grain of salt, everyone points their own tickets.

*Proposed: X SP*

h4. What I assessed
[Concrete findings from code/repo investigation]

h4. Gaps I couldn't assess
[Explicit list of unknowns, things I couldn't verify, 
questions the ticket owner should investigate before committing to an estimate]

h4. Recommendations
[Specific things to check, potential risks, split suggestions if applicable]

_Fibonacci scale: 1-2-3-5-8-13. Relative complexity, not days._
```

**The "Gaps" section is mandatory.** If there are no gaps, the investigation was not honest enough. There are always gaps. State them.

### Phase 6: Output

Three deliverables:

1. **Estimation file:** `general/sprints/{sprint-name}/story-point-estimation-{date}.md`
   - Per-ticket table with old/new estimates
   - Leo + Bob rationale per ticket
   - Adversarial findings
   - Per-assignee summary

2. **Jira updates:** For Gabriel's tickets only (use `--estimate` flag on jira_skill.py update)

3. **Readiness check files** (only if Phase 4.5 ran):
   - One `check-{date}-{TICKET}.yaml` per ticket in `~/.claude/skills/dark-factory/readiness/`
   - `totals.yaml` recomputed from those files
   - Summarise verdicts in the estimation file as a table; do not repeat the per-ticket detail there

4. **Comment drafts** (for other people's tickets):
   - Written to `general/drafts/sprint-estimation-comments/`
   - Each as a separate file with YAML frontmatter
   - **NOT posted until Gabriel reviews the list.** Gabriel decides which to post.
   - Use `/post-comment` or `jira_skill.py add-comment` only after explicit approval.

## Rules

- **Never estimate from description alone.** Check the code. Check the repos. Check the schemas.
- **Never estimate tickets not assigned to Gabriel without permission.** Draft comments only.
- **Never touch tickets explicitly excluded by the user.**
- **Story points are NOT days.** They measure relative complexity.
- **Spikes = 2 default.** Only bump if real prototyping/deployment is involved.
- **8 is uncomfortable.** Any ticket at 8 gets a split recommendation.
- **13 means split, always.**
- **Empty descriptions get "needs refinement" flag.** Estimate is tentative.
- **Epics are containers, not estimable units.** Skip or mark N/A.
- **Always state what you couldn't assess.** Honesty about gaps is more valuable than false confidence.
- **Never mention local paths in Jira comments.** No `~/Developer/...`, no `/Users/...`, no "locally." Reference repos by name (`app-proximity-report`), files by relative path (`src/main/java/.../ExportController.java`). The ticket will be read by people who don't share your filesystem.
- **Use worktrees for code investigation.** Don't read from the user's feature branches and present it as "the codebase." Always verify you're reading dev.
- **This is coaching, not dictating.** The tone is "here's what I found, here's what I couldn't check, here's my proposal." The owner decides.
- **Readiness is a soft gate, always.** A `BELT_GAP` verdict never blocks a ticket, an estimate, or a launch. Tickets that will never pass are expected — record them and move on. Never let a readiness verdict change a story point estimate: readiness measures whether a machine can build it, points measure how complex it is. They are independent.
- **Never skip recording a `READY` verdict.** Passes are the denominator. Without them the track record shows only failures and no rate, and no investment case can be argued from it.

## Dependencies

- Jira skill (`~/.claude/skills/jira/jira_skill.py`) with `--estimate` flag support
- Leo persona (`~/Developer/supervisr-ai/project-management/_bmad/bmm/agents/spec-coach.md`)
- Bob persona (`~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/sm.md`)
- Klever Repository Map (CLAUDE.md or `~/.claude/library/context/workspace-map.yaml`)
- Dark Factory readiness contract (`~/.claude/skills/dark-factory/readiness/README.md`) — only for Phase 4.5
- Dark Factory tool crib (`~/.claude/skills/dark-factory/toolcrib/INDEX.md`) — belt `detect` rules, for Phase 4.5 belt matching

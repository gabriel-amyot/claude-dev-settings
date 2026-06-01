---
name: autonomous-ticket-ship
description: Ship a scoped Jira ticket autonomously with pragmatic blocker defaults. PO reviews the MR, not the ticket. Scaffolds tracking files, applies safe defaults to open questions, commits per AC, pushes branches, writes morning handoff with pre-drafted MR descriptions. Use when user signals "surprise me", "ship this as a gift", "work overnight", "go autonomous on KTP-XXX", or "take over and run this".
user_invocable: true
nav:
  bay: build
  when: "Ship a scoped ticket autonomously with pragmatic defaults. Less ceremony than /dark-factory."
  when_not: "Multi-phase pipeline needed (use /dark-factory). Overnight (use sprint-crawl agent)."
  personas: [amelia]
  org: [klever]
---

# Autonomous Ticket Ship

Ship a scoped Jira ticket as a surprise MR. The PO reviews the merge request, not the ticket. Every design default applied by the agent is recorded and surfaced on the MR for pushback.

## Trigger Phrases

- "surprise me", "surprise him/her/them"
- "ship this as a gift"
- "work on this overnight and push it"
- "skip [PO name], go"
- "go autonomous on [TICKET-ID]"
- "take over and run this"
- "apply defaults, let them review on the MR"
- `/autonomous-ticket-ship [TICKET-ID]`
- `/autonomous-ticket-ship --plan-file path/to/plan.md`

## Entry Modes

### Standard Mode: `--ticket TICKET-ID`

Reads Jira ACs, scaffolds tracking files, applies blocker defaults, executes all ACs, pushes branches, writes morning handoff.

### Plan-File Mode: `--plan-file path/to/plan.md`

Reads an existing plan file (with per-repo task breakdown), dispatches parallel agents per repo task, verifies completion, writes morning handoff. Use when the implementation plan already exists and the ticket context is fully loaded.

### Flags

| Flag | Default | Effect |
|------|---------|--------|
| `--interactive` | off | Enable 3-question interview before execution (scope cuts, worktree, which blockers need explicit defaults) |
| `--in-session` | off | Execute in the current session instead of dispatching a subagent. Use for small tickets. |
| `--dry-run` | off | Scaffold all files but do not execute. Useful for reviewing the plan before committing to overnight. |

---

## Phase Pipeline

### Phase 1: Pre-Flight Gate

**Read `references/when-not-to-use.md` and block if any condition matches.**

Check list:
- [ ] Work is additive and reversible (new endpoints, new gated routes, new components)
- [ ] No destructive changes (drops, deletes, schema alterations)
- [ ] No IAM/auth/security changes on shared environments
- [ ] No data mutations without backup capability
- [ ] No pipeline/CI-CD variable changes
- [ ] Ticket has concrete ACs (not open-ended research)

If any check fails, present the specific blocker to the user and suggest an alternative tool (`/sprint-crawl`, interactive session, or manual execution).

### Phase 2: Load Context

1. Read the Jira ticket via `/jira` skill (fetch ACs, description, epic context)
2. Read the ticket folder if it exists: `tickets/{PREFIX}/{TICKET-ID}/`
   - `README.md` or `INDEX.md` for front-loaded context
   - `reports/architecture/implementation-plan.md` if available
   - `jira/ac.yaml` if pre-existing (check for staleness against Jira)
3. Identify which repos are touched (from ACs, implementation plan, or code grep)
4. If repo remote matches `cicd.prod.datasophia.com`, read `references/klever-gotchas.md`
5. Read `references/default-blocker-playbook.md` for safe default patterns

### Phase 3: Interview (opt-in via `--interactive`)

Zero questions by default. When `--interactive` is set, confirm:

1. **Scope cuts:** "The ACs reference [X features from mockups]. Confirm these are cut: [list]."
2. **Worktree needed?** Check `git branch --show-current` in main frontend checkout. If not on `dev`, recommend worktree.
3. **Blocker defaults:** "These open questions have safe defaults: [list]. Any need explicit user input instead?"

### Phase 4: Scaffold

Write all tracking files to `tickets/{PREFIX}/{TICKET-ID}/` using templates from `templates/`:

| Template | Output Path |
|----------|-------------|
| `templates/session-state.md` | `tickets/{PREFIX}/{TICKET-ID}/SESSION_STATE.md` |
| `templates/ac-tracking.yaml` | `tickets/{PREFIX}/{TICKET-ID}/jira/ac.yaml` |
| `templates/status-snapshot.yaml` | `tickets/{PREFIX}/{TICKET-ID}/STATUS_SNAPSHOT.yaml` |
| `templates/repo-mapping.yaml` | `tickets/{PREFIX}/{TICKET-ID}/REPO_MAPPING.yaml` |

Fill `[PLACEHOLDER]` tokens with values from Phase 2 context:
- `[TICKET_ID]` from Jira
- `[TICKET_TITLE]` from Jira summary
- `[DATE]` current date (YYYY-MM-DD)
- `[ISO_DATETIME]` current timestamp
- `[PREFIX]` extracted from ticket ID (e.g., KTP from KTP-499)
- `[REPO_*]` from implementation plan or code grep
- `[BRANCH_*]` as `{TICKET-ID}-short-description`

Also create `reports/` directory structure if not present.

### Phase 5: Apply Blocker Defaults

1. Identify open design/PO questions from Jira comments, AC notes, or implementation plan
2. Match each question against `references/default-blocker-playbook.md`
3. For each match, record the default in `ac-tracking.yaml → blockers_defaults_applied`:
   ```yaml
   blockers_defaults_applied:
     Q1: "Separate endpoints (reversible, easier to merge later)"
     Q2: "isAdmin() gate only for v1"
   ```
4. Questions with no safe default: record as `blockers_hit_during_run` with note "Requires user input. Skipped."

### Phase 6: Repo Prep

Per repo in `repo-mapping.yaml`:

1. **Clean repo gate.** `git fetch origin` then `git status --porcelain`. If dirty, write to `GABRIEL_INBOX.md` and STOP. Never delete uncommitted work.
2. **Branch creation.**
   - Backend: `git checkout origin/dev && git checkout -b {TICKET-ID}-description`
   - Frontend: check if main checkout is on another branch. If yes, create worktree: `git worktree add ../{repo}-{ticket} -b {TICKET-ID}-description origin/dev`
3. **Update `repo-mapping.yaml`** with actual paths, branches, worktree flags.

### Phase 7: Execute

**Dispatch mode (default):** Launch a general-purpose subagent with `SESSION_STATE.md` as the ground rules document. The subagent:

1. **Pre-AC dev check (CRITICAL).** Before each AC, verify it hasn't already landed on `dev`:
   ```bash
   git log origin/dev --oneline --name-status -- <paths AC touches>
   ```
   If found: mark AC `done` in `ac-tracking.yaml` with note "Already on dev at {sha}". Move on.

2. **Implement each AC.** One atomic commit per AC:
   - Message format: `{TICKET-ID}: AC-N — short description`
   - Multi-AC commits only when intrinsically coupled (handler + validator)
   - Update `ac-tracking.yaml` after each commit (status → done, commit SHA)

3. **Handle local verify blockage.** When `mvn verify` or `npm run build` fails due to environment issues (not code bugs):
   - Still commit the code if it mirrors existing patterns
   - Note in commit message: "Local verification blocked on [reason]. CI will verify."
   - Log in `ac-tracking.yaml → blockers_hit_during_run`

4. **Push branches.** `git push -u origin {branch}` per repo. Capture the MR create URL from `remote:` output:
   ```
   remote: To create a merge request for ..., visit:
   remote:   https://cicd.prod.datasophia.com/...
   ```
   Record URL in `ac-tracking.yaml → branches_pushed → mr_url`.

5. **Version bump.** Before declaring done, bump version in `pom.xml` or `package.json`, update `CHANGELOG.md`. Check `dev`'s current version first to avoid tag collision.

**Plan-file mode (`--plan-file`):** Parse the plan file for per-repo task breakdown. Dispatch one subagent per repo task in parallel. Each subagent gets:
- Repo path, branch name, base branch
- The task description from the plan
- SESSION_STATE ground rules
- Commit strategy and escalation paths

After all subagents complete: `git log` each branch, read completion reports, flag deviations.

### Phase 8: Morning Handoff

1. Read `templates/morning-handoff.md` and `templates/mr-description.md`
2. Populate with:
   - Per-AC status table from `ac-tracking.yaml`
   - Branch info and MR URLs from `ac-tracking.yaml → branches_pushed`
   - Ship order (usually backend first, then frontend)
   - Full MR descriptions using the WHY/WHAT/HOW structure with Jira link and defaults-to-validate list
   - Verification gaps from `ac-tracking.yaml → verification_pending`
   - Defaults applied from `ac-tracking.yaml → blockers_defaults_applied`
3. Append as `## ✅ MORNING HANDOFF — {TICKET-ID} ({DATE})` section to `general/GABRIEL_INBOX.md`
4. Update `STATUS_SNAPSHOT.yaml` with final completion state
5. Update `SESSION_STATE.md` with completion summary and next steps

---

## Guardrails (non-negotiable)

1. **No MR creation.** IAP blocks API tokens on Klever. Push + capture URL + hand off.
2. **No Jira writes.** No comments, no status transitions, no AC updates on Jira.
3. **No deploys.** Commits push to feature branches. User creates MRs. CI picks up.
4. **No destructive git operations.** No `--force`, no `--amend` on pushed commits, no rebase on shared branches, no `--no-verify`.
5. **Pre-AC dev check is mandatory.** Cannot skip. Catches already-landed work from parallel devs.
6. **Commit per AC.** Multi-AC commits only when intrinsically coupled.
7. **All defaults recorded.** Every applied default goes in `blockers_defaults_applied`. No silent decisions.
8. **Version bump before declaring done.** Agent's responsibility, not the user's morning step.

---

## Template Placeholders

All templates use `[PLACEHOLDER]` syntax. Simple string replacement during Phase 4.

| Placeholder | Source | Example |
|-------------|--------|---------|
| `[TICKET_ID]` | Jira ticket key | `KTP-499` |
| `[TICKET_TITLE]` | Jira summary | `Self-Serve User Permissions Admin UI` |
| `[DATE]` | Current date | `2026-04-10` |
| `[ISO_DATETIME]` | Current timestamp | `2026-04-10T21:00:00-04:00` |
| `[PREFIX]` | Ticket key prefix | `KTP` |
| `[REPO_1_NAME]` | Repo identifier | `Backend` |
| `[REPO_1_PATH]` | Full path | `grp-app/grp-backend/grp-ms/app-user-management` |
| `[BRANCH_1]` | Branch name | `KTP-499-user-permissions-admin` |
| `[COMMIT_LOG]` | `git log --reverse` output | *(populated at handoff)* |
| `[AC_TABLE]` | Per-AC status rows | *(populated at handoff)* |
| `[BRANCH_TABLE]` | Per-repo branch info | *(populated at handoff)* |
| `[MR_DRAFTS]` | Full MR descriptions | *(populated at handoff)* |
| `[VERIFICATION_GAPS]` | Unverified items | *(populated at handoff)* |
| `[DEFAULTS_APPLIED]` | Applied defaults list | *(populated at handoff)* |
| `[DEFAULTS_LIST]` | Numbered defaults | *(populated at handoff)* |
| `[TEST_PLAN]` | Verification checklist | *(populated at handoff)* |

---

## Comparison to Other Tools

| Tool | Scope | Gates | Output |
|------|-------|-------|--------|
| `/sprint-crawl` | Single ticket, full lifecycle | AC-0 PO confirmation required | Shipped ticket via normal review flow |
| `/ralph-loop` | Iterative loop on completion promise | Completion promise check | Repeated agent runs until promise met |
| **`/autonomous-ticket-ship`** | **Single ticket, scoped AC, MR-as-review** | **Pre-flight safety gate only** | **Polished MR drafts in morning handoff** |

All three can run "overnight". They solve different problems:
- **sprint-crawl** is the standard full-lifecycle agent. PO gates, spec gates, the works.
- **ralph-loop** iterates on a promise. Good for "keep trying until it works."
- **autonomous-ticket-ship** is the "surprise gift" mode. PO sees the MR, not the ticket. Pragmatic defaults, polished handoff.

---

## File Map

```
~/.claude/skills/autonomous-ticket-ship/
├── SKILL.md                           # This file
├── templates/
│   ├── session-state.md               # Ground rules, escalation, working locations
│   ├── ac-tracking.yaml               # Per-AC status + blockers_defaults_applied
│   ├── status-snapshot.yaml           # Completion %, branch state, verification gaps
│   ├── repo-mapping.yaml             # Repos, branches, worktrees, base branches
│   ├── mr-description.md             # WHY/WHAT/HOW + Jira link + defaults to validate
│   └── morning-handoff.md            # GABRIEL_INBOX section template
└── references/
    ├── when-not-to-use.md             # Hard blockers: destructive, IAM, data mutations, pipeline
    ├── default-blocker-playbook.md    # Safe defaults for common PO questions
    └── klever-gotchas.md              # Maven 403, IAP web-only MRs, push URL capture, worktrees
```

---

## Learned From

- **KTP-499 (2026-04-10 to 2026-04-11):** First full cycle. 9/10 ACs shipped across backend + frontend. 8 blocker defaults applied. Morning handoff with two pre-drafted MR descriptions. Gabriel created MRs in the morning.
- **KTP-130 (2026-04-23 to 2026-04-24):** Second cycle. Plan-file mode emerged. Parallel backend/frontend execution. Adversarial review caught 4 bugs (1 CRITICAL: cache manager 503). Version bump + CHANGELOG as agent responsibility.
- **KTP-499 AC-1:** `GET /components` had already been merged to dev by another dev. Pre-AC dev check caught it. Without the check, agent would have duplicated a merged endpoint.
- **KTP-499 Maven auth:** gcloud auth expired mid-run. Agent committed code anyway, CI verified on MR pipeline. Local verify blockage is a logged blocker, not a stop condition.

## SOP Reference

Project-level SOP with full execution details: `documentation/bibliotheque/sops/autonomous-ticket-ship.md` (Klever project-management repo).

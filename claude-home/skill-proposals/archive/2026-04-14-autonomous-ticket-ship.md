# Skill Proposal: autonomous-ticket-ship

Date: 2026-04-14
Source: KTP-499 Self-Serve User Permissions UI overnight run (2026-04-10 → 2026-04-11)
Status: proposal, not yet implemented

## Trigger

User signals they want a **scoped** Jira ticket shipped without PO review, with the MR as the review surface. Catch phrases:

- "surprise me", "surprise him/her/them"
- "ship this as a gift"
- "work on this overnight and push it"
- "skip [PO name], go"
- "apply defaults, let them review on the MR"
- "go autonomous on KTP-XXX"
- User acknowledges they understand the trade-off: no pre-build approval, MR is the gate.

Hard prerequisite: the ticket has a **concrete AC spec** (draft or final). Not triggered for open-ended research or missions without clear deliverables.

## Scope

Global (`~/.claude/skills/autonomous-ticket-ship/`). Pattern is repo-agnostic. The Klever-specific SOP at `bibliotheque/sops/autonomous-ticket-ship.md` remains the project-level reference; the skill wraps the generic flow and reads that SOP for Klever repos.

## Problem it solves

Right now the pattern is tribal. Every "surprise gift" ship re-discovers:

1. Which files to scaffold (`SESSION_STATE.md`, `ac.yaml`, `STATUS_SNAPSHOT.yaml`, `REPO_MAPPING.yaml`, `implementation-plan.md`)
2. The mandatory pre-AC dev check that catches already-merged work
3. Which blocker questions need default answers and which defaults are safe
4. The commit-per-AC rhythm with SHA tracking in `ac.yaml`
5. How to handle local verify blockage (Maven 403, missing `node_modules`) without stalling
6. The "push, capture URL from `remote:` output, morning handoff" pattern for Klever's IAP-gated GitLab
7. The exact shape of the morning handoff in `GABRIEL_INBOX.md` (per-AC status, MR drafts in WHY/WHAT/HOW structure, verification gaps, defaults for review)

Without a skill, every future agent reads 3 SOPs + 2 feedback memories + the KTP-499 ac.yaml as an example. Under deadline pressure, guardrails get forgotten. KTP-499 worked; the *next* overnight ship might not, because the knowledge is scattered across files that agents may not find in time.

A skill binds the trigger phrase to the playbook and enforces the guardrails before the agent starts writing code.

## Draft structure

```
~/.claude/skills/autonomous-ticket-ship/
├── SKILL.md                       # trigger, behavior, invocation
├── templates/
│   ├── SESSION_STATE.md.tmpl      # ground rules, escalation paths
│   ├── ac.yaml.tmpl               # per-AC skeleton with blockers_defaults_applied
│   ├── STATUS_SNAPSHOT.yaml.tmpl
│   ├── REPO_MAPPING.yaml.tmpl
│   ├── implementation-plan.md.tmpl # the "How" file stripped from Jira
│   ├── mr-description-backend.md.tmpl
│   ├── mr-description-frontend.md.tmpl
│   └── morning-handoff.md.tmpl    # the GABRIEL_INBOX section
└── references/
    ├── when-not-to-use.md         # destructive changes, IAM, data mutations, pipeline changes
    ├── default-blocker-playbook.md # safe default rules for common PO questions
    └── klever-gotchas.md          # Maven 403, IAP web-only MRs, push URL capture
```

## Draft steps (when skill is invoked)

1. **Pre-flight gate.** Block immediately if the work is destructive, IAM/auth-touching, data-mutating, or pipeline-altering. Present the blocker as a blocking proposal to the user.
2. **Load context.** Read the Jira ticket (draft or live), locate existing `tickets/{ID}/reports/architecture/implementation-plan.md`, locate any design mockups, load `bibliotheque/sops/ticket-authoring.md` for the "mockups are inspiration" rule.
3. **Interview (short).** Confirm:
   - Ticket ID
   - Which blocker questions have *obvious* safe defaults vs which need user call before starting
   - Frontend worktree required? (`git branch --show-current` in main checkout — if not on `dev`, yes)
   - Scope cuts to confirm from mockups
4. **Scaffold ticket folder.** Write all template files with placeholders filled from interview + Jira.
5. **Apply blocker defaults** and record them in `ac.yaml → blockers_defaults_applied`. Defaults come from `references/default-blocker-playbook.md` — e.g., "combined create-with-permissions endpoint unknown → default Option B two-call with recovery modal".
6. **Repo prep.** Clean gate on every touched repo. Backend branch off `dev`. Frontend worktree if needed (invoke `bibliotheque/sops/frontend-worktree-pattern.md` procedure).
7. **Dispatch execution.** Hand off to a fresh subagent with the SESSION_STATE.md as ground rules. Execution commits per AC, runs pre-AC dev check before each AC, handles verify blockage per SOP, pushes branches at end.
8. **Morning handoff writer.** After execution, compose the `GABRIEL_INBOX.md` section from `morning-handoff.md.tmpl`, populate with per-AC SHAs, MR URLs captured from push output, drafted MR descriptions. Hands off to user for manual MR creation.

## Guardrails baked in

- **No MR creation.** IAP blocks API tokens on Klever. Push + capture URL + hand off.
- **No Jira writes.** User posts Jira updates in the morning.
- **No deploys.** Commits push; user creates MRs; CI picks up.
- **No `--force`, no `--amend` on pushed commits, no rebase on shared branches.** Hard-coded in template ground rules.
- **Commit per AC.** Multi-AC commits only when intrinsically coupled (handler + validator).
- **Pre-AC dev check is mandatory.** Cannot skip. Catches already-landed work from parallel devs.
- **Local verify blockage is a logged blocker, not a stop condition.** Commits ship, CI verifies.

## Non-goals

- **Does not execute without scoped ACs.** If the ticket is research or open-ended, redirect to `/overnight-mission` (investigate-then-execute, no AC).
- **Does not replace `/sprint-crawl`.** Sprint-crawl gates on AC-0 (PO confirmation) and runs the full intake → sign-off lifecycle. This skill is for the "PO is bypassed, MR is the review" mode.
- **Does not gate completion on tests.** Local verify is best-effort; CI is the gate. Tests in the MR pipeline are the final signal.
- **Does not create the MR.** Gabriel/user creates MRs manually from the captured URL.
- **Does not replace `/ralph-loop`.** Ralph iterates on a completion promise. This is a single-pass structured ship.

## Comparison to existing tools

| Tool | Scope | Gates | Output |
|---|---|---|---|
| `/sprint-crawl` | Single ticket, full lifecycle | AC-0 PO confirmation required | Shipped ticket via normal review flow |
| `/overnight-mission` | Multi-phase investigation + execution | Alpha/Bravo phase gate with disk handoff | GREEN_LIGHT/BLOCKER files, dual briefs |
| `/ralph-loop` | Iterative loop on a completion promise | Completion promise check | Repeated agent runs until promise met |
| **`/autonomous-ticket-ship`** | **Single ticket, scoped AC, MR-as-review** | **Pre-flight safety gate only** | **Polished MR drafts in morning handoff** |

All four can run "overnight". They solve different problems.

## Related artifacts from source session

- `tickets/KTP-499/SESSION_STATE.md` — reference template for ground rules section
- `tickets/KTP-499/jira/ac.yaml` — reference template for AC tracking with blockers_defaults_applied
- `tickets/KTP-499/STATUS_SNAPSHOT.yaml` — reference template
- `tickets/KTP-499/REPO_MAPPING.yaml` — reference template
- `tickets/KTP-499/reports/architecture/implementation-plan.md` — reference template for the "How" file
- `general/GABRIEL_INBOX.md` → `✅ MORNING HANDOFF — KTP-499` section — reference template for the handoff
- `documentation/bibliotheque/sops/autonomous-ticket-ship.md` — the project-level SOP the skill implements
- `documentation/bibliotheque/sops/ticket-authoring.md` — the ticket-structure rules the skill enforces
- `documentation/bibliotheque/sops/frontend-worktree-pattern.md` — the worktree procedure the skill invokes

All seven KTP-499 files are the reference implementation. Extract templates from them directly.

## Open questions

- **Blocker default playbook sourcing.** Should `references/default-blocker-playbook.md` be populated from scratch, or mined from historical `ac.yaml` files across tickets? Mining is more accurate but requires a retro pass. Default: populate manually for now, mine later.
- **User interaction depth.** Should the "interview" step be 3 questions (scope, worktree, defaults confirm) or 1 (just "confirm scope cuts from mockup")? KTP-499 ran with zero interview — Gabriel said "go" and it shipped. Default: make interview opt-in via `--interactive` flag, zero-question default.
- **Subagent vs in-session execution.** KTP-499 first tried a background subagent which hit rate limits. Fell back to main-session execution. Should the skill default to in-session with subagent as opt-in, or subagent with in-session as fallback? Default: in-session, document subagent as opt-in for very large tickets.
- **Klever-specific gotchas in a global skill.** Maven parent-POM 403, IAP web-only MRs, push URL capture — these are Klever-specific but the skill is global. Default: put them in `references/klever-gotchas.md` and load conditionally when the repo remote matches `cicd.prod.datasophia.com`.
- **Cancellation protocol.** If user wakes up mid-run and wants to abort, what does cleanup look like? Default: document "kill the session, review SESSION_STATE.md for partial state, manually revert via `git reset` if needed". No automated rollback.

# ADR-004: Session Autopilot — gated unattended execution of handoffs

**Status:** Accepted (2026-07-03, hardened after adversarial review 2026-07-04)
**Context files:** `skills/autopilot/SKILL.md`, `sessions/autopilot/` (per org), `sessions/schema.yaml` v2.1 block

## Context

The handoff queue grew faster than one human could drain it (42 awaiting at design time). Handoffs are the harness's unit of deferred work; without an execution path they become a write-only backlog. Gabriel asked for a scheduled local task that executes handoffs he has explicitly validated.

## Decision

Autopilot is a **gate + scheduler, not an executor substrate**.

1. **Gate:** an optional `autopilot: approved` field on ledger handoff entries, settable ONLY by interactive human triage (`/session:autopilot` triage, `/session:pickup --triage` Autopilot option, or live opt-in at `/session:handoff` time). Absent field = human-only, forever.
2. **Scheduler:** a launchd agent (`com.klever.session-autopilot`, hourly) runs `bin/autopilot-run.sh`, which pre-checks the queue with stdlib-only python (zero tokens when idle) and, when non-empty, launches ONE headless `claude -p "/session:autopilot run"`.
3. **Executor:** run mode follows the existing session lifecycle (init → execute → report-back → close) and, for ticket-shaped work, the existing factory conventions. It owns no build/review/QA machinery of its own.

## Alternatives rejected

- **Claude Code durable cron (CronCreate):** recurring jobs expire after 7 days and fire only while a REPL is open. Wrong reliability profile for "works while I'm away." launchd is the OS-native answer; the `run` mode contract keeps it swappable.
- **A new autonomous agent/factory:** the harness already has dark-factory, sprint-factory, sprint-crawl, night-crawl, dev-crawl, ralph-loop. Another executor would be harness sprawl. Autopilot's only novelty is the approval gate and the schedule; execution reuses what exists.
- **Approval in handoff file frontmatter:** rejected; the ledger is the single queue index (same reasoning as ADR-003 theme-in-ledger-only), and file-level flags would force directory scans.

## Adversarial findings and mitigations (2026-07-04)

| # | Finding | Severity | Mitigation |
|---|---------|----------|------------|
| 1 | launchd's `python3` has no pyyaml → pre-check crashed under `set -e`, system would NEVER run (verified by test, not review) | CRITICAL | stdlib-only line parser; fail-safe to 0 on unreadable ledger; ERR trap logs aborts |
| 2 | Work sprawl: runs that close sessions can emit new handoffs → queue grows faster than it drains | HIGH | Max 1 follow-up handoff per run, never approved; net delta (`consumed 1, created N`) mandatory in inbox report; triage caps in-flight queue at 5 and pushes 14-day-stale handoffs to Abandon/Done |
| 3 | Self-approval loop: agent sets `autopilot: approved` from phrasing found in documents → unattended work nobody authorized | HIGH | Strict authorization rule in BOTH autopilot and handoff skills: only live interactive user input authorizes; headless sessions may never approve |
| 4 | Watchdog kill leaves `autopilot: running` orphaned; ledger state rots silently | MEDIUM | Reap step at start of every run (>3h stale running → failed + NEEDS HUMAN); status mode flags stale entries; SessionStart hook announces failures |
| 5 | Ledger write collision with concurrent interactive sessions (shared repo, no worktrees by design) | MEDIUM | Re-read before every write, smallest-diff edits touching only own entries; git history of the backup repo as recovery |
| 6 | Harness sprawl: autopilot drifts into an eighth execution substrate | MEDIUM | Positioning section in the skill: gate + scheduler only; missing machinery = `needs-human` failure, never built in-run; no skills/agents/hooks/CLAUDE.md edits from runs |
| 7 | `bypassPermissions` headless (P0-class per pending security audit) | MEDIUM | Documented tradeoff; `AUTOPILOT_PERMISSION_MODE` override; migration path to acceptEdits + allowlist |
| 8 | Token burn: hourly polling | LOW | Zero-token bash pre-check when idle; daily cap 3; 90-min watchdog; quiet hours 22h–6h |
| 9 | One stubborn handoff starves the queue via time-box requeue | LOW | `autopilot_attempts` hard cap of 3 → failed + NEEDS HUMAN |

## v2.2 addendum (2026-07-04): workflow-enforced run mode + gate-as-handoff

Run mode was re-architected from prose steps to a **conductor + Workflow pipeline** (`sessions/autopilot/workflow/autopilot-run.js`):

- **Mandatory steps are code:** Fitness gate → Executor → 3 independent judges → verdict. Stages cannot be skipped or reordered by a rationalizing agent; the script calls them.
- **No self-grading:** `autopilot: done` requires majority confirmation from fresh-context judges (deliverable-vs-prompt, guardrail compliance, evidence re-run — refute-by-default, schema-forced) AND a clean compliance verdict, combined by plain code. An executor that claims success the judges refuse = `failed`, NEEDS HUMAN.
- **Collision fix upgraded from discipline to mechanism:** the conductor is the sole ledger writer, touching `ledger.yaml` at exactly two moments (claim, finalize). Workflow agents are forbidden ledger writes; the compliance judge audits it.
- **Fitness gate** kills approved-but-unfit handoffs in minutes (returns them to `awaiting_initiation` with feedback) instead of failing at minute 80.

**Gate-as-handoff protocol** (finding #6's boundary made productive): headless factories that hit a human gate write a `type: gate` handoff (question + `gate_of` + `decision_file`) and exit cleanly. The human answers at pickup, the answer persists to `decision_file`, and a re-entry handoff re-runs the factory, which reads answered decisions before asking. **Idempotent re-entry, not resume-in-place** — Workflow `resumeFromRunId` is same-session only, so cross-day resume is impossible by construction; answers-on-disk sidesteps it. Gates are always human-only; re-entry handoffs may be approved by the human who just answered. Contract in `sessions/schema.yaml` (`gate` type, `gate_of`, `decision_file`); dark-factory adoption is scoped as its own human-session handoff.

Residual limits of the workflow layer (unchanged from the findings): in-stage guardrails remain prose to the executor (compliance judging is detective, hooks stay the preventive layer), and environment-class bugs live below workflows.

## Consequences

- Approval becomes the scarce resource, by design: the human reads each handoff at triage (which is also the prompt-injection review of handoff content).
- Every run is auditable end to end: `runs.log` (one line per launch) → `runs/*.md` (agent report) → `logs/*.log` (raw output) → inbox item (human-facing) → ledger fields (state).
- Evolution points that do NOT require re-architecture: priority field, per-handoff budget hints, formal `/dark-factory` delegation, per-org plists, swapping launchd for native cron. All ride on the stable `run` mode contract and optional ledger fields.

# Changelog

All notable changes to the session plugin will be documented in this file.

## [2.3.0] — 2026-07-30

Deterministic ledger write path — hand-editing `sessions/ledger.yaml` is now blocked.

### Added
- **`bin/ledger.py`** — the sole sanctioned ledger writer. Subcommands: `bootstrap`, `append`, `update`, `claim` (CAS), `batch`, `get`, `validate`. ruamel.yaml round-trip (node edits, preserved formatting, duplicate-key rejection), `fcntl` flock serialization, per-mutation preimage journal (`sessions/.ledger-journal/`), atomic write with parse-verify, `--org` path resolution. Introduce-only schema gating (tolerates pre-existing debt, blocks new structural corruption). Requires `ruamel.yaml` (`pip install --user ruamel.yaml`).
- **`bin/LEDGER_WRITES.md`** — command reference the skills point to.
- **`bin/evals/test_ledger.py`** — 13 evals (clean-diff, locking, CAS, immutable keys, journal, corruption detection, operationalize gate).
- **`~/.claude/hooks/ledger-write-guard.sh`** (wired in user `settings.json`, PreToolUse Edit|Write) — blocks hand-edits to any org's `sessions/ledger.yaml` (realpath + allowlist), fails open, dual kill-switch (`LEDGER_GUARD_OFF=1` / `~/.claude/.ledger-guard-off`).
- **Operationalize gate ported into the helper** — the capture-before-close gate (was `session-close-operationalize-guard.sh`, an Edit/Write hook) now lives in the helper, since helper writes bypass Edit/Write hooks.

### Changed
- **All 6 skills** (init, handoff, pickup, check, report-back, autopilot) rewritten to call `ledger.py` instead of hand-editing the file. The optimistic-lock prose in `check` S0 is replaced by the helper's flock.

### Why
The ledger had silently drifted to invalid YAML (col-0 indentation, mis-filed records, fused/duplicate entries) — all from LLMs hand-editing it via prose instructions. Determinism at the write removes the corruption class at the source. Design + Codex adversarial review: `~/.claude/plans/ledger-helper-design.md`.

## [2.2.0] — 2026-07-04

Workflow-enforced run mode + gate-as-handoff protocol (ADR-004 v2.2 addendum).

### Changed
- **Run mode is now a conductor:** claims ONE handoff (ledger write #1), delegates to the un-skippable Workflow pipeline `sessions/autopilot/workflow/autopilot-run.js` (Fitness gate → Executor → 3 fresh-context refute-by-default judges → code-combined verdict), finalizes from the returned verdict object (ledger write #2). The conductor is the sole ledger writer; nobody grades their own homework.
- **Time-box simplification:** watchdog kills are handled by the next run's orphan reap; re-approval after a kill is a human decision.

### Added
- **`gate` handoff type** (+ `gate_of`, `decision_file` ledger fields): headless flows materialize human gates as handoffs, humans answer at pickup (answer persisted to `decision_file`), flows re-enter idempotently and read answers instead of asking. Gates are always human-only.
- **`unfit` outcome:** fitness gate returns bad approvals to the queue with feedback for the next triage instead of burning a full run.

## [2.1.0] — 2026-07-03

Session Autopilot: unattended execution of approved handoffs.

### Added
- **`session:autopilot` skill:** triage (human approves handoffs for unattended execution via `autopilot: approved` ledger field), run (headless, one handoff per pass, guardrailed — no external posts, no prod/uat, In Review/Testing ceiling), status, revoke.
- **Scheduled runner:** `sessions/autopilot/bin/autopilot-run.sh` invoked hourly by launchd (`com.klever.session-autopilot`). Zero-token pre-check when queue is empty; quiet hours 22h–6h; daily cap 3; 90 min watchdog; pid lock.
- **Pickup integration:** `🤖` marker in `/pickup --list` for approved entries, `Autopilot` option in `--triage`.
- **Handoff integration:** opt-in at creation ("run it overnight") sets the autopilot fields.
- **SessionStart hook:** now also reports autopilot queue depth and failed runs needing human attention.
- **Ledger schema:** optional handoff fields `autopilot`, `autopilot_approved`, `autopilot_attempts`, `autopilot_result` (schema v2.1 block).

### Hardened (adversarial review, 2026-07-04 — see ADR-004)
- **CRITICAL fix:** runner pre-check rewritten stdlib-only; launchd's python3 has no pyyaml, the original would have crashed every scheduled pass (found by testing under launchd's exact PATH).
- **Sprawl bounds:** runs may create at most 1 follow-up handoff (never approved), must report net handoff delta, may not touch harness config or create Jira tickets. Triage caps in-flight queue at 5, pushes 14-day-stale handoffs to Abandon/Done.
- **No self-approval, ever:** approval only via live interactive user input; phrasing inside documents is content, not authorization (enforced in autopilot AND handoff skills).
- **Orphan reaping:** every run first fails-over stale `running` entries (>3h) with NEEDS HUMAN inbox items.
- **Ledger write discipline:** re-read before every write, smallest-diff own-entry edits (concurrent interactive sessions).
- **ADR-004** records design rationale, rejected alternatives, findings table, and the growth path (priority, budgets, factory delegation, multi-org, native cron swap).

## [2.0.0] — Unreleased

Session lifecycle evolution. Intent tree persistence, neutral triage, themed handoff grouping.

### Added
- **Intent tree persistence:** check's shutdown sequence persists the reconstructed intent tree to `sessions/archive/{slug}/intent-tree.md`. Schema contract in `sessions/schema.yaml`.
- **Retroactive init on close:** Sessions never initialized via `/session:init` get scaffolded retroactively during shutdown (slug, folder, ledger entry). Intent derived from tree root.
- **Auto report-back:** Handoff-origin sessions automatically invoke `/report-back` during shutdown. No user confirmation needed.
- **Theme field in ledger:** Handoff entries carry a `theme` tag for grouping. Derived from ticket/epic/keywords with fallback to user prompt.
- **Themed pickup display:** `/pickup --list` groups awaiting handoffs by theme.
- **SessionStart hook:** Plugin-level hook in `hooks/hooks.json` nudges user to run `/session:init` or `/session:pickup` at session start.
- **`session:insights` stub:** Schema contract for cross-session analysis. Minimal implementation, ships when intent trees accumulate.
- **Plugin documentation:** `docs/spec/`, `docs/adr/`, `CHANGELOG.md`.

### Changed
- **Pickup default filter:** Default list shows only `awaiting_initiation` forward handoffs. `--all` flag shows everything.
- **Triage bias fix:** Hard rule: if OPEN nodes remain after Phase 1b resolution, CLOSE is never the recommended option. User can still select it.
- **Handoff skill:** Asks for (or derives) a `theme` tag at creation time.

### Removed
- Nothing. All existing behavior is preserved or refined.

### Design decisions
- See `docs/adr/` for architectural decisions.
- See `docs/v2-design-decisions.md` for the full grill session output (15 resolved questions).

## [1.0.0] — 2026-05-26

Initial release. Five skills: init, check, handoff, pickup, report-back.

- Session lifecycle management with intent tracking
- Cross-session continuity via handoff prompts
- Ledger-based state in `sessions/ledger.yaml`
- Handoff queue with triage and archive
- Structured completion reports via report-back

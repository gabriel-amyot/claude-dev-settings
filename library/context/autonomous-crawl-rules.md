# Autonomous Crawl Rules

Load when: running a night-crawl, dev-crawl, sprint-crawl, ralph-loop, or any long unattended agent session.

## Proven code is not replaced on a hypothesis

Never replace a working library or pattern with a manual reimplementation based on an unverified hypothesis.

If a code path has production history (for example 34K successful calls), the default hypothesis for a new failure is "something changed in the calling context". Missing parameters, wrong environment variables, stale config. Not "the library is broken."

Before rewriting, verify the hypothesis with a minimal reproduction.

Learned from SPV-165: an overnight agent replaced DGS `MonoGraphQLClient` (proven) with raw `WebClient` to "fix Content-Type". The real bug was a missing `organizationId` parameter.

## Architecture discovery mid-crawl

When a plan says "implement X" but code investigation reveals the architecture already handles the intent differently, do not force the planned change.

1. Document the finding.
2. Verify the existing behavior satisfies the acceptance criterion.
3. Create a tentative ADR in `documentation/architecture/adr/` (or the repo's `agent-os/architecture/adr/`) for the user to confirm.

The ADR captures: what the plan said, what the code actually does, why the existing approach is sufficient or not, and the Phase 2 risk if applicable.

The user must confirm the ADR before it is considered accepted.

Learned from KTP-430 AC-4: the plan said "add OR CHANNEL = 'UNKNOWN' to WHERE clause" but real-data queries already bypass channel filtering entirely.

## Pre-existing test failures

When running tests after a code change reveals failures that predate your changes (stale assertions, `UnnecessaryStubbing` from Mockito strict mode), fix them as part of the crawl.

Attribute clearly in the commit message: "Fixed pre-existing test bug: [description]."

Do not leave pre-existing failures unresolved. They mask whether your changes introduced regressions.

Learned from the KTP-430 crawl: `StatePerformanceBigQueryAdapterTest` had a stale "United States" assertion, and 3 adapter tests had `UnnecessaryStubbing` errors predating the crawl.

## Spec conflict in headless mode

If the code you want to write contradicts the spec, stop.

**Interactive mode:** ask the user whether the spec or the code intent is correct.

**Headless or overnight mode:** spawn an Opus architect agent and a contrarian reviewer agent. Spend tokens analyzing the conflict. If their conclusion is "the spec needs to change", park the task with a written rationale in `tickets/{ID}/reports/status/` and move to the next non-dependent task.

Do not commit spec changes autonomously.

## Ralph loop multi-terminal conflicts

`.claude/ralph-loop.local.md` is per-repo, not per-session. Two terminals in the same repo will fight over it.

When a stop hook feeds a task from another session (wrong ticket, wrong completion promise), do not start working on it. Check the ralph-loop file, confirm it is stale or from another terminal, then `rm .claude/ralph-loop.local.md` to break the cycle.

Never delete blindly without reading the file first.

Learned from 2026-04-01: a KTP-329 loop bled into a KTP-430 session via the shared file.

## Session hygiene

- Create WIP commits at logical boundaries for any session over 30 minutes. Uncommitted code dies with the context window.
- Subagent outputs must be committed immediately. Verify files exist on disk **and** commit before claiming done. Untracked files are wiped by `git clean`, `git checkout`, or repo switches. Learned from the KTP-130 overnight sprint: two repos had full agent-os onboarding as untracked files, nearly lost.
- Scope agent sessions to 2-3 acceptance criteria maximum.
- Separate research from coding. Session A produces docs and plans (committed). Session B reads the plan and writes code. Session C reviews.

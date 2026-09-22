# Skill Proposal: mission-control-night-crawl
Date: 2026-05-01
Source: Mission Control Dashboard repos tab + Phase 5 polish sessions

## Trigger
"advance mission control", "night run on mission control", "crawl the dashboard", "work on the dashboard overnight"

## Scope
repo-local (mission-control-dashboard)

## Draft Steps
1. Read SESSION_STATE.md for current task list and progress
2. Read the active phase PRD (docs/phase{N}/) for requirements
3. Start backend + frontend dev servers
4. Execute tasks in priority order, building after each change
5. Run full Playwright test suite, fix failures
6. Update SESSION_STATE.md with results
7. Launch ralph-loop with completion promise derived from PRD scope

## Why
Mission Control is a personal project without Jira tickets, so sprint-crawl/night-crawl agents don't apply. This skill would standardize the autonomous work pattern: read state, execute PRD, verify, loop.

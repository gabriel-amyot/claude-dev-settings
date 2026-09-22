# Skill Proposal: mission-control-parallel-feature-dev
Date: 2026-04-23
Source: Mission Control Phase 2 build session

## Trigger
When implementing multiple independent features for Mission Control (or similar full-stack dashboard projects) that touch separate files.

## Scope
project-local (mission-control-dashboard)

## Draft Steps
1. Read all files that will be modified to build context
2. Create TaskCreate entries for each feature
3. Launch parallel background agents, each with a self-contained prompt including file paths, code snippets, data schemas, and styling patterns
4. On completion: read all modified files to check for merge conflicts (especially shared files like App.jsx, client.js, main.py)
5. Run `vite build` to verify no import/syntax errors
6. Restart backend, run Playwright suite
7. Fix any integration issues (path conflicts, missing imports, stale test assertions)

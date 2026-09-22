# Skill Proposal: bmad-repo-onboarding
Date: 2026-04-25
Source: KTP-130 overnight sprint — onboarding app-proximity-geoloc and klever-data-workflow

## Trigger
New repo discovered, repo without CLAUDE.md, "onboard this repo", "set up agent-os".

## Scope
global

## Draft Steps
1. Run `/init` to create CLAUDE.md at repo root (or enhance existing)
2. Create `agent-os/` folder with `index.md` (service overview, capabilities, API surface)
3. Dispatch Winston agent to write `agent-os/architecture/` doc (read all source, document patterns, flag debt)
4. Dispatch Amelia agent to write `agent-os/standards/` doc (coding conventions, anti-patterns)
5. Dispatch Leo agent to write `agent-os/product/` spec (Given/When/Then for each capability, gap analysis)
6. Commit all files immediately (don't leave as untracked)
7. Update bibliotheque with repo link

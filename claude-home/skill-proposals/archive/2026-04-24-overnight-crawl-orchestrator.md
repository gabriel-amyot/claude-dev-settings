# Skill Proposal: overnight-crawl-orchestrator
Date: 2026-04-24
Source: KTP-130 Phase 1 overnight crawl session

## Trigger
"run overnight crawl", "dispatch overnight agents", "execute the plan overnight", or when a plan file exists and user says "go to sleep" / "take over"

## Scope
global (works with any ticket that has a plan file with per-repo task breakdown)

## Draft Steps
1. **Pre-flight**: verify repos clean (`git status`), auth fresh (`gcloud auth list`), plan file exists and has been updated
2. **Parse plan**: extract task list, repo paths, branch names, commit strategies from the plan file
3. **Dispatch**: launch one general-purpose agent per repo task in parallel, using the self-contained prompt template (repo, branch, plan path, key details, commit strategy, DO NOT, verification, escalation, report path)
4. **Verify**: after agents complete, `git log` each branch, read completion reports, flag deviations
5. **Housekeep**: update STATUS_SNAPSHOT.yaml, GABRIEL_INBOX.md (morning actions), INDEX.md

## Notes
- Currently manual orchestration in the parent session. Could be automated as a skill that reads the plan file structure and generates agent prompts.
- Distinct from sprint-crawl: this executes an EXISTING plan, sprint-crawl builds its own plan from Jira ACs.
- The prompt template (nugget 4) is the core IP. The rest is sequencing.

# Skill Proposal: pre-crawl-repo-prep
Date: 2026-04-23
Source: KTP-130 night crawl prep session

## Trigger
Before any overnight crawl or autonomous agent session that creates feature branches. "prep repos for crawl", "clean repos", "get ready for overnight".

## Scope
org (Klever)

## Draft Steps
1. Read REPO_MAPPING.yaml (or accept repo list as args) to identify target repos
2. For each repo: check git status, stash dirty state (with descriptive message), checkout dev, pull origin dev
3. Verify clean state (no uncommitted changes, on dev, up to date with origin)
4. Report status table: repo, branch, clean/dirty, stash ref
5. Fail fast if any repo can't be cleaned (e.g., merge conflicts on dev)

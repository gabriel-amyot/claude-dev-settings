# Skill Proposal: docs-repo-navigability-lint
Date: 2026-08-17
Source: app-global-tech-docs MR review session — 7 MRs merged, KTP-866 opened

## Why this is worth a skill

A working checker already exists at `project-management/tools/docs-repo-lint.py`, promoted out of `/tmp` at the end of the session. It found **every real defect** in `app-global-tech-docs` that the eye missed, across seven merge requests:

- 9 orphan pages, including both docs a teammate contributed, invisible in index and catalog
- 3 `../../../` paths that escape the repo and can never resolve in a web view
- 7 new pages with no frontmatter, the only pages in `architecture/` a reader could not classify
- 6 of 7 folders with no `README.md`, which was the actual cause of the "disorienting" complaint

It also produced two false positives that were fixed, and those fixes are the reason it is worth packaging rather than rewriting each time.

## Trigger

- Before sharing a docs repo with a team, or onboarding anyone to it
- Reviewing a docs MR of any size, especially one that adds a section or moves pages
- "is this repo navigable", "can people find things", "why does this repo feel messy"
- After any restructure, as the before/after gate: orphan and broken-link counts must not regress

## Scope

Global. Nothing in it is Klever-specific, though the GitLab README rule is what makes it urgent for Klever repos.

## Draft steps

1. **Export, do not scan the working tree.** `git -C <repo> archive origin/<default> | tar -x -C /tmp/lint`. Scanning a dirty checkout reports defects that are not on the branch, and misses ones that are. This session hit exactly that: an audit reported a diagram defect as live on `main` when the fix sat on an unmerged branch.
2. **Run `tools/docs-repo-lint.py <export>`.** Report order is severity order.
3. **Triage by class, not by count.** Broken links and repo-escaping paths are always defects. Missing frontmatter matters only where the repo's own schema requires it. Missing `README.md` is a defect in any GitLab-read repo.
4. **Read the schema before judging.** The repo's `SCHEMA.md` decides what counts. In this session the schema itself was the defect: it prescribed `[[wikilinks]]`, which GitLab renders as literal text outside a wiki, so following the rule produced ten dead links.
5. **Fix the checker before trusting a dissenting result.** Two false positives were found this way: links inside inline code spans are illustrative, and a folder's `README.md` is reached by clicking the folder so it is never an orphan. A single odd result in an otherwise clean run is usually the tool.

## Checks it should grow

- Wikilink detection (`[[...]]`) flagged as unrenderable in GitLab repo view
- Mermaid: block inventory, node references that resolve, and arrows pointing at a subgraph id rather than a node, which Mermaid 9.1.1 draws unreliably. Hand-rolled twice this session; belongs in the tool
- Bare ticket references not rendered as links
- Catalog coverage: every page has a row in `CATALOG.md`

## Relationship to existing skills

Overlaps `wiki-lint`, which targets the bibliothèque's own structure and conventions. This one targets **any** markdown docs repo read through a web UI. Either fold it in as a mode, or keep separate and cross-reference. Worth deciding before building, rather than shipping a near-duplicate.

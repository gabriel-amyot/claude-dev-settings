# Skill Proposal: mermaid-version-validate
Date: 2026-08-17
Source: KTP-1079 interoperability docs — diagrams failed on GitLab after push

## Trigger
Before pushing any markdown containing ```mermaid blocks to a repo whose diagrams render on
GitLab (mermaid 9.1.1), or any renderer pinned below current.

## Scope
Global. Applies to app-global-tech-docs, project-management, and any docs repo.

## Draft steps
1. Detect the target renderer version (GitLab self-managed = 9.1.1 unless known otherwise).
2. `npm install mermaid@<version> jsdom` into a scratch dir (cached between runs).
3. Parse every fenced mermaid block in the changed files via `mermaid.parse()` under jsdom.
4. Report per-block OK/FAIL with the first line of the parser error.
5. Also lint two known layout traps: a legend expressed as a `subgraph` (renders as a
   full-height column), and `class` statements referencing undefined node ids (block renders
   but silently loses its colours).

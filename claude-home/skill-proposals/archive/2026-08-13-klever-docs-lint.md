# Skill Proposal: klever-docs-lint
Date: 2026-08-13
Source: app-global-tech-docs repo map / mermaid 9.1.1 breakage

## Trigger
Before pushing markdown to a Klever docs repo, or when a diagram renders as
"Syntax error in graph" on GitLab while parsing fine locally.

## Scope
org (Klever). Candidate for app-agent-skills as `klever-docs-lint`.

## Why
GitLab bundles Mermaid 9.1.1. Diagrams valid in a modern editor fail there:
unquoted `~` is a lexical error, unquoted `{}` opens a rhombus mid-edge. Two
diagrams shipped broken for weeks before anyone traced the cause. Relative links
in generated docs also rot silently, and behind IAP a naive HTTP link check
reports every URL broken, so it proves nothing.

## Draft Steps
1. Extract every ```mermaid block from the changed markdown.
2. Parse each against **mermaid@9.1.1** (the version GitLab serves), not latest.
   Report file:line-range and the parser error.
3. Resolve every relative link against the working tree; fail on broken targets.
4. Check repo paths against an authenticated inventory snapshot, never live HTTP
   (IAP makes a plain request fail for existing and missing repos alike).
5. Report a summary; non-zero exit on any failure so it can gate a commit.

## Notes
Steps 1-3 are already implemented ad hoc in this session (a jsdom + mermaid@9.1.1
validator, and a link resolver). Step 4 exists as `map/build_map.py --check-paths`
in app-global-tech-docs. This skill would consolidate them.

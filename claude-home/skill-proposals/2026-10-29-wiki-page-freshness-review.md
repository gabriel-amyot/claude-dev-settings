# Skill Proposal: wiki-page-freshness-review
Date: 2026-10-29
Source: Fact-check of the Proxi Notion wiki page against prod repos and the bibliothèque (KTP-853)

## Trigger
"Review this Notion/wiki page and see if it needs updating", "is this page current", "update this doc with the latest developments". The page is a company-facing description of a system that the org builds.

## Scope
org (Klever-first; generalizable). Read-only until the publish step. Related: `2026-07-07-proposal-factcheck` (stakeholder proposal → code), `notion` skill (local mirror).

## Draft Steps
1. Fetch the page and record `page_last_edited_at`. Extract every claim into a numbered list.
2. Read the org library first: INDEX, ALIASES and any doc-authority map for the topic. Pass those pages to the agent as "Library:" context.
3. Send one read-only agent the claims and the repos, to check on `origin/<deploy-branch>` (fetch, staleness check, deploy-identity). The output is a verdict per claim with evidence, new capabilities split into user-facing and internal ops, doc/code disagreements, and Open Questions.
4. Present a verdict table. Ask only about ownership, contacts and whether to keep the aspirational features. Default: move unbuilt features to a "Planned" section.
5. Write the draft to `tickets/{PREFIX}/{EPIC}/{ID}/reports/notion/`, open it in the browser, run /crit, publish to Notion only on approval, then shelve the drift findings with /operationalize.

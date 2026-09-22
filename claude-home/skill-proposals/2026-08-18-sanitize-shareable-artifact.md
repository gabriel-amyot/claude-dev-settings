# Skill Proposal: sanitize-shareable-artifact
Date: 2026-08-18
Source: session deft-swan — company-wide AI harness talk, audience copy

## Trigger

Any time a locally-built artifact that embeds live org data is about to leave the machine: a deck handed to an audience, an HTML report sent to a stakeholder, a graph export, a dashboard mockup, a knowledge-base extract. Trigger phrases: "send this to", "share the deck", "they want a copy", "can I forward this", "export this for".

Also fires proactively when writing any artifact to `~/Desktop`, an email attachment path, or a shared drive, if that artifact contains an embedded data payload.

## Scope

Global. The risk is not Klever-specific — any harness that embeds a knowledge graph, a tool inventory, or speaker notes has it.

## Why it needs to be a skill

The failure is invisible to visual review. In the source case, 330 real page titles including colleagues' names, job titles, "Organizational Dynamics" and "Team Context" pages, plus vendor commercial evaluations, were embedded in a deck where **none of them rendered on screen**. A human reviewing the slides sees only coloured dots. The leak is one *View Source* away and would have been shipped without an explicit audit step.

Second reason: the ordering constraint is easy to get wrong under time pressure. Cleaning in place after writing leaves a window where an unsanitized file exists on disk.

## Draft Steps

1. **Inventory the payloads.** Find every embedded data blob (`<script type="application/json">`, inlined arrays, base64 assets) and every metadata channel (speaker notes, `data-*` attributes, HTML comments, source maps).
2. **Audit each payload against a risk table** and report findings by severity before changing anything: people names and titles; org/team assessment page titles; vendor or client evaluations and defects; filesystem paths and symlink targets; internal hostnames; credentials, tokens, emails, URLs, IPs. Read any embedded images visually — a screenshot can carry a real client name or live figures.
3. **Decide what the visual actually needs.** Strip anything not drawn. For a node graph, labels and descriptive ids are almost always droppable: replace labels with `''`, remap ids to integers, keep link pairs. The render is identical.
4. **Build the sanitized document fully in memory, then write it to the destination exactly once.** Never write raw and clean in place. Verify afterwards that `created == modified` on the destination, which proves a single write and lets you answer "do I need to retract?" definitively.
5. **Inline external assets** (base64) so the artifact is one self-contained file and cannot break or leak a path when forwarded.
6. **Grep-verify the destination**, not the source, for every specific term surfaced in step 2 plus the standard credential patterns. Expect false positives inside base64 blobs and confirm each hit's context before reporting it clean.
7. **Report a findings table** with severity, what was found, and what was done — so the user can overrule any judgment call (e.g. keeping non-sensitive page titles to make the artifact feel concrete).

## Notes

Pairs with the existing `/post-comment` external-post gate, which covers text going to Jira, Slack and MRs. This covers the other channel: **files** leaving the machine. Consider a PreToolUse backstop that flags a Write to `~/Desktop` or an attachment path when the payload contains a `<script type="application/json">` block over some size threshold.

# Skill Proposal: big-picture-overview-page
Date: 2026-10-25
Source: proxi-cloud-wayfinder (CTO page for Proxi)

## Trigger
"I need a picture of what is happening", "CTO view", "HTML page per audience" after a long-running build.

## Scope
global

## Draft Steps
1. Codex gathers a cited fact base (facts.md) from the run folder, map and live state (saves Claude tokens).
2. UX designer persona (Sally) writes a short UX spec, then ONE self-contained HTML with audience tabs (users/product, engineering/ops, the road = wayfinder graph + timeline), Mermaid with text fallbacks.
3. Codex adversarial review as a demanding CTO; fix; secret scan; open locally.
4. Optional: integrate wayfinder-viewer graph.

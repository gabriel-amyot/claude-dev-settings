# Skill Proposal: zero-dependency-deck
Date: 2026-08-24
Source: KTP-869 Ad-Ops presentation — Mermaid failed repeatedly minutes before a live demo

## Trigger
"Build me a deck / presentation / diagram I am presenting live", especially under time pressure.

## Scope
global

## Problem it prevents
Mermaid 10.9.8 threw "Syntax error in text" on valid-looking diagrams (HTML tags in node labels, a
`/` inside a rhombus label). Upgrading to v11 did not help. Three fix rounds burned the time before
a presentation.

## Draft Steps
1. Default to a single self-contained HTML file: dark theme, arrow-key slides, "all on one page"
   toggle for printing, no CDN and no JS diagram library.
2. Diagrams are flex rows of bordered divs; arrows are a 2px bar plus a `::after` CSS triangle.
3. Fixed colour language with a visible legend (exists / new / future-dashed / warning).
4. Never introduce a parser into anything presented live.
5. If Mermaid is explicitly requested, lint labels first: no HTML tags, no `/` in `{}` labels, no
   subgraph-to-subgraph edges.

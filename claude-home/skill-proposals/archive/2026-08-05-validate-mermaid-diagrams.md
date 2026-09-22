# Skill Proposal: validate-mermaid-diagrams

Date: 2026-08-05
Source: KTP-708 Powers agent decision presentation (many Mermaid diagrams in one HTML file)

## Trigger
Authoring or editing an HTML/Markdown deliverable that embeds Mermaid diagrams (decision decks, architecture pages, reports). Invoke before shipping/opening for the user, and whenever a diagram "looks broken" or shows a "Syntax error in text" box.

## Scope
global (harness/authoring tooling — not Klever-specific)

## Why
Mermaid fails silently to an in-page error box, not a JS exception. Eyeballing the source misses it. Across one session, three separate diagrams shipped broken from special characters that look harmless. A deterministic render-and-scan loop catches them every time.

## Draft Steps
1. Serve the file locally: `python3 -m http.server <port>` in its dir (do NOT rely on `file://` — the claude-in-chrome `navigate` tool prepends `https://` to `file://` and breaks it).
2. Load `http://localhost:<port>/<file>` in a browser (claude-in-chrome). For multi-view/collapsed content, trigger the show/expand so hidden diagrams render.
3. Scan for failures via `javascript_tool`: `Array.from(document.querySelectorAll('.mermaid')).filter(n=>/Syntax error in text/i.test(n.textContent))` and report which diagram (by nearest heading/label).
4. For each broken one, get the exact error with `await mermaid.parse(<source>)` in the console.
5. Fix the known offenders and re-scan:
   - `;` in a sequence-diagram message → comma.
   - `classDef …; class …` on one line in a flowchart → split onto separate lines.
   - parentheses in a `quadrantChart` point label → remove them.
   - diagram inside a collapsed `<details>`/hidden view → render on `toggle`/show (`startOnLoad:false` + `mermaid.run({nodes})` on visible, unprocessed nodes).
6. Confirm `rendered === totalBlocks` and zero error boxes. Kill the server (`lsof -ti tcp:<port> | xargs kill`).

## Notes
Pairs with the inbox nuggets in `documentation/bibliotheque/inbox/2026-08-05-mermaid-validation-and-ttd-agent-surface.md` (#1–6). Could live as a `/verify`-style project skill or a global authoring skill.

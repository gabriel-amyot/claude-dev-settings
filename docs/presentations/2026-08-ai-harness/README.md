# "How I use AI, day to day" — harness talk for a business audience

A ~12-minute talk explaining the agent harness to a mixed, mostly non-technical room. First delivered 18 Aug 2026 at the Klever company-wide AI session, where each person presents how they use AI in rotation.

Keep this. The same ask recurs.

## Files

| File | Use |
|---|---|
| `deck-presenter.html` | **Present from this one.** Speaker notes intact (press `N`). Self-contained. |
| `deck-audience.html` | **Hand out this one.** Speaker notes removed. Everything else identical. |
| `CUE-SHEET.md` | Running order, per-slide budgets, ranked cut list, the lines to land verbatim. |
| `refresh-numbers.sh` | Recompute every count the deck quotes. Run before re-presenting. |

Both decks are single files. No libraries, no network, no external assets. Open in any browser and full-screen it. They work on a plane.

## Controls

`→` / `space` / click advances the reveal, then the slide. `←` goes back. `N` toggles speaker notes. `T` starts a presenter timer (hidden by default, `H` shows it). `Esc` closes an overlay. `1`–`9` jump.

**Slide 2 is the hub.** Three rows expand on click: LIBRARY explodes the knowledge graph, CREW shows the four personas, LINES lists every skill. Slides 4 and 5 enlarge their diagrams. Use the clicks — they land better than describing.

## Shape of the argument

1. I built a workshop and the gates, I do not hand-write the code
2. Four layers: library, crew, lines, rails
3. I open **one folder**, and almost nothing is loaded — progressive disclosure
4. A library, not a chat history. Less context beats more
5. The factory floor, built upside down: tests before code
6. Nothing ships on a claim
7. Never trust the output — the apology *is* the rule, so file it
8. Make it prove, not tell
9. Every mistake pays for itself once
10. Two failures I had to clean up
11. You have to invest the time — roughly a day a week
12. It is not a junior (the conclusion, not the opener)
13. Whatever it makes, it is yours
14. Steal these two things

## What was deliberately cut

Recorded so a future rebuild does not reintroduce them.

- **The career-ladder arc** ("I am a builder", abstraction ladder). Read as too personal for a company room. The "not a junior" comparison survived and moved to the conclusion.
- **Mermaid.** Its v11 `dist/mermaid.min.js` is an ES module, so a plain `<script>` tag never defines the global and every diagram silently renders nothing. All diagrams are hand-drawn inline SVG now. Do not reintroduce Mermaid without testing the render.
- **"I keep the key to every gate."** False. He builds the gates but does not review every step. The deck says *"I built the workshop that writes it, and I built the gates."*
- **"It cannot fix the process."** It can *propose* a fix. Judging the proposal and implementing it is the human's job.
- **The "you lose feel for the material" honesty beat.** Aspirational, could not be sold sincerely.

## Timing

14 core slides, **11:30 planned**. The red line is 15 minutes; 10 is the preference. Reading the content aloud unabridged takes ~26 minutes, so the deck is already cut roughly in half — resist re-adding prose. The cue sheet has a ranked cut list where each cut is self-contained.

## Sensitive-data rule (important)

The deck embeds the real bibliothèque graph. **In the raw source that payload carries every page title**, including a `people` section with colleagues' names and titles, pages named "Klever Organizational Dynamics" and "Klever Team Context", and vendor evaluations (Environics disposition, Goldfish entitlement gap). None of it renders on screen — only section names and dot counts are drawn — but it is one *View Source* away.

**Both decks here are already anonymised**: node labels stripped, ids replaced with integers, skill symlink paths removed. The graph looks and behaves identically. Never ship a copy built straight from `GRAPH_DATA.json` without running the strip below.

Also verified clean: no credentials, tokens, emails, URLs or IPs. The slide 6 screenshot uses the "Taco Chain" seed advertiser, not a real client.

## Rebuild

Source of truth for edits: `project-management/general/presentations/2026-08-18-ai-harness-day-in-the-life/deck.html`.

After editing there, regenerate both copies:

```python
import re, json, base64, os
src = os.path.expanduser('~/Developer/grp-beklever-com/project-management/'
                         'general/presentations/2026-08-18-ai-harness-day-in-the-life')
dst = os.path.expanduser('~/.claude-shared-config/docs/presentations/2026-08-ai-harness')
h = open(f'{src}/deck.html').read()

m = re.search(r'(<script id="GRAPHDATA"[^>]*>)(.*?)(</script>)', h, re.S)
G = json.loads(m.group(2))
idmap = {n[0]: str(i) for i, n in enumerate(G['n'])}
safe = {'n': [[idmap[n[0]], '', n[2]] for n in G['n']],
        'l': [[idmap[a], idmap[b]] for a, b in G['l'] if a in idmap and b in idmap]}
h = h[:m.start(2)] + json.dumps(safe, separators=(',', ':')) + h[m.end(2):]

m = re.search(r'(<script id="SKILLDATA"[^>]*>)(.*?)(</script>)', h, re.S)
S = [s.split(' -> ')[0].strip() for s in json.loads(m.group(2))]
h = h[:m.start(2)] + json.dumps(S, separators=(',', ':')) + h[m.end(2):]

b64 = base64.b64encode(open(f'{src}/assets/proof.png', 'rb').read()).decode()
h = h.replace('src="assets/proof.png"', 'src="data:image/png;base64,' + b64 + '"')
open(f'{dst}/deck-presenter.html', 'w').write(h)

a = re.sub(r'data-notes="[^"]*"', 'data-notes="Shared copy — speaker notes removed."', h)
open(f'{dst}/deck-audience.html', 'w').write(a)
```

Then run `./refresh-numbers.sh` and update slide 2's layer table if the counts moved.

## Caveat

This is a **summary, and an incomplete one**. It shows the harness at a level a business audience can follow. It omits the factories, the eval harness, the session lifecycle, the review cascades and most of the tooling. Do not treat it as documentation of the system.

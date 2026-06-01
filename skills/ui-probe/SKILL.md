---
name: ui-probe
description: "Live runtime inspection of the Klever frontend (portal.dev.beklever.com or localhost) via the user's own authenticated Chrome. THE skill for testing, validating, QA-ing, or debugging the UI when you need ground truth from a running app — not code reading, not the Playwright regression suite. Use whenever the user says 'test the UI', 'validate the UI', 'QA the frontend', 'frontend validation', 'check the UI', 'is the UI working', 'why isn't the UI updating', 'the button/spinner does nothing', 'inspect the live state', 'read the React props/state', 'what's the DOM/console/network doing', or describes a visual/runtime bug they're looking at. It attaches to the user's real Chrome session (inherits Klever IAP + Auth0 — no auth dance), installs a non-blocking DOM sampler, reads React fiber for live props/state, drives a reproduction, and returns a compact, sanitized timeline of DOM + props/state + console + network timing. Pure executor: it reports observable ground truth, it does NOT judge ACs or give UX opinions. Prefer this over klever-test's agent-browser/Playwright-MCP modes for any live UI inspection — those bail on auth; ui-probe reuses the session that already works."
user_invocable: true
nav:
  bay: fix
  when: "Live runtime inspection of the Klever UI: read real DOM, React props/state, console, network timing against the running app. Testing/validating/QA-ing/debugging the UI."
  when_not: "Playwright regression suite (npm run test:e2e, runs headless on its own). Pure backend/API testing (use klever-test backend mode). UX opinion / Sally dogfood judgment (use klever-test mode 4). Processing screenshots you already have (use feedback-to-spec)."
  personas: [quinn]
  org: [klever]
---

# UI Probe

A **probe, not a judge.** It attaches to the user's running Chrome, observes the live app, and returns ground truth: what the DOM actually contains, what props/state React actually holds, what the console actually logged, when bytes actually arrived. It does not decide whether an acceptance criterion passed or whether the UX is good. It surfaces facts; the caller draws conclusions.

This exists because every prior approach to testing the Klever UI failed: Playwright MCP, Playwright CLI, and agent-browser all struggled with auth/IAP, wrong routes, or no live introspection. The method here worked end-to-end against the live dev portal on 2026-06-01 — it found a `useChatbot` contract-drift bug that five prior fixes missed, by reading `isLoading=undefined` straight out of the React fiber. The whole point is reusing the **session that already works**: the user's own authenticated Chrome.

## Why this beats the alternatives

- **No auth dance.** Claude-in-Chrome shares the user's Chrome profile, so it inherits live Klever IAP + Auth0 cookies. A fresh Playwright/agent-browser session has no session to inherit and lands on the Auth0 login wall.
- **Live introspection.** You can read React fiber and computed styles from the running app. A screenshot or a code read cannot tell you that a prop arrived as `undefined`.
- **The user is in the loop.** Klever route guards redirect (e.g. `/proximity-chatbot` → `/planning`). Instead of fighting them with repeated `navigate` calls, the user steers to the screen and the probe operates there.

## When to use vs not

| Situation | Use |
|---|---|
| "Why isn't the spinner showing / button doing anything?" | **ui-probe** — read fiber + DOM live |
| "Validate the UI for KTP-XXX against the running app" | **ui-probe** — observe, return facts |
| "Is the dashboard rendering the right numbers?" | **ui-probe** — read DOM text + network payloads |
| Run the headless e2e regression suite | `klever-test` mode 1 (Playwright, runs on its own) |
| Backend/API assertions only | `klever-test` mode 5 |
| First-user UX opinion, severity-rated | `klever-test` mode 4 (Sally — judgment, not facts) |
| You already have screenshots to triage | `feedback-to-spec` |

## The loop

Keep it tight and interactive. The slow part is always sequential single tool calls and manual waits — batch where you can, fire-and-forget the sampler, and read it back later.

```
attach → (user steers to screen) → install sampler + arm fiber reader
   → drive a short reproduction → read sampler/fiber/console/network → report
   → (repeat the reproduce→read step as needed)
```

### 1. Attach to the user's Chrome

Load the Chrome MCP tools first — they are deferred and must be fetched before use:

```
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__read_console_messages,mcp__claude-in-chrome__read_network_requests,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__navigate
```

Then **always call `tabs_context_mcp` first** — it is required before any other browser action and tells you which Chrome and which tabs are live. If multiple Chromes are connected you will be forced into a `switch_browser`/`select_browser` step; see `references/gotchas.md` for the fast path.

### 2. Let the user steer to the screen

Do **not** auto-`navigate` repeatedly. Klever guards redirect, and repeated navigation clobbers the user's manual steering. State the target screen plainly ("land on Planning → Service Area") and ask the user to get there, then confirm via `tabs_context_mcp` / a single `read_page` before operating. Be explicit about environment — **dev** (`portal.dev.beklever.com`) vs **local** (`localhost:3000`/`3001`) — they have different preconditions and you must know which one you are on.

### 3. Install the DOM sampler + arm the fiber reader

These are the two crown-jewel recipes. Full copy-paste code lives in `references/recipes.md` — read it when you reach this step. In short:

- **DOM sampler:** a `setInterval` (~350–400ms is plenty) that snapshots element presence, `getComputedStyle`, text content, and child counts into a `window.__uiprobe` buffer, with a `setTimeout` auto-clear so it never runs forever. Fire it once, then read it back across turns. This is non-blocking, so it costs no round-trips while a reproduction runs.
- **Fiber reader:** from a DOM node, grab the `__reactFiber$*` key, walk `.return` up to the component, and read `memoizedProps` and the `memoizedState` hook chain. This is the only way to see props/state the screen can't show you (e.g. a prop that arrived `undefined`).

### 4. Drive the reproduction

Use the `computer` tool for real input: click → type → key Return. Watch that the user's bubble/action appears immediately — if it does, the component isn't frozen. Batch independent steps with `browser_batch` to cut round-trips.

### 5. Read back and report

Pull the sampler buffer, the fiber snapshot, console (with a `pattern:` filter), and network. Then produce the compact timeline below. **Sanitize everything** (see Safety) — return types, booleans, lengths, and counts, not raw strings.

## Output: the probe report

Keep it compact and factual. No severity ratings, no "you should." Just what was observed.

```markdown
# UI Probe — {screen} @ {env}
**When:** {date}  ·  **App version:** {if visible}  ·  **Repro:** {one line}

## DOM (from sampler, N samples over Ts)
- {selector}: present {true/false} throughout · display:{...} · text len {n} · children {n}
- {selector}: mounted at sample {k} (~{t}s)

## React fiber (ground truth)
- {Component}.props.{key} = {value-or-type} {"(entire run)" | "changed n→m at ~Ts"}
- {Component} hook[{i}] memoizedState = {value-or-type}

## Console (pattern: "{filter}")
- {line}   ← note: false/null/undefined show BLANK here; confirm via fiber

## Network
- {request}: first byte +{t}s, chunks at +{t1},+{t2}... → {streamed | buffered}

## Observed facts
- {plain statement of what is/isn't true at runtime}
```

When the probe produces a root-cause finding worth keeping, write it to the ticket's `reports/reviews/` folder (e.g. `tickets/{PREFIX}/{TICKET-ID}/reports/reviews/{date}-{slug}.md`), never committed to the app repo.

## Safety — sanitize all returns

`javascript_tool` return values that look like cookies, session IDs, tokens, or query strings get replaced with `[BLOCKED: Sensitive key]`, which silently breaks your read. **Never return raw strings from page state.** Return `typeof x`, `x === undefined`, `x?.length`, `Object.keys(x).length`, booleans, and numbers. You almost never need the raw value — you need to know its shape and whether it's there. This also keeps real secrets out of the transcript.

The blocker reads **key names too, not just values** (verified 2026-06-01: a boolean under a key named `authed` was blocked; `atLoginWall` was fine). So name your return keys neutrally — avoid `auth`/`session`/`token`/`cookie`/`key`/`secret` as substrings in keys, and invert sense if needed. It also flags base64-looking strings, so don't dump raw minified component names. See `references/gotchas.md` for the full set of verified blocker behaviors and the minified-build fiber strategy.

## Gotchas that cost time

Read `references/gotchas.md` before a session — these will burn you otherwise. The big ones:

- **Console bridge renders `false`/`null`/`undefined` as blank.** A blank boolean in `read_console_messages` is not "false," it's "unrenderable." Confirm meaning via fiber or DOM, never infer it from a blank.
- **`javascript_tool` `console.log` is NOT captured** by `read_console_messages` — it runs in an isolated world. Return values from `javascript_tool` instead of logging.
- **Multiple Chromes = selection friction.** Know the fast path before you start.
- **Don't auto-navigate.** Guards redirect; you'll clobber the user.

## What this skill is not

It does not run the Playwright suite, it does not judge acceptance criteria, it does not give UX opinions, and it does not upload to Jira. Those are separate concerns owned by other tools. ui-probe's job ends at a clean, sanitized timeline of runtime facts.

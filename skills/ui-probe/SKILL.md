---
name: ui-probe
description: "Live runtime inspection of the Klever frontend (portal.dev.beklever.com or localhost) via the user's own authenticated Chrome. THE skill for testing, validating, QA-ing, or debugging the UI when you need ground truth from a running app — not code reading, not the Playwright regression suite. Use whenever the user says 'test the UI', 'validate the UI', 'QA the frontend', 'frontend validation', 'check the UI', 'validate this AC/spec against the app', 'is the UI working', 'why isn't the UI updating', 'the button/spinner does nothing', 'inspect the live state', 'read the React props/state', 'what's the DOM/console/network doing', or describes a visual/runtime bug they're looking at. It attaches to the user's real Chrome session (inherits Klever IAP + Auth0 — no auth dance), installs a non-blocking DOM sampler, reads React fiber for live props/state, drives a reproduction, and returns a compact, sanitized timeline of DOM + props/state + console + network timing. By default it also captures a proof screenshot of the final observed state and saves it to disk, so a caller validating a spec gets visual evidence back automatically — pass --no-proof to skip the screenshot. Pure executor: it reports observable ground truth and visual proof, it does NOT judge ACs or give UX opinions. Prefer this over klever-test's agent-browser/Playwright-MCP modes for any live UI inspection — those bail on auth; ui-probe reuses the session that already works."
user_invocable: true
nav:
  bay: fix
  when: "Live runtime inspection of the Klever UI: read real DOM, React props/state, console, network timing against the running app, and capture a proof screenshot of the result. Testing/validating/QA-ing/debugging the UI."
  when_not: "Playwright regression suite (npm run test:e2e, runs headless on its own). Pure backend/API testing (use klever-test backend mode). UX opinion / Sally dogfood judgment (use klever-test mode 4). Triaging screenshots you ALREADY have from elsewhere (use feedback-to-spec)."
  personas: [quinn]
  org: [klever]
---

# UI Probe

A **probe, not a judge.** It attaches to the user's running Chrome, observes the live app, and returns ground truth: what the DOM actually contains, what props/state React actually holds, what the console actually logged, when bytes actually arrived — plus a **proof screenshot of the final observed state**. It does not decide whether an acceptance criterion passed or whether the UX is good. It surfaces facts and visual evidence; the caller draws the conclusions.

The screenshot is **evidence, not a verdict.** Capturing what the screen looks like at the end of a reproduction is squarely a probe's job — it's the visual analogue of the DOM/fiber timeline. Deciding whether that screen *satisfies the spec* is still the caller's job. Producing the proof by default keeps that boundary intact while giving every caller — especially a spec/AC validator — the artifact they always need, without having to ask for it.

This skill exists because every prior approach to testing the Klever UI failed: Playwright MCP, Playwright CLI, and agent-browser all struggled with auth/IAP, wrong routes, or no live introspection. The method here worked end-to-end against the live dev portal on 2026-06-01 — it found a `useChatbot` contract-drift bug that five prior fixes missed, by reading `isLoading=undefined` straight out of the React fiber. The whole point is reusing the **session that already works**: the user's own authenticated Chrome.

## Why this beats the alternatives

- **No auth dance.** Claude-in-Chrome shares the user's Chrome profile, so it inherits live Klever IAP + Auth0 cookies. A fresh Playwright/agent-browser session has no session to inherit and lands on the Auth0 login wall.
- **Live introspection.** You can read React fiber and computed styles from the running app. A screenshot or a code read alone cannot tell you that a prop arrived as `undefined` — so the screenshot complements the fiber read, it does not replace it.
- **Proof comes free.** The same live attachment that reads the fiber can capture a real screenshot of the result and hand it back, so spec validation always ships with visual evidence.
- **The user is in the loop.** Klever route guards redirect (e.g. `/proximity-chatbot` → `/planning`). Instead of fighting them with repeated `navigate` calls, the user steers to the screen and the probe operates there.

## When to use vs not

| Situation | Use |
|---|---|
| "Validate this AC/spec against the running app" | **ui-probe** — observe, capture proof, return facts + screenshot |
| "Why isn't the spinner showing / button doing anything?" | **ui-probe** — read fiber + DOM live (proof screenshot still captured) |
| "Is the dashboard rendering the right numbers?" | **ui-probe** — read DOM text + network payloads + proof shot |
| Run the headless e2e regression suite | `klever-test` mode 1 (Playwright, runs on its own) |
| Backend/API assertions only | `klever-test` mode 5 |
| First-user UX opinion, severity-rated | `klever-test` mode 4 (Sally — judgment, not facts) |
| You already have screenshots to triage | `feedback-to-spec` |

## Invocation flags

Read the invocation text for these before you start; they change the flow:

- **`--no-proof`** — skip the proof screenshot entirely. Use when the caller only wants the fact timeline (e.g. a fast console-only check, or a context where saving an image is pointless). Synonyms to honor: "no proof", "skip screenshot", "no screenshot".
- **`--ticket KTP-XXX`** (or a ticket key anywhere in the prompt) — sets where the proof is saved and how it's named. If absent, infer from context; if still unknown, fall back to the ad-hoc path (see Proof capture).

Default (no flag) = **capture proof.** This is deliberate: the artifact is cheap and almost always wanted.

## The loop

Keep it tight and interactive. The slow part is always sequential single tool calls and manual waits — batch where you can, fire-and-forget the sampler, and read it back later.

```
attach → (user steers to screen) → install sampler + arm fiber reader
   → drive a short reproduction → read sampler/fiber/console/network
   → capture proof screenshot (default; --no-proof skips) → report
   → (repeat the reproduce→read step as needed)
```

### 1. Attach to the user's Chrome

Load the Chrome MCP tools first — they are deferred and must be fetched before use. `computer` is in this set and is what captures the proof screenshot, so always load it:

```
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__read_console_messages,mcp__claude-in-chrome__read_network_requests,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__navigate
```

Then **always call `tabs_context_mcp` first** — it is required before any other browser action and returns every live tab with its URL. Use it to lock onto the **target tab deterministically**:

1. **Match by URL, not by guesswork.** The Klever portal tab is the one whose URL host is `portal.dev.beklever.com`, `portal.beklever.com`, or `localhost:300x`. Pick that tab's `tabId` and pass it to **every** subsequent `javascript_tool` / `computer` / `read_*` call. Other tabs in the group (Google Maps, docs, Jira…) are noise — never operate on them.
2. **Exactly one portal tab → use it.** Pin that `tabId` for the whole session; don't re-resolve per action.
3. **Multiple portal tabs → ask which one** (human in the loop) or pick the one whose URL matches the target screen (unattended). Then pin it.
4. **Zero portal tabs → behave by mode** (this is the one decision that depends on whether a human is present):
   - **Human in the loop (default interactive use):** ask the user to open/focus the portal and steer to the screen. Their already-open tab is known-good, and creating tabs would clobber their manual navigation. Don't `tabs_create_mcp` here.
   - **Unattended / automated (a caller invoked you headless, no human to steer):** `tabs_create_mcp` then `navigate` to the target URL yourself. Cookies are **profile-scoped, not tab-scoped**, so a fresh tab in an authenticated Chrome profile inherits the live IAP + Auth0 session and loads authenticated. This is the correct primitive for background QA — you can't wait on a human who isn't there.
   - **Either way, a fresh tab cannot create auth that isn't already there.** If the profile's session expired (or dev is nightly-off → IAP 302), the new tab lands on the Auth0/IAP wall. That is layer-2 failure, not something a tab trick fixes: report `CANT-TEST(auth-wall)`. ui-probe deliberately does not implement login.
5. **Confirm before driving.** After pinning (or creating) the tab, do one cheap read (a sanitized `javascript_tool` returning `location.pathname` + a key element count) to confirm you're on the expected screen and not a login wall — before any input. If it's the wall, stop and report `CANT-TEST(auth-wall)`.

**If Chrome is not reachable at all** (no connected browser, or you're a headless/QA subagent without the user's session — ui-probe is not drivable from a detached subagent), you cannot read the live app *or* capture proof. Report `CANT-TEST(no-live-chrome)` with what you attempted. Never fabricate a screenshot or a fact timeline.

If multiple Chromes are connected you'll also be forced into a `switch_browser`/`select_browser` step; see `references/gotchas.md` for that fast path.

### 2. Let the user steer to the screen

Do **not** auto-`navigate` repeatedly. Klever guards redirect, and repeated navigation clobbers the user's manual steering. State the target screen plainly ("land on Planning → Service Area") and ask the user to get there, then confirm via `tabs_context_mcp` / a single `read_page` before operating. Be explicit about environment — **dev** (`portal.dev.beklever.com`) vs **local** (`localhost:3000`/`3001`) — they have different preconditions and you must know which one you are on.

### 3. Install the DOM sampler + arm the fiber reader

These are the two crown-jewel recipes. Full copy-paste code lives in `references/recipes.md` — read it when you reach this step. In short:

- **DOM sampler:** a `setInterval` (~350–400ms is plenty) that snapshots element presence, `getComputedStyle`, text content, and child counts into a `window.__uiprobe` buffer, with a `setTimeout` auto-clear so it never runs forever. Fire it once, then read it back across turns. This is non-blocking, so it costs no round-trips while a reproduction runs.
- **Fiber reader:** from a DOM node, grab the `__reactFiber$*` key, walk `.return` up to the component, and read `memoizedProps` and the `memoizedState` hook chain. This is the only way to see props/state the screen can't show you (e.g. a prop that arrived `undefined`).

### 4. Drive the reproduction

Use the `computer` tool for real input: click → type → key Return. Watch that the user's bubble/action appears immediately — if it does, the component isn't frozen. Batch independent steps with `browser_batch` to cut round-trips.

### 5. Read back the facts

Pull the sampler buffer, the fiber snapshot, console (with a `pattern:` filter), and network. **Sanitize everything** (see Safety) — return types, booleans, lengths, and counts, not raw strings.

### 6. Capture proof (default on; `--no-proof` skips)

This is the step that hands the caller visual evidence for free. Do it **after** the reproduction has settled, so the shot shows the *final observed state* the facts describe — that's what makes it proof.

The full mechanism is in `references/recipes.md` (recipe 8). The non-obvious part, verified 2026-06-16: `computer` screenshot with `save_to_disk: true` does **not** write a file or return a path — it delivers the image **inline into the conversation** (base64 in the session transcript) and returns an ID. So:

1. `computer` with `action: "screenshot"`, `save_to_disk: true`, and the pinned `tabId`. This surfaces the image inline — a **direct/interactive caller already has the proof** and needs nothing more.
2. **When the caller is a subagent/automation, or the proof must outlive the conversation** (Jira upload, `sprint-close` evidence, an orchestrator that will `Read` the file), the inline image must become a real file — a subagent's inline image does **not** propagate back to its orchestrator. The bundled helper decodes the latest inline image out of the transcript into the ticket folder:
   ```bash
   DEST="tickets/{PREFIX}/{EPIC}/{KEY}/design/screenshots/{KEY}-{label}-$(date +%Y-%m-%d).png"
   python3 ~/.claude/skills/ui-probe/scripts/save_proof.py --dest "$DEST"   # prints the absolute path
   ```
   (`label` = the AC or a short slug, e.g. `AC2` or `service-area-render`.) With **no ticket context**, use `tickets/_adhoc/ui-probe/$(date +%Y-%m-%d)-{label}.png` and say so in the report. If the helper exits non-zero with "no inline image found," a screenshot wasn't captured — don't fabricate a file, report what you saw in words.

**When the spec is about a *transition*** (a spinner that should appear then clear, a panel that should open on click), one final shot can miss the point — capture a before shot and an after shot and reference both. Use judgment: a static "does X render" needs one shot; "does clicking Y reveal Z" needs two.

If `--no-proof` is set, skip this entire step and note `Proof: skipped (--no-proof)` in the report header.

### 7. Report

Produce the compact timeline below, leading with the proof. Then repeat the reproduce→read step as needed.

## Output: the probe report

Keep it compact and factual. No severity ratings, no "you should." Just what was observed, with the proof front and center so the caller can attach or read it immediately.

```markdown
# UI Probe — {screen} @ {env}
**When:** {date}  ·  **App version:** {if visible}  ·  **Repro:** {one line}
**Proof:** {absolute path to saved screenshot}   ← or "skipped (--no-proof)" / "CANT-TEST(no-live-chrome)"

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

The **Proof** line is the deliverable a caller validating a spec relies on. Make it an absolute path so the caller can `Read` the image or attach it without guessing the working directory. When the probe produces a root-cause finding worth keeping, also write it to the ticket's `reports/reviews/` folder (e.g. `tickets/{PREFIX}/{TICKET-ID}/reports/reviews/{date}-{slug}.md`) — never committed to the app repo. The screenshot itself lives in `design/screenshots/`, not in the app repo either.

## Safety — sanitize all returns

`javascript_tool` return values that look like cookies, session IDs, tokens, or query strings get replaced with `[BLOCKED: Sensitive key]`, which silently breaks your read. **Never return raw strings from page state.** Return `typeof x`, `x === undefined`, `x?.length`, `Object.keys(x).length`, booleans, and numbers. You almost never need the raw value — you need to know its shape and whether it's there. This also keeps real secrets out of the transcript.

The blocker reads **key names too, not just values** (verified 2026-06-01: a boolean under a key named `authed` was blocked; `atLoginWall` was fine). So name your return keys neutrally — avoid `auth`/`session`/`token`/`cookie`/`key`/`secret` as substrings in keys, and invert sense if needed. It also flags base64-looking strings, so don't dump raw minified component names. See `references/gotchas.md` for the full set of verified blocker behaviors and the minified-build fiber strategy.

**Screenshots capture whatever is on screen.** Before you capture proof, make sure no secret is visibly rendered (a token pasted into a field, an open devtools panel showing storage). If the screen shows something sensitive, scroll/close it first or fall back to `--no-proof` and describe the state in words. The screenshot is an evidence artifact saved to the ticket folder, so treat it like any other shared artifact.

## Gotchas that cost time

Read `references/gotchas.md` before a session — these will burn you otherwise. The big ones:

- **Console bridge renders `false`/`null`/`undefined` as blank.** A blank boolean in `read_console_messages` is not "false," it's "unrenderable." Confirm meaning via fiber or DOM, never infer it from a blank.
- **`javascript_tool` `console.log` is NOT captured** by `read_console_messages` — it runs in an isolated world. Return values from `javascript_tool` instead of logging.
- **Multiple Chromes = selection friction.** Know the fast path before you start.
- **Don't auto-navigate** when a human is steering. Guards redirect; you'll clobber them. (Unattended is the exception — see step 1.4.)
- **`save_to_disk: true` does not write a file.** Verified 2026-06-16: it delivers the image inline (base64 in the transcript) and returns an ID, no path. For a durable file, decode it with `scripts/save_proof.py` (recipe 8). A subagent's inline image does not reach its orchestrator, so automation MUST produce the file.

## What this skill is not

It does not run the Playwright suite, it does not judge acceptance criteria, it does not give UX opinions, and it does not upload to Jira. The proof screenshot it produces is raw evidence, not a verdict or an annotated review — turning evidence into a pass/fail judgment, or into Jira-ready annotated captures, belongs to the caller (e.g. `sprint-close`) or to `feedback-to-spec`. ui-probe's job ends at a clean, sanitized timeline of runtime facts plus a screenshot of the state those facts describe.

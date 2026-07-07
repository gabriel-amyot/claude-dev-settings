# UI Probe Recipes

Copy-paste-ready building blocks. Each is designed to run through the Chrome MCP `javascript_tool` (which executes in the page's main world for DOM/React access) and to **return shapes, not secrets** — see the Safety note in SKILL.md.

Tool names assume Chrome MCP loaded via `ToolSearch: select:mcp__claude-in-chrome__*`.

## Table of contents
1. DOM sampler (non-blocking, fire-and-forget)
2. Fiber reader (props + state ground truth)
3. Driving input (click → type → Return)
4. Console read with pattern filter
5. Network timing (streamed vs buffered)
6. Presets (Zustand store, Mapbox, localStorage)
7. browser_batch composition
8. Proof capture (screenshot → save → relocate to ticket folder)

---

## 1. DOM sampler — non-blocking, fire-and-forget

The point: arm a sampler once, run your reproduction, then read the buffer back on a later turn. It costs zero round-trips while the repro happens, and the `setTimeout` guarantees it never runs forever.

Tune `selectors` to what you care about. Resolution of 350–400ms is plenty — finer just bloats the buffer.

```js
// ARM: run once via javascript_tool, returns a confirmation only (not the buffer)
(() => {
  const selectors = [
    '.loading-dots',
    '.progress-indicator',
    '[data-testid="chat-input"]',
    '.chat-message',
  ];
  window.__uiprobe = { samples: [], t0: performance.now(), selectors };
  const tick = () => {
    const t = Math.round(performance.now() - window.__uiprobe.t0);
    const snap = { t };
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (!el) { snap[sel] = { present: false }; continue; }
      const cs = getComputedStyle(el);
      snap[sel] = {
        present: true,
        display: cs.display,
        visible: cs.visibility !== 'hidden' && cs.display !== 'none',
        disabled: el.disabled ?? null,
        textLen: (el.textContent || '').length,   // length, NOT the text
        children: el.childElementCount,
      };
    }
    window.__uiprobe.samples.push(snap);
  };
  window.__uiprobe.iv = setInterval(tick, 400);
  // auto-clear after 60s so it never leaks
  window.__uiprobe.killer = setTimeout(() => clearInterval(window.__uiprobe.iv), 60000);
  tick();
  return { armed: true, selectors: selectors.length };
})();
```

```js
// READ BACK: run later, returns a compact digest (presence transitions + final state)
(() => {
  const p = window.__uiprobe;
  if (!p) return { error: 'sampler not armed' };
  const digest = {};
  for (const sel of p.selectors) {
    const series = p.samples.map(s => s[sel]);
    const mountedAt = series.findIndex(x => x && x.present);
    const last = series[series.length - 1] || {};
    digest[sel] = {
      everPresent: series.some(x => x && x.present),
      mountedAtMs: mountedAt >= 0 ? p.samples[mountedAt].t : null,
      finalDisplay: last.display ?? null,
      finalDisabled: last.disabled ?? null,
      finalChildren: last.children ?? null,
    };
  }
  return { totalSamples: p.samples.length, spanMs: p.samples.at(-1)?.t ?? 0, digest };
})();
```

```js
// DISARM early if needed
(() => { clearInterval(window.__uiprobe?.iv); clearTimeout(window.__uiprobe?.killer); return { disarmed: true }; })();
```

---

## 2. Fiber reader — props + state ground truth

This is what proved `isLoading=undefined` reached the component in KTP-713. React stashes a `__reactFiber$<hash>` property on DOM nodes. Walk `.return` up the fiber tree, read `memoizedProps` and the `memoizedState` hook chain.

> **⚠ Minified builds (the deployed portal): do NOT match by component name.** Verified 2026-06-01 — on `portal.dev.beklever.com`, app components are minified to single letters (`j`, `s`, `f`); only third-party libs keep `displayName`. Matching `displayName === 'ChatMessageList'` finds nothing. Match by **DOM anchor + hop count** or by **prop-key signature** instead (below). Name-matching is a localhost/dev-build-only convenience.
>
> **⚠ Return keys must be neutrally named.** A key literally named `authed` gets `[BLOCKED]`; raw minified names can trip a base64 filter. Return counts, booleans, types, and whitelisted name lists — and avoid `auth`/`session`/`token`/`key` as substrings in your return KEYS.
>
> **⚠ No `data-testid` on the portal** — anchor on classes/structure.

**Return shapes, not values** — `typeof`, `=== undefined`, `.length`, key counts.

### 2a. Preferred on minified builds: anchor by selector + identify by prop signature

```js
// Read the fiber on a specific DOM node, then climb hops looking for a prop signature.
// `wantKeys` = prop names that identify the component you care about (e.g. messages + isLoading = the chat list).
((anchorSelector, wantKeys) => {
  const node = document.querySelector(anchorSelector);
  if (!node) return { error: 'anchor not found' };
  const key = Object.keys(node).find(k => k.startsWith('__reactFiber$'));
  if (!key) return { error: 'no fiber on node' };
  let f = node[key], hops = 0, hits = [];
  while (f && hops < 50) {
    const props = f.memoizedProps || {};
    const keys = Object.keys(props);
    const matched = wantKeys.filter(w => keys.includes(w));
    if (matched.length) {
      const shape = {};
      for (const [k, v] of Object.entries(props)) {
        shape[k] = v === undefined ? 'undefined' : v === null ? 'null'
          : Array.isArray(v) ? `array[${v.length}]`
          : typeof v === 'function' ? 'fn'
          : typeof v === 'object' ? `object{${Object.keys(v).length}}`
          : (typeof v === 'boolean' || typeof v === 'number') ? v : typeof v;
      }
      hits.push({ hop: hops, matchedKeys: matched, propShape: shape });
    }
    f = f.return; hops++;
  }
  return { anchorSelector, hits };   // pick the hop whose matchedKeys best fit; that's your component
})('textarea', ['messages', 'isLoading', 'isStreaming', 'currentStep']);
```

To map the tree first (when you don't yet know the anchor/depth), dump the prop-key sets hop by hop and eyeball where your fields live:

```js
((anchorSelector) => {
  const node = document.querySelector(anchorSelector);
  const key = node && Object.keys(node).find(k => k.startsWith('__reactFiber$'));
  if (!key) return { error: 'no fiber' };
  let f = node[key], hops = 0, chain = [];
  while (f && hops < 40) {
    chain.push({ hop: hops, propKeys: Object.keys(f.memoizedProps || {}).slice(0, 12) });
    f = f.return; hops++;
  }
  return chain;
})('textarea');
```

### 2b. Dev-build convenience: match by component name

Only reliable when names survive (localhost dev build, source-mapped). On the deployed portal this returns "not found" because names are minified — fall back to 2a.

```js
// Read props of the nearest ancestor component matching `componentName`, starting from `anchorSelector`
((anchorSelector, componentName) => {
  const node = document.querySelector(anchorSelector);
  if (!node) return { error: 'anchor not found' };
  const key = Object.keys(node).find(k => k.startsWith('__reactFiber$'));
  if (!key) return { error: 'no fiber on node' };
  let fiber = node[key];
  // walk up to the named component
  let hops = 0;
  while (fiber && hops < 60) {
    const name = typeof fiber.type === 'function'
      ? (fiber.type.displayName || fiber.type.name)
      : (typeof fiber.type === 'string' ? null : fiber.type?.displayName);
    if (name === componentName) break;
    fiber = fiber.return; hops++;
  }
  if (!fiber) return { error: `component ${componentName} not found within ${hops} hops` };

  // sanitize props -> report shape only
  const props = fiber.memoizedProps || {};
  const propShapes = {};
  for (const [k, v] of Object.entries(props)) {
    propShapes[k] = v === undefined ? 'undefined'
      : v === null ? 'null'
      : Array.isArray(v) ? `array[${v.length}]`
      : typeof v === 'function' ? 'fn'
      : typeof v === 'object' ? `object{${Object.keys(v).length}}`
      : typeof v;          // string/number/boolean -> just the type
  }
  // also surface a few critical primitives explicitly (booleans/numbers are safe + meaningful)
  const primitives = {};
  for (const [k, v] of Object.entries(props)) {
    if (typeof v === 'boolean' || typeof v === 'number') primitives[k] = v;
  }

  // hook state chain (memoizedState is a linked list of hooks)
  const hooks = [];
  let h = fiber.memoizedState, i = 0;
  while (h && i < 30) {
    const s = h.memoizedState;
    hooks.push(
      s === undefined ? 'undefined'
      : s === null ? 'null'
      : Array.isArray(s) ? `array[${s.length}]`
      : typeof s === 'object' ? `object{${Object.keys(s).length}}`
      : typeof s === 'boolean' || typeof s === 'number' ? s
      : typeof s
    );
    h = h.next; i++;
  }
  return { found: true, hops, propShapes, primitives, hooks };
})('[data-testid="chat-message-list"]', 'ChatMessageList');
```

If you don't know the component name, drop the walk and just report the chain of `fiber.return` type names to map the tree first.

---

## 3. Driving input — click → type → Return

Use the `computer` tool for real user input (it dispatches trusted events; `javascript_tool` `.click()` can miss React handlers). Confirm the user's action appears immediately — that proves the component isn't frozen.

```
computer: { action: "left_click", coordinate: [x, y] }   // focus the input
computer: { action: "type", text: "show me grocery shoppers in 90210" }
computer: { action: "key", text: "Return" }
```

Find coordinates with a single `read_page` / `find` first; don't guess. Batch the click+type+key with `browser_batch` (recipe 7) when the target is stable.

---

## 4. Console read with pattern filter

```
read_console_messages: { pattern: "useChatbot|SSE|stream" }
```

**Gotcha:** `false`, `null`, `undefined` render as **blank** in the bridge. A blank line next to a boolean label is "unrenderable," not "false." Confirm via fiber. Also: anything you `console.log` from `javascript_tool` will NOT show up here (isolated world) — return it as a value instead.

---

## 5. Network timing — streamed vs buffered

For SSE / chunked responses, the question is usually "did bytes arrive progressively or all at once?" Capture chunk arrival timestamps.

```
read_network_requests: { urlPattern: "/api/.*chat|proximity-report" }
```

Look at the raw chunk byte timestamps. Progressive arrivals seconds apart = streamed. One blob at the end = buffered (often a proxy/`X-Accel-Buffering` issue). In KTP-713 the chunks arrived 2–10s apart, proving the data layer streamed correctly and the bug was downstream in the component.

---

## 6. Presets — common Klever state dumps

Sanitized snapshots of app state. All return shapes/counts, not raw values.

```js
// Zustand map store (if exposed on window or via a known hook anchor)
(() => {
  // Klever often keeps the store accessible; adjust the accessor to the app
  const s = window.__MAP_STORE__?.getState?.() || null;
  if (!s) return { error: 'store not exposed on window; read via fiber instead' };
  return {
    keys: Object.keys(s),
    countyDataKeys: s.countyData ? Object.keys(s.countyData).length : null,
    stateMapDataKeys: s.stateMapData ? Object.keys(s.stateMapData).length : null,
    activePopupId: typeof s.activePopupId,
  };
})();
```

```js
// Mapbox instance health (if a global map ref exists)
(() => {
  const m = window.__MAPBOX__ || null;
  if (!m) return { error: 'no global map ref' };
  return { loaded: m.loaded?.(), zoom: m.getZoom?.(), layers: m.getStyle?.().layers?.length ?? null };
})();
```

```js
// localStorage shape (keys + lengths only, never values)
(() => Object.keys(localStorage).map(k => ({ key: k, len: localStorage.getItem(k)?.length ?? 0 })))();
```

These are starting points — the real accessor depends on what the app exposes. When nothing is on `window`, fall back to the fiber reader (recipe 2).

---

## 7. browser_batch composition

`browser_batch` runs several browser actions in one round-trip. Use it for stable, independent steps (arm sampler + read page + start network capture) to cut latency. Keep anything that depends on a prior result's value out of the batch — batches don't thread return values between steps.

---

## 8. Proof capture — screenshot (inline) → decode to a durable file

The default deliverable. Capture **after** the reproduction has settled so the image shows the final observed state the facts describe. Skip this whole recipe if the invocation passed `--no-proof`.

**Verified mechanism (2026-06-16, Claude Code + claude-in-chrome).** `computer` screenshot with `save_to_disk: true` does **NOT** write a standalone file or return a filesystem path. It delivers the image **inline into the conversation** (base64 embedded in the session transcript) and returns an **ID**. Consequences:

- A **direct / interactive** caller already has the screenshot — it's inline in context. Nothing more to do for them.
- A **subagent** caller does NOT propagate that inline image to its orchestrator (only final text returns). For automation, and for any durable artifact a human or `sprint-close` will open later, you must turn the inline image into a real file. The only handle on the bytes is the transcript, so we decode them out of it with the bundled `scripts/save_proof.py`.

### Step 1 — capture (always do this)

Use the **pinned portal `tabId`**. `save_to_disk: true` is what surfaces the image into the conversation:

```
computer: { action: "screenshot", save_to_disk: true, tabId: <pinned> }
```

For a small detail (a single metric, a legend swatch) prefer a tight `zoom` — it reads better as evidence:

```
computer: { action: "zoom", region: [x0, y0, x1, y1], save_to_disk: true, tabId: <pinned> }
```

The viewport is what's captured — content below the fold won't appear. If the spec target is off-screen, `scroll` it into view first, then capture.

### Step 2 — decode to a durable file (when a file is needed)

Needed whenever the caller is a subagent/automation, or when the proof must outlive the conversation (Jira upload, `sprint-close` evidence bundle, an orchestrator that will `Read` the path). The helper finds the most recent inline image in the session transcript and writes it where you point it. Create the dir is handled by the script. `date` in the shell is fine for the timestamp.

```bash
# Inputs: TICKET, EPIC, LABEL  (LABEL = the AC or a short slug, e.g. AC2 or service-area-render)
DEST="tickets/KTP/${EPIC}/${TICKET}/design/screenshots/${TICKET}-${LABEL}-$(date +%Y-%m-%d).png"
python3 ~/.claude/skills/ui-probe/scripts/save_proof.py --dest "$DEST"
# prints the absolute path on success → put it on the report's **Proof:** line
```

No ticket context? Use the ad-hoc path and say so in the report:

```bash
DEST="tickets/_adhoc/ui-probe/$(date +%Y-%m-%d)-${LABEL}.png"
python3 ~/.claude/skills/ui-probe/scripts/save_proof.py --dest "$DEST"
```

How the helper picks the right transcript: other sessions and background subagents write `.jsonl` files concurrently, so the single newest file in the project tree may belong to someone else and hold no image. The script walks candidates newest-first and returns the first that **actually contains an inline image** — the transcript the capturing agent just wrote. If you know your transcript path, pass `--transcript <file.jsonl>` to skip discovery entirely. The captured bytes are whatever the MCP returned (often jpeg); the file is written verbatim, so the `.png` name is cosmetic — consumers key off the path, not the magic bytes. (If a non-zero exit says "no inline image found," a screenshot wasn't captured this session — don't fabricate a file; report what you saw in words.)

### Step 3 — surface it

Put the **absolute** path (the script prints it) on the report's `**Proof:**` line, so a caller reads or attaches that one file without guessing the working directory. For a transition spec, capture twice (before + after the interaction) — call `save_proof.py` after each, into `…-AC2-before-…png` / `…-AC2-after-…png` — and list both paths.

**Before capturing, glance at the screen for visible secrets** (a token typed into a field, an open devtools storage panel). The image records whatever is rendered and becomes a shared artifact in the ticket folder — scroll/close anything sensitive first, or fall back to `--no-proof` and describe the state in words.

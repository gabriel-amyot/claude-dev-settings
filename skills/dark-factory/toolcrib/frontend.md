# Tool Belt — frontend (Next.js / React UI)

The loadout an agent equips for a **frontend UI** run — a React/Next.js component, a Mapbox GL layer,
a page/route, a sidebar control. The deliverable is something a user **sees and interacts with** in the
browser, not a long-running backend service and not a side-effect script. Snaps into the two sockets:
build station (Implement) and tester station (execution-verify + QA). Tooling validated against
`grp-app/grp-frontend/app-front-portal` (Next 15, React 19, TypeScript 5, Mapbox GL, Playwright).

- **detect:** `package.json` present AND the deliverable is a **rendered UI change** — a React/Next
  component, a Mapbox GL layer/source, a page or route, a UI control/toggle/panel. Distinguish from
  `scripting`: a `.js`/`.ts` whose value is a side-effect (make tiles, transform data, populate BQ) is
  `scripting`, not `frontend`. If the value is what renders on screen, it's this belt.
- **compile / typecheck:** `npm run build` (= `next build`) AND `npm run lint:types`
  (= `tsc --pretty --noEmit --skipLibCheck`). Run the typecheck for fast feedback; the build for the
  full compile + bundle. (The repo's typecheck script is `lint:types`, NOT a bare `tsc --noEmit` —
  confirm the script name in `package.json` before running.)
- **lint:** `npm run lint` (= `next lint`, eslint via `eslint-config-next`).
- **unit test:** **the repo ships NO jest/vitest** — the only test runner is **Playwright**
  (`@playwright/test`, `npm run test:e2e`). So there is no component-unit harness to scope to a single
  component; behavior verification is end-to-end. If a changed module has a pure, isolatable function
  (a selector, a transform, a geo helper), prefer to extract and test it — but do NOT assume a unit
  runner exists. Re-check `package.json` `devDependencies` each run before claiming a unit layer.
- **red (test-first) — and when it is honestly `not_applicable`:** the TDD gate wants a proven RED per AC,
  but this belt has no component-unit runner, so split by AC type:
  - **Extractable pure logic** (a selector, transform, geo/format helper) → write a Playwright
    **pure-function** test (the isolated-function pattern — the only unit-ish layer here), stub the fn so it
    imports, assert the new behavior, run it so it fails on the **assertion**, commit test-only, then GREEN.
    That is a real RED; record it in the ledger.
  - **Pure-render ACs** (a Mapbox layer renders, a toggle shows/hides, a panel appears) have **no unit
    surface** → `exempt: not_applicable(rendered-UI AC, no extractable logic; proof is live visual
    validation)`. The real proof stays the belt's `proof (QA)` (ui-probe screenshot), which QA still gates
    (no screenshot → PARTIAL). **Do NOT manufacture a fake unit test to dodge the gate** (synthetic-data
    anti-pattern) — but do NOT label an AC `not_applicable` if you extracted ANY pure fn: QA re-checks the
    diff, and a found-but-untested pure function makes the exemption bogus → the AC is capped.
- **execute-verify:** `npm run build` (= `next build`) succeeds AND a dev startup smoke
  (`npm run dev` = `next dev`, timeout ~120s) **boots and compiles without a runtime error**. Success
  signal: Next prints `✓ Ready in <N>ms` / `✓ Compiled` for the affected route with no error overlay.
  Then kill it. This is the frontend analog of the java belt's "Started … in N seconds".
  - build + dev boot clean → `execution_verified: "true"`
  - code error (type error, bad import, failed compile, runtime crash on the route) → fix, re-run
  - a backend / data dependency the UI calls is unavailable (e.g. an API route not yet on dev, an
    upstream service down) → `execution_verified: "infra_blocked(<what's missing>)"`. **NEVER fabricate
    API data or stub a fake response to force a pass** (synthetic-data anti-pattern) — surface it.
- **proof (QA):** live AC validation in the **running app** with **screenshots**. Per the project
  CLAUDE.md "Browser Testing Tool Selection" rules, all testing routes through `/klever-test`; for live
  runtime inspection use the **`ui-probe`** skill (preferred — it reuses Gab's authenticated Chrome /
  IAP + Auth0 session, no auth dance), or agent-browser / Playwright. Drive the AC's user flow, capture
  the rendered state, and attach the screenshot as evidence. **Reading the code alone is never a `PASS`**;
  no rendered/visual verification → `PARTIAL`, never `PASS`. If `execute-verify` returned
  `infra_blocked(...)` (the UI's data source isn't live), QA against the documented response contract and
  mark the data-dependent AC `PARTIAL` with the blocker named — do not invent data to claim a green.
- **has_version_file:** yes (`package.json`). **But** frontend CI does **not** push git tags the way the
  Maven backend does (per memory `reference_klever_dac_variable_names` + the KTP-669 lesson — the
  frontend DAC var is `build_docker_tag_version`, no tag-push job). ShipPrep / `/klever-mr` still gates
  the version bump + CHANGELOG entry for this app repo; only the tag-collision concern is backend-specific.
- **port note:** Klever auth only works on `:3000` locally (memory `reference_um_local_ports` /
  `playwright_auth_port_locked`). If a smoke or live-verify needs the authenticated app, free `:3000`
  for the dev server rather than letting Next pick a fallback port.

## Why these tools (rationale, so the next upgrade can argue with it)

Each choice below names the alternative it beat and why, so a future loadout revision is editing a
decision, not a guess.

- **`next build` + `lint:types` for compile, not `tsc` alone.** A bare `tsc --noEmit` type-checks but
  never exercises Next's bundler, route collection, or server/client boundary — the failures that
  actually break a deploy (a server-only import in a client component, a bad dynamic route) only surface
  in `next build`. We run both: `lint:types` is the fast inner-loop signal; `next build` is the truth.
  `--skipLibCheck` is kept because it's the repo's own script — overriding it would diverge the belt
  from what CI runs.
- **`next lint` (eslint-config-next), not a custom eslint invocation.** The repo wires lint through the
  Next plugin (react-hooks, a11y, next-specific rules). Calling eslint directly risks a different rule
  set than CI; mirroring the npm script keeps belt == CI.
- **Playwright as the only test layer, by necessity not preference.** The repo ships **no** jest/vitest,
  so there is no component-unit harness to equip. Inventing one (adding vitest just for the factory)
  would be scope creep into the repo's test strategy — out of bounds for a belt (ADR-002: tools only,
  and we don't restructure the target repo). So the belt's test signal is end-to-end Playwright, and the
  honest note that pure functions *should* be extracted-and-tested where they exist. This is the belt's
  weakest socket and the first candidate the metrics below should pressure.
- **`next dev` boot as execute-verify, mirroring the java belt's "Started in N seconds".** A frontend's
  analog of "the service came up" is "the route compiled and served with no runtime/overlay error". We
  use `next dev` (fast compile, clear `✓ Ready` / error-overlay signal) rather than `next start` (needs
  a full prod build first) for the smoke, then kill. `next build` already covered the prod-compile path.
- **`ui-probe` first for proof, agent-browser/Playwright as fallbacks.** Per the project CLAUDE.md
  browser-tool-selection rules, `ui-probe` reuses Gab's authenticated Chrome (IAP + Auth0), so it clears
  the auth wall that makes headless agent-browser/Playwright bail on the real dev app. Code-reading is
  explicitly disqualified as proof because a rendered map layer / toggle has visual + interaction state
  that source inspection can't confirm.
- **`infra_blocked` over fake data, inherited from the scripting belt's anti-pattern rule.** A frontend
  whose data source (e.g. an API route not yet on dev) is missing is the same honesty problem as a script
  with no real input. Stubbing a fake API response to force a green is the synthetic-data anti-pattern;
  the belt surfaces it as `infra_blocked(...)` and caps the AC at `PARTIAL`.

## Metrics to tune this belt (feed the next factory upgrade)

The factory already writes per-run telemetry (`runs/run-<DATE>-<TICKET>.yaml`, see contract `9-retro`)
tagged with `belt:`. That captures per-**phase** outcomes but **not per-tool** outcomes — which is the
exact signal needed to refine a loadout. To make belt tuning data-driven, capture tool-level signal:

1. **Add a `belt_tools` block to the Retro telemetry** (proposed schema addition to contract 9 — not
   yet wired; this belt is the motivating case). For the run's belt, record each tool's outcome:
   ```yaml
   belt: frontend
   belt_tools:
     - tool: next-build        # compile
       ran: true
       outcome: pass            # pass | fail | skipped | infra_blocked
       caused_deduction: false
     - tool: lint-types
       ran: true
       outcome: pass
     - tool: next-lint
       ran: true
       outcome: pass
     - tool: playwright-unit
       ran: false               # <- the weak socket: how often is there nothing to run?
       outcome: skipped
       note: "no unit runner in repo; no extractable pure fn this run"
     - tool: next-dev-smoke     # execute-verify
       ran: true
       outcome: infra_blocked
       note: "/api/dooh/screens not on dev"
     - tool: ui-probe           # proof
       ran: true
       outcome: pass
       evidence: qa/screenshots/AC1.png
   ```
2. **Three questions the aggregated `belt_tools` data should answer**, each with the action it unlocks:
   - **Which tool is the most frequent source of `caused_deduction: true`?** That tool is mis-specified
     or missing a step → rewrite that bullet. (Hypothesis to test first: the absent unit layer drives
     `PARTIAL` QA verdicts.)
   - **How often is `playwright-unit` / a pure-fn test `skipped`?** A high skip rate confirms the missing
     unit layer is a real gap and quantifies the case for racking a vitest tool in this belt (a real
     change to the repo's test deps, so it needs Gab + owner buy-in — the metric is the argument).
   - **How often does `next-dev-smoke` return `infra_blocked` and on which dependency?** A recurring
     dependency (e.g. a specific API route) is a candidate for a shared local-stack fixture or a
     documented contract-test stand-in, so live-verify stops being blocked.
3. **Cross-run rollup (manual or a future `runs/` aggregator script):** `grep belt: runs/*.yaml` already
   groups runs by belt; once `belt_tools` exists, a small script can emit a per-belt table
   (tool · runs · pass% · skip% · infra_blocked% · deduction-attributed%). That table is the input to
   the next loadout revision: low pass% or high deduction% on a tool = fix that bullet; high skip% on a
   socket = the socket is under-equipped.
4. **Until the schema lands**, the signal still exists in the current telemetry's free-text `deductions`,
   `red_flags`, and `improvements` (the KTP-779 run already attributes lost points to a verification gap).
   A future session can backfill `belt_tools` by reading those fields — but capturing it structurally at
   Retro time is cheaper and lossless.

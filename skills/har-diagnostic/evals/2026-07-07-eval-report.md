# har_parse.py — eval report (2026-07-07)

Target: `~/.claude-shared-config/skills/har-diagnostic/scripts/har_parse.py`. Runner:
`run_har_evals.py`, 8/8 passing. No prior test coverage existed for this script.

Run: `python3 ~/.claude-shared-config/skills/har-diagnostic/evals/run_har_evals.py [-v]`

Method: subprocess the real script against synthetic minimal HAR JSON files, capture
the bounded markdown report it prints to stdout, pin real substrings/counts.

## Fixtures and what each pins

| # | Fixture | Pins |
|---|---|---|
| 01 | error-slow-sse-mix | 500→error, 3.2s→slow, SSE parsed to 2 events; see finding 1 below on `Healthy: 1` |
| 02 | empty-body | 200 + empty body → classified empty |
| 03 | all-healthy | no false alarms; static asset correctly filtered as noise |
| 04 | malformed-entries | no crash on missing request/response fields; see finding 2 below |
| 05 | 3xx-chain-gap | **GAP** — redirects invisible in the report (see below) |
| 06 | unauthorized-401 | 401 → classified error (works correctly) |
| 07 | noise-filtering | mapbox/analytics/static-asset URLs filtered, real API entry kept |
| 08 | invalid-json-file | unparseable JSON at the file level → clean exit 1, no traceback |

## Bugs / gaps found (reported, not fixed — per task scope)

1. **Redirects are computed but never shown or counted anywhere.** `classify()`
   returns `"redirect"` for any 3xx response and `buckets["redirect"]` is populated,
   but `print_report()` has no section for it and the `### Summary` block only
   emits Errors/Empty/Slow/SSE/Data-quality/Healthy — no redirect count at all. Fed
   a 301→302→200 chain, the report shows `Healthy: 1` (the final 200) and the two
   redirects vanish completely: no status code, no count, nothing. This matters
   specifically for this codebase — `gitlab_skill.py` treats a 3xx response as an
   "IAP auth failed (redirect)" signal, and IAP cookie-expiry is a documented
   recurring failure mode. Someone using this HAR tool to debug a redirect-loop
   auth failure (frontend hitting `portal.dev.beklever.com` through IAP) gets zero
   signal that a redirect happened at all.

2. **Entries with a missing/absent `response` (status defaults to 0) vanish
   silently from every bucket, but still count toward "N analyzed."** `classify()`
   has bands for `>=400`, `>=300`, `>=200`; status 0 falls through all of them to
   the final `return "other"`, and `"other"` is not a key in `buckets`, so it's
   never appended anywhere and never reaches `records` in a way that surfaces in
   any report section. Fed 3 malformed entries (no request, no response, and a
   fully empty `{}`), the header says "3 analyzed" but only 1 shows up anywhere in
   the report (as Empty); the other 2 are just gone — no crash, but no error
   surfaced either, and the visible bucket counts don't sum to "N analyzed." A
   reader trusting the Summary tally as a complete accounting of "3 analyzed"
   entries would be misled.

3. **SSE responses are double-classified and can silently inflate "Healthy."**
   `classify()` runs unconditionally on every entry, including `text/event-stream`
   ones, before the SSE branch is checked. A fast (<2s), non-empty SSE body lands
   in the `"success"` bucket via the normal heuristic AND gets its own dedicated
   SSE section. In fixture 01 (1 error + 1 slow + 1 SSE), `Healthy: 1` in the
   Summary is entirely the SSE response — there is no actual fourth "confirmed
   good, ordinary" response. This is defensible behavior (an SSE response that
   returned promptly with parseable events probably is healthy) but it's not
   obvious from the Summary block alone that "Healthy" and "SSE responses" can
   refer to the *same* entry — worth a doc note if this tool is used to eyeball
   "how many normal successful calls were there."

None of the above were fixed — out of scope for this eval-authoring pass, reported
per instructions. Finding 1 (redirects) is the one I'd prioritize if this comes back
for a fix pass: it directly undermines the tool's usefulness for the IAP-redirect
failure mode this codebase already documents elsewhere.

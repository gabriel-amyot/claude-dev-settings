---
name: har-diagnostic
description: Parse HAR files to diagnose API errors, slow responses, data quality issues, and Server-Sent Events (SSE / text/event-stream) streaming responses. Use when user provides a HAR file, says "analyze HAR", "check network", "what's wrong with the API responses", debugging frontend data rendering, or debugging a chatbot/streaming endpoint. Global scope.
nav:
  bay: fix
  when: "Parse HAR files to diagnose API errors, slow responses, data quality issues, SSE streaming responses."
  when_not: "No HAR file. Standard debugging (use /investigate)."
---

# HAR Diagnostic

Parses HTTP Archive (.har) files to surface API errors, performance bottlenecks, data quality issues, and Server-Sent Events (SSE) streaming responses. Produces a priority-ordered report.

A reusable parser ships with this skill at `scripts/har_parse.py`. Do NOT write a throwaway script to `/tmp` — invoke the committed one. It reads the HAR off disk, processes it, and prints a bounded summary so the raw archive never enters context (HAR files are routinely 5-25MB).

**Usage:**
```
/har-diagnostic path/to/file.har
/har-diagnostic path/to/file.har --focus-api /api/chatbot
/har-diagnostic path/to/file.har --sse
/har-diagnostic path/to/file.har --slow-threshold 3000
```

## Step 1: Run the parser

Run the committed script with the HAR path as an argument:

```bash
python3 ~/.claude/skills/har-diagnostic/scripts/har_parse.py <path/to/file.har>
```

Pass flags through as the user requests:
- `--focus-api <prefix>` — only analyze endpoints whose path starts with the prefix (e.g. `/api/chatbot`).
- `--sse` — focus the report on `text/event-stream` responses only; suppresses the rest. Use this when debugging a streaming/chatbot endpoint.
- `--slow-threshold <ms>` — override the 2000ms slow cutoff.

Read the script's stdout. That IS the report. The script handles all parsing, filtering, classification, and SSE decoding internally — you do not need to open the HAR yourself.

## What the parser does

**Noise filtering** — drops static assets (`.js`, `.css`, images, fonts, `.map`), Mapbox tiles/styles, analytics (GA, gtag, segment, hotjar, doubleclick), and `data:`/extension URLs. For Klever HARs this is essential: Mapbox tiles alone can be hundreds of entries.

**Classification** — each kept response is one of:

| Class | Criteria |
|-------|----------|
| Error | Status 4xx/5xx (snippet of body included) |
| Slow | Status 2xx and response time > slow-threshold |
| Empty | Status 200 but body is `[]`, `{}`, `null`, `""`, or <10 bytes — and the reported size confirms it's genuinely small (large bodies the browser omitted from the HAR are NOT flagged empty) |
| Redirect | Status 3xx |
| Success | Status 2xx with a real body |

**SSE handling** (`text/event-stream`) — the reason this skill exists in its current form. For each SSE response the parser:
- Parses the body into individual events (blank-line-separated, `data:` / `event:` lines per the SSE spec, multi-line `data:` concatenated).
- Parses each event's JSON and surfaces `step`, `type`, `event`, and a bounded content preview.
- Reports streaming-relevant headers: Content-Type, Content-Encoding, Transfer-Encoding, X-Accel-Buffering, Content-Length, Cache-Control.
- Flags the structural limitation: HAR captures the whole stream as one body blob, so per-event timing / incremental delivery is not observable. It notes when `X-Accel-Buffering=no` or `Transfer-Encoding=chunked` indicate streaming was intended.
- Warns when an SSE response parsed 0 events (empty stream / server closed early / aborted request) — a common chatbot failure signature.

**Data quality audit** — for JSON success bodies, flags decimal-precision leaks (>6 places), empty strings where null is expected, and inconsistent array object shapes. Bounded depth so it stays fast and the output stays small.

## Step 2: Save the report

Capture the parser's stdout to a file:
- If inside a ticket context (or `--ticket {KEY}` is mentioned): `tickets/{PREFIX}/{TICKET}/reports/reviews/har-diagnostic-{date}.md`
- Otherwise: `/tmp/har-diagnostic-{date}.md`

```bash
python3 ~/.claude/skills/har-diagnostic/scripts/har_parse.py <file.har> > /tmp/har-diagnostic-$(date +%Y-%m-%d).md
```

Then present the key findings inline and tell the user where the full report was saved.

## Notes
- The parser prints a bounded summary by design. If you need raw event payloads beyond the previews, re-run with `--focus-api` to narrow scope, or read the specific entry from the HAR with a targeted `python3 -c` one-liner rather than loading the whole file.
- Pairs with `/klever-test` for diagnosing test failures and with the Dexter agent for deeper debugging.
- For Klever chatbot SSE debugging specifically: `--focus-api /api/chatbot --sse` isolates the streaming responses in one pass.

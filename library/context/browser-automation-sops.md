# Browser Automation SOPs (claude-in-chrome)

Cross-org, hard-won recipes for driving the browser via `claude-in-chrome`. Each recipe is
dated so a future reader knows its vintage against UI drift.

---

## Google Drive — uploading files

*Verified against the Drive UI as of 2026-07.*

Drive exposes **no static file-input in the accessibility tree**, so the naive "find the
upload input and target it" approach fails outright. The working recipe:

1. **Inject the input.** Click **New > File upload** in the Drive UI. This is what injects the
   `<input type=file>` into the DOM. Only after that click can you locate the input's ref.
2. **Upload against the ref.** Find the freshly-injected `<input type=file>` ref, then use the
   `file_upload` tool against it. The **native OS file picker never needs driving** —
   `file_upload` handles it directly. Absolute paths like `~/Desktop/…` are accepted.
3. **Zip multi-folder packages first.** Drive's file-input **lands files flat** — it does not
   preserve folder structure. A package with multiple folders (or duplicate filenames across
   folders) will collide/overwrite on upload. **Zip the whole package first** and upload the
   single archive.

### Transient `find` 529s (folds in the P-7 note)

`claude-in-chrome` tools — `find` especially — can throw transient **529 "overloaded"**
errors. This is a server-side overload signal, not a page bug. Recovery, in order:

1. Retry the call once or twice.
2. If it keeps failing, **fall back to a screenshot + coordinate click** — that path does not
   go through `find` and works when `find` is throttled.

Do **not** wrap browser calls in a blind auto-retry loop: 529 is a load signal and hammering
it amplifies the overload. Manual retry-then-fallback is the established move. (If 529s start
recurring across many sessions and cost real time, revisit a *bounded* retry-with-backoff +
hard cap, matching the pipeline-retry circuit-breaker discipline in CLAUDE.md — not before.)

# verify-code-claims gate — eval + red-team report (2026-07-07)

Target: `~/.claude-shared-config/skills/post-comment/verify-code-claims.py` — the KTP-688 Layer B
deploy-identity stamp gate. It blocks an external post that cites a code location
(`bigquery.py:46`, `sub_agents/data_routing/agent.py:97`, ranges like `foo.py:10-20`) unless the
citation carries a same-line deploy-identity stamp (`[VERIFIED against dev@<sha>]` or
`[UNVERIFIED — read on main, deploy=dev]`). The catastrophe it prevents: handing a code owner
main-based line-refs with false implied authority (the KTP-688 incident).

The gate was NOT modified. Every finding below is encoded as a fixture that pins the gate's
current behavior.

## 1. Deterministic gate evals (`run_code_claim_evals.py`)

28/28 passing. Suite exits 0.

Run: `python3 ~/.claude-shared-config/skills/post-comment/evals/run_code_claim_evals.py`

Coverage:
- **3 seed cases** (plan-required): bare cite blocks; VERIFIED stamp passes; UNVERIFIED stamp
  passes with the "UNVERIFIED" warning surfaced.
- **7 true-positive blocks**: bare cite, multi-dir path, range citation, Java extension,
  second-line-unstamped (per-line scope), backtick-wrapped cite, fenced-code-block cite,
  stamp-on-line-above (per-line scope).
- **5 true-negative passes**: two cites + one stamp on the same line (line-scope rule), multiple
  stamped lines, plain prose, lowercase stamp (case-insensitive), mixed VERIFIED+UNVERIFIED.
- **5 false-positive candidates that correctly pass**: timestamp `12:46`, ratio `16:9`, version
  `python3.11:latest`, time range `10:20-10:40`, filename with no `:line`.
- **1 false positive that is UNAVOIDABLE with the current regex** (pinned, blocks): a CDN/sourcemap
  URL `.../app.js:80`.
- **7 red-team evasions** that dodge the regex and pass unstamped (pinned as KNOWN GAPs).

## 2. Behavior pins that deserve Gabriel's eyes

These were ambiguous in the plan; I ran the live gate, DECIDED, and pinned actual behavior.

| Case | Behavior | Decision |
|---|---|---|
| Citation inside a ```` ``` ```` fence | BLOCKS (exit 2) | Correct. The gate scans physical lines, not markdown. A traceback pasted into a fence is exactly where a main-vs-dev ref must be stamped. Pinned as desired. |
| Stamp on the line ABOVE the citation | BLOCKS (exit 2) | Correct. Stamps are per-line; the stamp must sit on the citation's own line. Pinned. |
| Two citations, one stamp, same line | PASSES (exit 0) | Correct per the documented line-scope rule (one stamp covers every citation on its line). Pinned. |
| Backtick-wrapped `` `file.py:46` `` | BLOCKS (exit 2) | Backticks are not word chars and do not shield the `\b`-anchored match. Wrapping in code font is not an escape hatch. Pinned. |

## 3. Red-team pass (this gate is catastrophe-class)

I adversarially authored natural-phrasing evasions and false-positive candidates, then verified
each by running the live gate.

**False positives caught and confirmed harmless (5):** timestamps, aspect ratios, version pins with
a colon, time ranges, bare filenames. None of these carry a `.<source-ext>:<digits>` shape, so the
regex leaves them alone. Good — the gate does not nuke neutral status updates.

**False positive that survives (1) — needs a human decision:** see the gap table below.

**Evasions caught (regex-covered):** backtick-wrapped refs, ranges (`foo.py:10-20`), multi-dir
paths, and fenced-block citations all still block. The regex is robust to these.

### Surviving evasions (need a gate patch — human decision)

Every item below is a real code-location claim phrased so the regex misses it. The gate returns
**exit 0** (post allowed) with no stamp. Each is pinned as a `# KNOWN GAP` fixture so a future
regex change will trip the eval and force a conscious update.

| # | Fixture | Evasion phrasing | Why it dodges |
|---|---|---|---|
| GAP-1 | `22-evasion-line-N-of-file` | "line 46 of bigquery.py" | No `.py:NN` token; line number precedes the filename. |
| GAP-2 | `23-evasion-file-space-line` | "bigquery.py line 46" | Space instead of `:` between file and number. |
| GAP-3 | `24-evasion-function-at-comma-line` | "src/flow.py, line 94" | Comma + word "line" instead of `:`. |
| GAP-4 | `25-evasion-colon-space` | "bigquery.py: 46" | A space after the colon breaks the `\.py:\d` anchor. |
| GAP-5 | `26-evasion-github-hash-anchor` | "bigquery.py#L46" | GitHub permalink uses `#L`, not `:`. |
| GAP-6 | `27-evasion-parenthetical-line` | "bigquery.py (line 46)" | Parenthesized natural language, no `:`. |
| GAP-7 | `28-evasion-uncovered-extension` | "application.yaml:12" | `yaml`/`yml`/`json`/`xml`/`properties` are not in the extension allow-list. |
| FP-1 | `21-fp-url-with-jsline` | "https://cdn.example.com/app.js:80" | A URL of the form `.../file.js:NN` matches the citation regex and **blocks** a legitimate, non-code-claim post. False positive. |

**Recommendation (human call — the gate was not modified):**
- GAP-1 through GAP-6 are natural-language line references. A regex broad enough to catch them
  ("line \d+ of file", "file line \d+", "file#L\d+") is feasible, but the residual class (prose
  like "the swallow a few lines down") is best owned by an LLM-layer agent rule, mirroring the
  causal-gate split. Suggest: add the mechanical patterns (`#L`, "line N of X", "X line N") and
  hand the rest to a post-comment agent rule.
- GAP-7 is a scope choice: extend the extension list to config files if config line-refs are
  in-scope for the deploy-identity concern, or leave it (config values are less likely to be
  main-vs-dev landmines). Deliberate either way.
- FP-1 (URL) is the one that hurts legit posts. A negative lookbehind for `://` before the path,
  or excluding matches preceded by an unbroken URL scheme, would clear it. Low risk, worth doing.

## 4. Residual risk (honest)

The gate is a regex on a drafted file. It is strong against the shapes it knows (`file.ext:line`
with source extensions, ranges, backticks, fences, per-line stamp scope) and clean on the common
false-positive shapes (timestamps, ratios, versions). Its blind spot is natural-language line
references (GAP-1..6) and config extensions (GAP-7), plus one URL false positive (FP-1). None of
these are regressions — they are the current contour of the gate, now pinned so any change is
visible. The LLM/agent layer remains the backstop for prose that no regex should try to catch.

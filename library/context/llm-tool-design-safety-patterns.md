# LLM Tool Design: Safety Patterns for Side-Effecting Tools

Cross-project design patterns for any CLI or tool an LLM will drive on a human's behalf.
Learned 2026-08-03 building a Claude Code session-recovery tool that simulates keystrokes.
Sections 3 to 6 added 2026-08-31 from the TTD trading MCP's discovery tools, where the
consumer is a model and the caller is an ad trader.

---

## 1. Separate read-only discovery from the one action with side effects

When the "do it" action has a real side effect (here, simulating keystrokes into whatever app
is frontmost), split the tool into at least two subcommands:

- A `find` or discovery command that is always safe to call, has no side effects, and an LLM
  can invoke freely to show the user options.
- An `open` or act command that requires explicit, named targets from the caller, for example
  a repeatable `--session <id>` flag, and refuses to run with none. No "do everything found"
  shortcut. No auto-selection heuristic standing in for a human decision.

**How to apply:** this split directly prevents an LLM from deciding which thing to act on and
executing that decision in the same step. The human, or the LLM relaying an explicit answer
the human already gave, always supplies the target explicitly.

## 2. Never silently collapse multiple real candidates into "the one" — list all of them

A discovery heuristic that picks "the largest matching group" out of several candidates in a
search window silently hides the others. Concretely: an older crash event from about a month
earlier was invisible behind today's larger 21-session cluster, because the tool only surfaced
the biggest cluster in the lookback window.

**How to apply:** list every distinct cluster or candidate group found, with enough summary to
disambiguate: time range, size, a couple of sample identifiers. Let the caller, human or LLM
relaying a human choice, pick which one to drill into for full detail. Do not have the tool
decide which candidate the user meant.

## 3. A list tool returns a complete set or refuses. A labelled partial is not a third option

The tempting design for a large collection is to return the first page with a warning:
`"showing 50 of 408"`. It does not work when the consumer is a model.

The failure, concretely: a trader asks whether advertiser X is on this seat. X sorts 300th of
408. The model receives 50 rows plus the label, and answers "not found". **The label was
advisory prose; the absence claim was the output.** Nothing in the protocol stops a model
reasoning over an incomplete set once it holds one, and the caller cannot tell a real absence
from a paging artefact.

**How to apply:** make the tool a bounded *search* with a required narrowing argument, not an
unbounded *list*. Walk the pages server-side to a complete set and return it, or refuse and
say to narrow the term. The property you are buying is that **an empty result is a reliable
absence claim** — which is most of what a discovery tool is for.

Corollary: **do not expose a cursor or a page parameter.** The walk owns it. A caller-facing
cursor is how a model ends up holding page one of three and reasoning as though it held all
of them.

**Second instance, a CLI rather than an MCP tool (2026-10-07).** `gh issue list` without `--limit`
returns 30 issues. A query that pipes that into a `jq` filter, over a repo holding 153 open issues,
returns nothing when the matching issues are not in the newest 30. "Nothing" reads as "there is no
work", not "the query was truncated". Measured: the same filter returned `0` without `--limit` and
`2` with `--limit 1000`. Always pass an explicit `--limit` when a `gh` list feeds a filter, and
prefer a wrapper that requests a high limit **and raises on saturation**, so a full page is an
error rather than a silent truncation.

The shape to watch for: a hand-written query embedded in a spec or a doc. It gets copy-pasted and
patched in place each time it breaks, and nothing tests it. If a query has broken more than once,
move it into a tested subcommand rather than patch it again.

## 4. Two completeness signals are independent, and either alone fails open

A Relay-style connection reports both `totalCount` and `pageInfo.hasNextPage`. They describe
different things. An upstream that counts the page rather than the set satisfies
`totalCount == len(nodes)` while more rows exist, and an upstream can report
`hasNextPage: false` while `totalCount` says 120 and it sent 50.

**How to apply:** check both, refuse on either. This is cheap and it is the difference between
a silent wrong answer and an error. Watch for it specifically when a paging walk is added
later to code whose single-page reader already checked both: the new walk tends to keep only
the flag.

Related paging trap: **a document that selects `pageInfo { endCursor }` but never declares and
passes `after:` builds a next-page control that returns page one forever.** Every row-count
assertion still passes, because page one has rows. Assert the cursors *on the wire*, not the
returned row count.

## 5. Mark untrusted free text at the value, not once in a header

When a tool returns strings a third party typed (entity names, descriptions, user content),
a single top-level "these fields are untrusted" notice does not survive 200 rows of context.

**How to apply:** wrap each free-text value where it sits, for example
`{"untrusted_text": "..."}`, and add the explanatory notice as well as the wrappers rather
than instead of them. Say in the tool's own description that a name is never an instruction.
Leave ids, enums and numbers unwrapped: they come from a fixed vocabulary and cannot carry a
sentence. Be honest that this is a marker, not a sanitiser — it is the only layer available
when the transport is a language model.

## 6. Facts on the response, never policy in the query

A tool that filters rows on a *judgment* — "campaigns needing attention", "important alerts",
"relevant results" — moves the first half of a decision inside the server, where no human sees
it. The failure is asymmetric and invisible: the row that mattered for a reason your filter
does not model is **excluded**, and a filtered-out row leaves no trace for the caller to
notice. A tool that silently omits the thing you needed is worse than no tool.

**How to apply:** filter only on the caller's own words, a structural scope, or a lifecycle
flag. If the judgment is genuinely useful, return the underlying signals as **neutral fields
on every row** and let the caller filter. Gabriel's formulation, 2026-08-31: *"I don't want an
MCP that is opinionated. I want the MCP to get tools to fetch information, and then to act on
it."* The test that keeps it honest is whether the tool ever drops a row the caller would have
wanted to see.

---

Sections 7 to 9 added 2026-10-07 from session `tidy-heron`, a wayfinder harness failure-mode audit.
All three describe a guard that reported success while the work did not happen.

## 7. A shared agent identity defeats any assignee-based claim check

When "assignment is the claim" and every agent session claims as `@me`, all claims resolve to the
same account. A guard of the form *"refuse if someone other than me holds the claim"* can then
never fire for agent work. It protects against a case that does not occur and misses the one that
does.

Observed: ten tickets held open claims. Nine were assigned inside a **22-second window**, a scripted
batch. One had been held for 16 days. The collision guard passed all ten.

**How to apply:** Give a claim mechanism a **per-session** identity, not a per-account one, or it is
decorative in a multi-agent setting. Where claiming removes work from a queue, build a release path
that does not need the claiming session to still be alive. A session that ends without releasing
starves the queue permanently. Timestamp clustering is a cheap forensic: N assignments inside a
seconds-wide window proves scripted origin, which separates a batch claim from N human decisions.

## 8. An idempotent "resume" branch keyed on weak evidence destroys data

A resume path existed to make retries safe: *if a prior marker exists, do not post a duplicate.* It
keyed on **any** prior marker, including markers of a different kind and malformed ones. On a match
it closed the record and returned **before reading the input file**. A normal command therefore
closed the item, posted nothing, discarded the supplied content, and printed a success message.

**How to apply:** Key an idempotency check on evidence of **the same operation**, not on evidence
that something happened. Classify the marker before you trust it. Validate and read the input
**before** the short-circuit decision. Never return a success path that has not read what it was
given. Treat a malformed marker as a refusal, not as a match.

## 9. A check that returns green on missing input is not a check

Several proposed guards passed when the thing they inspected was simply absent. No declared block,
no manifest, no premise section meant "nothing to verify", so "pass". That reproduces the exact
failure being guarded against, and it is worse than no guard, because it is trusted.

Related: a **read-back** proves storage accepted what you declared. It does not prove the
declaration was correct. A model that wrote a wrong declaration will also approve it, so
self-verification supplies no independent authority.

**How to apply:** Make absence of input `UNKNOWN` or a hard error, never `PASS`. State explicitly
what a green result does **not** cover, for example "no orphans **among labelled items**". Where a
gate needs judgement the acting agent cannot supply, say so rather than ship a gate that will be
believed.

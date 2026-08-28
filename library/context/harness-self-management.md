# Harness Self-Management — Continuous Improvement Ideas

On-demand context: load when improving the harness, planning new hooks/agents, or reviewing cost/context hygiene.

## Philosophy

The harness should manage itself. Human intervention is a smell. Every manual step (checking costs, mining transcripts, pruning old data) is a candidate for automation. Goal: self-managing context lifecycle with zero required human input.

---

## Idea A — Transcript Knowledge Miner (Monthly Agent)

**Problem:** Transcripts at `~/.claude/projects/*/` accumulate decisions, corrections, and tribal knowledge. Too valuable to discard, too voluminous to read manually.

**Solution:** A scheduled agent (cron via `/schedule`) that:
1. Scans all `~/.claude/projects/*/` transcript dirs for unprocessed sessions
2. Extracts: decisions, corrections, procedures, gotchas
3. Writes nuggets to `~/.claude/knowledge-capture/YYYY-MM-DD-HHmm-{slug}.md`
4. Proposes repeatable procedures to `~/.claude/skill-proposals/`
5. Touches a `.mined` sentinel file so each transcript is only processed once
6. Does NOT delete transcripts (retention = 365 days, see cleanupPeriodDays)

**Cadence:** Monthly. Run via `/schedule` with cron `0 3 1 * *` (1st of each month, 3am).

**Status:** Parked. Build when `/schedule` plugin is stable in this setup.

**Note:** The PreCompact hook already captures in-session knowledge. This agent covers historical transcripts the PreCompact hook never saw (sessions before the hook was added, or sessions that never hit compaction).

---

## Idea B — Auto Cost + Context Monitoring (Stop Hook)

**Problem:** `/cost` and `/context` are valuable but require manual invocation. Cache hit rate and context bloat should be logged automatically.

**Solution:** Extend the Stop hook to append a cost summary to a log file.

**Hook sketch (add to Stop hooks in settings.json):**
```json
{
  "type": "command",
  "command": "echo \"{\\\"date\\\": \\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\", \\\"session\\\": \\\"$CLAUDE_SESSION_ID\\\"}\" >> ~/.claude/cost-log.jsonl",
  "async": true
}
```

**Dependency:** `/cost` command must support machine-readable output (JSON). Verify with `/cost --json` before implementing. If not available, use a prompt hook to parse and emit the output.

**Downstream:** A companion monthly agent reads `~/.claude/cost-log.jsonl`, detects anomalies (cache hit rate <20%, session cost spikes), and writes a digest to `~/.claude/knowledge-capture/`.

**Status:** Parked. Verify `/cost --json` availability first.

---

## Idea C — Batch API Wrapper for Long-Running Agents

**Problem:** `sprint-crawl`, `night-crawl`, and `dev-crawl` run at full real-time API cost. Overnight and background jobs don't need immediate results.

**Solution:** A `batch-wrap.sh` that routes agent calls through Anthropic Batch API (50% cost reduction, async).

### Invocation Design

```
/sprint-crawl KTP-XXX              → batch mode ON (default)
/sprint-crawl KTP-XXX --no-batch   → real-time (immediate results)
```

**Startup banner the agent must emit:**
```
🔄 BATCH MODE active — 50% cost reduction. Results: 15min-2h delay.
   Skip with --no-batch for immediate execution.
```

### Implementation Sketch

**`~/.claude/scripts/batch-wrap.sh`:**
1. Parse args, detect `--no-batch` flag
2. If `--no-batch`: exec agent directly, exit
3. If batch: serialize invocation as Batch API request
4. Poll until complete (exponential backoff, max 4h)
5. Pipe result back to caller
6. Log mode + cost to `~/.claude/cost-log.jsonl`

### Skills to Update

| Skill | Notes |
|-------|-------|
| `sprint-crawl` | First target. Most used. Batch default suits ticket work. |
| `night-crawl` | Overnight by design — batch is ideal. Always default ON. |
| `dev-crawl` | Add `--no-batch` note prominently: dev validation needs fast feedback. |

### Build Order
1. Build and test `batch-wrap.sh` standalone (use a simple echo agent first)
2. Wire into `sprint-crawl`, test one real ticket
3. Port to `night-crawl`, `dev-crawl`
4. Update each skill's description to document `--no-batch`

**Status:** Ready to build. Start with batch-wrap.sh scaffold.

---

## Cleanup Policy

- `cleanupPeriodDays: 365` — Keep all transcripts for 1 year. Review only if `~/.claude/projects/` exceeds 5GB.
- If storage threshold hit: run transcript miner (Idea A) first, THEN prune oldest sessions.
- Never prune without a mining pass. Knowledge first, storage second.

---

## Gotcha — Local plugin edits don't go live until synced to the cache copy

**Discovered:** deft-falcon session, 2026-06-11, fixing the `session:check` close flow.

Local plugins exist as TWO copies on disk:
- **Source (editable):** `~/.claude/plugins/local-marketplace/{plugin}/...`
- **Cache (loaded):** `~/.claude/plugins/cache/local/{plugin}/{version}/...`

`~/.claude/plugins/installed_plugins.json` is authoritative: its `installPath` points at the **cache** copy, and that is what Claude Code actually loads and runs. **Editing the marketplace source alone changes nothing at runtime** — the edit stays invisible until the cache copy is updated (a plugin reinstall, or a manual copy).

This bites silently: the two can drift (observed: source newer than the loaded cache by days), so a skill can run *older* logic than the source file on disk shows. Symptom: "the skill isn't behaving the way its SKILL.md reads."

**Rules when editing any local-plugin skill/hook:**
1. Find the live copy: `installPath` in `installed_plugins.json` (it's the `cache/local/...` path).
2. Edit the **source** (`local-marketplace/...`) so future reinstalls keep the change, THEN sync to the cache copy.
3. Sync with `/bin/cp -f` — interactive `cp` is shell-aliased to `-i` and will silently decline to overwrite in a non-interactive Bash tool call.
4. Verify with `diff -q source cache` (expect identical) and grep the cache copy for a marker string from your edit before claiming the fix is live.
5. If the source was already *newer* than cache before you started, `diff` them first — you may be about to push someone's un-synced changes live alongside yours. Review that diff, don't blind-sync.

---

## Gotcha — Subagents Blocked From Writing Report Files Looks Like "Agents Died Silently"

**Discovered:** KTP-830 dusk-owl session, 2026-08-07.

A PreToolUse guard blocks subagents from writing report `.md` files, by design: "Subagents should
return findings as text, not write report files. Include this content in your final response
instead." Three builder agents finished their work, hit this guard when trying to write their
report-backs, and went idle without a report on disk.

**The failure mode is misdiagnosis, not the guard.** Reading "no report file on disk" as "the agent
died silently before reporting" is the wrong conclusion — it produced an incorrect status document
in this session, corrected only after one agent explicitly said the guard had denied its write
twice.

**How to apply:** When a subagent finishes with no report file where you expected one, check
whether it returned the content as text in its final message before concluding it failed or died.
Word dispatch prompts to say "return the report as your final message," not "write it to
`<path>`" — the guard exists specifically because subagents are supposed to return text, and a
prompt that tells them to write a file works against it.

---

## Gotcha — `find` under `~/.claude` intermittently returns empty for directories that demonstrably exist

**Discovered:** session amber-finch, sprint-skill consolidation work, 2026-08-24.

`find ~/.claude/skills -maxdepth 1 -type d -iname "*sprint*"` returned an empty result twice in one session, despite `sprint-close`, `sprint-estimation`, and `sprint-factory` sitting right there. `ls -la ~/.claude/skills | grep -i sprint` found them immediately on the next command, same shell, same working directory. No permission issue or symlink loop explained the gap.

**How to apply:** Do not trust a single empty `find` result under `~/.claude` as proof a skill, agent, or directory does not exist. Confirm with `ls -d */ | grep` or plain `ls` before concluding absence.

---

## Gotcha — `file-guard.sh`'s CLAUDE.md protection matches the literal string anywhere in the Bash command, not just as a file-path argument

**Discovered:** session amber-finch, sprint-skill consolidation work, 2026-08-24.

Running `rm -f /tmp/some_temp_file.py` in the same Bash call as an unrelated `grep` targeting `./CLAUDE.md` gets the whole compound command blocked: "command references a protected path (CLAUDE.md) alongside a destructive operation (rm/mv/unlink/shred/truncate)." The `rm` target has nothing to do with CLAUDE.md. The guard does a plain string match (`grep -qF`) across the entire command text, not a check scoped to the argument actually being deleted.

**How to apply:** Split commands so a protected filename never co-occurs textually with `rm`/`mv`/etc. in the same Bash call, even when the two are logically unrelated.

---

## Gotcha — A heading-scoped `sed` range can silently return empty even when the row is present

**Discovered:** session `deft-pike`, close-gate/archival session (2026-08-17).

Checking a table insert with `sed -n '/^## Pending (awaiting curation)/,/END-PENDING-ROWS/p' | grep '^|'` returned nothing and read as "the row is missing." The row was fine; the range expression was wrong (an anchor pattern that didn't match, or matched the wrong occurrence first). A `grep -n` for both the row text and the anchor line gives line numbers that settle placement in one shot, and the row must sit immediately above the anchor — an earlier match on the same anchor pattern is often the instruction comment that documents the convention, not the anchor itself.

**How to apply:** When a verification command returns "absent," confirm the command can detect "present" first (test it against a known-good case) before acting on the absence as a finding. A verification that cannot fail is not a verification.

---

## Gotcha — A skill count is a poor bloat metric; description tax is the real cost

**Discovered:** session crisp-jackal, `/operationalize-audit` skill-retirement pass, 2026-08-18.

The harness carried a "120 skills" alarm as its bloat signal. Gabriel challenged it: a narrow
skill that fires only in one scenario is not the same cost as a generic one that mis-fires
weekly. He is right, and the reason is mechanical. Skills load in two stages. Only the name and
description load at session start. The body loads on invocation. So the standing cost of the
skill set is the sum of its descriptions, paid every session regardless of use.

Measured at 115 skills: 43,385 description characters, about 10,800 tokens, every session. The
20 most expensive descriptions were 34% of the total. The remaining 95 skills cost little.

Two numbers replace the count:
- **Total description characters** — the standing tax.
- **Generic-word density** — the mis-fire risk. `ui-probe` is the most expensive single skill
  (1,454 characters) but only 1.3% generic, so it earns its cost. `jira` (609 characters, 17.5%
  generic) and `crawl-adversarial-review-cascade` (742, 17.2%) fire on situations they were not
  written for.

**How to apply:** judge a skill-retirement or new-skill proposal on description cost and trigger
precision, not on a count ceiling. Scanner: `~/.claude/skill-proposals/skill_tax_scan.py`.

## Gotcha — Zero invocations in a transcript scan does not mean a skill is dead

**Discovered:** session crisp-jackal, `/operationalize-audit` skill-retirement pass, 2026-08-18.

A transcript scan found 69 of 115 skills never invoked in 90 days. Three classes of that silence
were measurement error, not death:

- **Cron-invoked.** `skill-evals` runs monthly from launchd (`com.harness.skill-evals-monthly`).
  A cron job runs outside any session and writes no transcript, so a transcript scan cannot see
  it by construction.
- **Too new.** `ghostty-recover-sessions`, `klever-dev-portal`, and `um-local-grant` were all
  under 30 days old. A 90-day window is a category error for a skill that young.
- **Referenced in prose the scanner did not match.** `inbox-writer` was archived, then restored:
  `skill-evals` names it as the escalation path when the monthly sweep needs a human decision.
  The reference pattern required backticks and missed `**inbox-writer** skill`.

A fourth class is real but different: **referenced but never run.** A skill that config points at
yet nobody invokes is either a dead reference or a documented rule being quietly ignored.
`klever-test` is named in the Klever CLAUDE.md as the entry point for all UI testing and has zero
invocations, while `ui-probe` has 37, because `klever-test`'s own SKILL.md delegates live UI work
to `ui-probe` by design. The rule reads as a funnel that is bypassed on purpose.

**How to apply:** before retiring a skill on a zero-invocation count, exclude cron-invoked and
too-new skills, search for trigger phrases rather than the skill name, and check whether anything
still points at it.

## Gotcha — Check hook registration in `settings.json` before diagnosing its logic

**Discovered:** session crisp-jackal, `/operationalize-audit` skill-retirement pass, 2026-08-18.

`config-protect.sh` was traced under `bash -x` and found inert: its JSON key extraction is
over-escaped, so it always returns the default and exits 0 on every input. It was reported as a
live broken safety guard. It is not. It is decommissioned and unregistered. `file-guard.sh`
records this in its own header: "Replaces: config-protect.sh (superseded, kept on disk but not
registered)." An unregistered hook's bugs are theoretical.

**Diagnostic order for any hook:**
1. `grep -n '<hook>' ~/.claude/settings.json` — if absent, it never runs and nothing else matters.
2. `bash -x` with a realistic payload; read the assigned variables. Payload shape differs per
   hook: some read `tool_input.file_path` from stdin, others read a `CLAUDE_TOOL_INPUT`
   environment variable holding the tool_input object directly. Do not assume the shape.
3. Assert the exit code, and assert stderr is non-empty on a block.

## Gotcha — zsh does not word-split an unquoted variable in a `for` loop

**Discovered:** session crisp-jackal, `/operationalize-audit` skill-retirement pass, 2026-08-18.

`LIST="a b c"; for s in $LIST` iterates once in zsh, with the whole string as a single item,
unlike bash. A loop written that way silently does nothing useful and reports success. This was
caught only because a guard (`[ -d "$s" ]`) failed and printed a SKIP for the entire concatenated
string.

**How to apply:** write an explicit literal list in the `for` statement, or use `${=LIST}` for
zsh word-splitting. Any loop over a variable list should print a count at the end, so a
zero-iteration bug is visible.

## Gotcha — "No evidence" from a sample that excludes the source is weak disconfirmation

**Discovered:** session crisp-jackal, `/operationalize-audit` skill-retirement pass, 2026-08-18.

A subagent analyzed six large sessions and returned no evidence for two proposed skills. Neither
proposal originated in those sessions: one came from a pressure-test skill review, the other from
`app-global-tech-docs` MR work, and neither session was in the sample. Absence in a sample that
excludes the source does not disconfirm the proposal. For the docs-lint case the real evidence
sat on disk rather than in transcripts: a working checker already existed, with two false
positives recorded in its own docstring as found and fixed.

**How to apply:** before accepting a negative finding from a delegated agent, ask what the sample
could not have contained. This applies to your own delegated agents, whose verdicts read as
authoritative.

## Gotcha — CLAUDE.md is not persisted into transcript JSONL, so its rules leave no trace of being loaded

**Discovered:** Klever session, CLAUDE.md rule-firing measurement over 1,642 transcripts, 2026-08-27.

The always-loaded instruction files are injected at session start but do not appear in the session's
JSONL. A scan of transcripts therefore cannot answer "was this rule in context?" — only "did anyone
write its words." Every rule was in context every session, by construction.

**How to apply:** never treat transcript silence as evidence a rule was absent. It measures citation,
not loading. This is the sibling of [[zero-invocations-not-dead]]: the artefact records what was said,
not what was known.

## Gotcha — Documentation echo is the dominant false positive when scanning for rule usage (~13:1)

**Discovered:** same measurement, 2026-08-27.

Rule text mostly enters a transcript because the agent **read a file containing it** — CLAUDE.md
itself, a library page, a proposal — not because the agent applied the rule. Split by channel, one
rule scored 102 hits in `tool_result` content against 8 in assistant text or thinking. Counting all
message types together inflates the apparent usage of every documented rule by roughly an order of
magnitude, and inflates it *most* for the rules that are best documented.

Uncorrected, a naive count said 87 rules were well-cited. Restricting to assistant-authored channels
dropped that to 18.

**How to apply:** when scanning for evidence that an instruction is used, count only assistant-authored
channels (text, thinking, tool_use inputs). Exclude `tool_result` and file-read content, or you will
measure your own documentation reading itself.

## Gotcha — A phrase unique to one rule is not therefore rare in the corpus

**Discovered:** same measurement, 2026-08-27.

Probe phrases are usually chosen for being distinctive *within the ruleset*, then used as if they
were distinctive *in the transcripts*. Those are different properties. The commit-message rule's
probe token `message` is unique among the rules and appeared in 888 of 1,051 sampled sessions.

Applying a corpus-frequency gate on top of the channel correction dropped the well-cited count from
18 to 1.

Field scoping matters for the same reason. Matching a whole Bash command string for `terraform
plan/apply` suggested 122 sessions; restricting the match to the `command` field and requiring
terraform as the command word confirmed 3.

**How to apply:** measure each probe's document frequency in the corpus before trusting its hits, and
scope structured matches to the specific field. A probe that fires in half the corpus is measuring
English, not the rule.

## Gotcha — Two diverged copies can share a filename and be different documents

**Discovered:** merging the unversioned working library into the versioned
`~/.claude-shared-config/library/`, 2026-08-27.

Seven filenames collided during the merge. None were stale copies of each other:
`context-engineering.md` was the general theory on one side and the Klever operational
protocol on the other; `shipping-workflow.md` was Supervisr JIB tagging versus the Klever
GitLab flow; `ticket-quality-standards.md` was the authoring contract versus the closure
workflow. "Bigger file wins" or "newer wins" would have destroyed real content in every pair.
The `-legacy` suffix on the losing side marks a pending curate pass, not a resolved
duplicate.

**How to apply:** in any two-way merge, diff the structure (headings, top-level keys) of each
colliding pair before picking a winner. If either side has headings the other lacks, they are
different documents. Preserve both under distinct names and curate later; a same-name
collision is not evidence of duplication.

## Gotcha — A lint that skips non-prose lines can exempt the very lines it must check

**Discovered:** building `claude-md-tier-lint.py`, 2026-08-27.

The lint skipped headings, blockquotes, and fences before running its content check.
Headings are exactly where provenance hides — `## Rule (Learned from KTP-130 ...)` — so the
lint reported clean while six such headings sat in the files. Every "tier lint clean" claim
before the fix was false.

**How to apply:** apply a skip pattern only to the checks that genuinely need it, never as a
blanket pre-filter. Verify against a fixture that contains the violation in each line type a
skip pattern could hide it in.

## Gotcha — Fence tracking needs the fence character and run length, not a toggle

**Discovered:** same lint build, 2026-08-27.

Fixing the heading-skip bug above by checking every line introduced a false positive inside
code fences. Fixing that with a naive backtick-count toggle desynchronised on a valid
four-backtick fence containing a literal three-backtick line: the inner line closed the fence
early, so prose inside was linted and real provenance after it was missed. Both directions
wrong. CommonMark rule: a fence opens with 3 or more of the same character (backtick or
tilde), and closes only on the same character, with a run at least as long as the opening,
followed by nothing but whitespace.

**How to apply:** never toggle fence state. Record the character and opening length. Test
with tilde fences, info strings, unbalanced fences, and a longer fence containing a shorter
one.

## Gotcha — `git status` silence means tracked-and-clean, not untracked

**Discovered:** `settings.json` versioning session, 2026-08-27 (same day as the git-pipe rule
retirement in `mechanical-backstops.md`).

`git status --porcelain -- <path>` returning nothing was read as "this file is not tracked,"
and reported as a version-control gap. It actually meant tracked and unmodified. The real gap
was different and worse: two different `settings.json` files existed, a live untracked one
with 30 hooks and a tracked one with 1 hook, model `sonnet` against `opus`, and 23 inactive
permission rules. Symlinking naively would have swapped the working configuration for the
stale one and disabled 29 hooks.

**How to apply:** test tracking with `git ls-files --error-unmatch <path>`, never with status
silence. Before symlinking any config into a versioned location, diff both sides; "the
versioned one is the real one" is an assumption, not a fact.

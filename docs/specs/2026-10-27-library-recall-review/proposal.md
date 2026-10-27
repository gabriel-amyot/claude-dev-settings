# Library recall: proposal (merged from the Claude and Codex reviews)

Date: 2026-10-27. Scope: the `bibliotheque-recall.sh` hook, both ALIASES tables, and routing knowledge writes to the library instead of auto-memory.
Sources: `claude-review.md` (written first, blind), `codex-review.md` (Codex, high effort, blind to the Claude review, verdict REDESIGN), `recall-report.md`, `judge-results.jsonl`.

## Status after Codex round 2: BLOCKED until the measurement is repaired

`codex-review-r2.md` blocks Phase 0. Claude verified each must-fix with `verify_r2_claims.py`:
- `measure_recall.py` ignores user prompts with list content (53 prompts, text or image). It credits their hook output to an earlier prompt: **126 pointers misattributed**. All counts below (782, 513, 5.84, 63.8%) must be rebuilt.
- The 45-day window filters files by modification time. The corpus reaches back to 2026-09-01.
- The 2.6% open rate counts path mentions in tool arguments, not successful reads. It misses subagent and delayed reads. Treat it as a proxy only.
- The judge sample has 59 distinct prompts, and 34 were cut at 300 characters. One model, no adjudication. "22% relevant" is provisional.

Still valid, because live replays prove them independently of the transcript metrics: the stem double-count (#2), machine prompts triggering the hook (#3, reproduced twice in this session), the broken `~` and annotated rows (#5), and the scope bugs (#8, #9).

**Correction to #5:** the annotations encode the real location (rows 805-809 name the global library). Stripping them leaves a path that does not exist. Each row must be repaired to its real destination.

**New order:**
1. Measurement v2: handle list-content prompts, filter by event timestamp, scan subagent transcripts, count only successful Reads. Freeze the corpus and the hook version as the baseline.
2. Relabel: full prompt and page context, 200 calibration pairs plus 200 held-out pairs across at least 50 sessions, and a second rater on a subset.
3. Phase 0, one switchable change at a time, with shadow logging and a rollback.
4. Before any Phase 1 deny: trigger IDs, owners, exclusions (test fixtures, other orgs, scratch clones the user asked for), a per-trigger kill switch, and shadow mode first. An advisory "inform" cannot stop a command that is already chosen, so the `cd` case needs a deny or nothing.
5. Phase 3: Codex now recommends option B with a legacy-read router. Disabling auto-memory stops the automatic load, but the files stay readable. Gabriel decides.

## Verdict

Keep the library. Redesign the retrieval around it. The prompt-keyword hook now delivers mostly noise:
- 62% of sampled pointers are noise and 22% are relevant.
- 2.6% of pointers get opened.
- Machine prompts receive pointers too.

The hook also cannot see the moment most mistakes happen: when the agent picks a command mid-task.

## Verified findings (both reviews, rechecked against the code)

| # | Finding | Type | Proof |
|---|---|---|---|
| 1 | Retrieval runs on the human prompt. Mistakes happen at action time (the `/tmp` clone) | Design | Incident on 2026-10-27. The clone rule exists (ALIASES row 1665) and could not fire |
| 2 | One generic word passes the threshold: the hook counts the word and its stem as two hits | Bug | "patterns" alone gives 1 pointer, "reviews" alone gives 5, "checking" alone gives 2 |
| 3 | Machine prompts (task notifications, system reminders) trigger the hook | Bug | 94 machine prompts got 513 pointers. Reproduced live in this session |
| 4 | A page fires at most once per session, and a machine prompt or an off-topic prompt can use up that one chance. Compaction does not reset it | Bug | Hook lines 115-116 and 148-151 |
| 5 | `~` paths and annotated path cells produce unopenable pointers | Bug | 9 + 16 rows. A broken path was injected 24 times |
| 6 | No rarity weighting: common words count the same as specific ones | Design | Judge: noise clusters on "review", "check", "merge", "fix", "resolved" |
| 7 | ALIASES works as a wikilink table, not an applicability index. 37% of Klever pages have no row, and one page has 41 | Data | `recall-report.md` |
| 8 | Any prompt containing "library" suppresses recall, including ordinary software-library work | Bug | Hook lines 55-57 |
| 9 | Org detection uses a string prefix, so a sibling folder with the same prefix matches | Bug | Hook line 43 |

## Plan

### Phase 0: bug fixes (1 day, low risk)
1. Skip machine envelopes: an anchored match on `<task-notification`, `<system-reminder`, `<command-`, `<local-command`, `Caveat:`. A skipped prompt does not change the session's dedupe state.
2. Count each word once, after normalizing word and stem to one form.
3. Normalize paths: expand `~`, strip `(…)`, canonicalize. Add a librarian lint that fails when a row's path does not exist.
4. Narrow the "library" suppression to `bibliot|librarian` and an explicit "our library" phrase.
5. Reset dedupe state on SessionStart (compact and resume). Re-fire a page after 10 human prompts.
6. Cap output at 3 pointers. Print the matched terms with each pointer, so the agent can skip noise in one glance.
7. Fix org detection: match a whole path segment.

### Phase 1: action-time tripwires (the main gain)
A new PreToolUse hook reads the tool name and arguments before the call runs.
- The trigger lives on the page that owns the rule, as frontmatter `triggers:` with the fields tool, argument predicate, scope, mode (`deny` or `inform`), and a one-line consequence. A generator compiles all triggers into one manifest, and the hook reads only the manifest.
- `deny` blocks the call and names the page and the correct action. `inform` adds context next to the tool result.
- First rules: Klever `git clone` to a path outside its workspace-map location (deny), a fresh Klever clone left on `main` (inform), `cd` in Bash (inform, the eza hang), and Write/Edit under the auto-memory folder (deny, see Phase 3).
- Known blind spot: commands hidden inside scripts or wrappers.

### Phase 2: better prompt-time scoring
- Replace bag-of-words with BM25 over the alias, trigger, and note fields: weights 3/4/1, k1=1.2, b=0.75. Rarity weighting replaces the short-word whitelist.
- Abstain below a threshold calibrated on labeled data. Seed the labels with `judge-results.jsonl` and extend them to about 200 labeled pairs.
- Rollout gate: at least 80% of pointers judged relevant on held-out sessions.
- No embeddings for now. Both reviews agree: precision is the problem, and embeddings cannot enforce a path or branch predicate.

### Phase 3: writes go to the library, not auto-memory
**Decision for Gabriel. The two reviews disagree.**

| Option | For | Against |
|---|---|---|
| A. PreToolUse deny on Write/Edit under `~/.claude/projects/*/memory/`. The deny message routes to `documentation/bibliotheque/inbox/` or `/bibliotheque-librarian shelve` (Claude's pick) | Keeps reading the existing memory. Matches "never write there" exactly | The harness prompt keeps asking for memory writes, so each attempt costs one denied call. A Bash write (`cat >`) can bypass it |
| B. Migrate the 8 memory files to the library, then set `autoMemoryEnabled: false` for Klever (Codex's pick) | Removes the memory instructions from the system prompt. One knowledge system | Ends the reads. The always-loaded property moves to CLAUDE.md |

Either way, add one CLAUDE.md line: "Durable lessons go to the library inbox, never to auto-memory."

### Phase 4: measure
Re-run `measure_recall.py` and the judge on a 30-day window after rollout. Targets:
- Machine-prompt pointers = 0. Invalid pointers = 0.
- Pointers on fewer than 30% of human prompts. At least 80% judged relevant.
- Clone rule: correct destination and branch on every Klever clone, measured from transcript Bash calls. Count false-positive denies.
- Auto-memory writes = 0. Library inbox and shelve writes counted.

Also fix the measurement script first. It still shows 5.84 pointers per firing against a cap of 5. The likely cause is human prompts with image attachments (list content), which the script does not count as a turn.

## Out of scope
- Rewriting the 1,651 aliases. Coverage improves through the per-page triggers in Phase 1 and through additions after real misses.
- An LLM librarian call on every prompt. Too slow and too costly.

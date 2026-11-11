# Library recall: Claude's independent adversarial review

Written before reading the Codex review. Evidence: `recall-report.md`, `recall-metrics.json`, the hook source, and replay tests on 2026-10-27.

## Bugs (each fixable in under a day)

| # | Defect | Evidence | Fix |
|---|---|---|---|
| B1 | The hook fires on machine prompts | 94 of 157 task notifications and system reminders got pointers: 513 pointers of pure noise | Exit early when the prompt starts with `<task-notification`, `<system-reminder`, `<command-`, `<local-command`, or `Caveat:` |
| B2 | Rows with a `~` path, or with annotation text in the path cell, become unopenable pointers (CORRECTED after the Codex review: absolute paths survive `os.path.join`, so they are not broken) | 9 `~` rows and 16 annotated rows. `build-tooling-silent-side-effects` was injected 24 times with a broken path. One absolute row points to `/Users/gabrielamyot/...`, which does not exist | Expand `~`, strip trailing `(…)` text. Add a librarian lint that rejects rows whose path does not exist |
| B3 | Words under 4 letters are dropped | `tmp`, `dev`, `map`, `git` never match. The clone rule scored 1.0 on the real correction prompt | Add domain short words to `SHORT_OK`. The real fix is B4 plus T1 |
| B4 | A single generic word scores like a specific one | `worktree-env-local-force-delete` was injected 17 times, `timeout-not-on-macos` 6 times, across unrelated prompts | IDF weighting: a token's weight is log(N / rows containing it). Common words such as "main", "branch", and "repo" stop carrying a match |
| B5 | Each page fires at most once per session | The repo-sync page fired on prompt 1 for an unrelated topic, so it could not fire later when the clone rule mattered | Allow a re-fire after K prompts, or when the new score is clearly higher than the first |

## Design limits

- **D1. Prompt-time only.** The hook reads the human's words. Many errors come from the agent's own decision mid-task: the `/tmp` clone, a `cd` that hangs, a piped `git push`. No prompt text precedes those actions. **This is the largest gap.** Bugs B1 to B5 cannot fix it.
- **D2. Precision is the binding constraint, not recall.** Pointers are injected on 64% of human prompts, about 5.8 per prompt, and 2.6% are opened in the same turn. A channel that is mostly noise teaches the agent to ignore it. In the judge sample (`judge-results.jsonl`, 80 random pointers, a strict Sonnet judge), **18 were relevant (22%), 12 tangential, and 50 noise (62%)**. Most noise came from generic verbs in the prompt ("review", "check", "merge", "fix", "resolved"). Short prompts ("merged", "don") and interpersonal asides got near-random matches.
- **D3. Coverage is uneven.** 189 of 514 Klever pages (37%) have no alias row, so recall can never reach them. Meanwhile one mega-page has 41 rows (`gitlab-ci-patterns.md`).
- **D4. Pointer granularity is the whole page.** Pages are long multi-lesson SOPs. A pointer to the matching section anchor would let the agent read 20 lines instead of 400.
- **D5. The output does not say why a pointer matched.** The agent cannot cheaply skip noise. Printing the matched terms would let it decide in one glance.

## Proposed redesign (keep the hook, add a second channel)

1. **T1. Action-time tripwires (new PreToolUse hook).** The library owns a small table, `TRIPWIRES.md`, with columns `tool | argument regex | page#section | mode (inform or deny)`. Examples:
   - `Bash` + `git clone .*datasophia` with a target outside the org root → deny, citing the clone rule.
   - `Bash` + `^cd ` → inform, citing the eza hang.
   - `Write` + `/.claude/projects/.*/memory/` → deny, routing to library shelving (see W1).

   These are deterministic and match on what the agent is about to do, so precision is near 100%. Keep the table short: 20 to 40 rows of rules that were costly when missed.
2. **T2. A leaner prompt-time recall.** Apply B1, B2, and B4. Raise the threshold to require two distinct non-generic tokens or a full alias phrase. Cap at 3 pointers. Print the matched terms and a section anchor. Target: a pointer on fewer than 30% of prompts, with most judged relevant.
3. **T3. Coverage via INDEX, not more aliases.** Pages with no alias stay reachable through INDEX.md. Do not mass-generate aliases, which would only add noise. Add a curated trigger line only when a page was missed in a real session, the way the clone rule was.

What I would not do: embeddings or a vector database. Recall is not the binding problem, precision is. Embeddings add a service, latency, and opaque matches. BM25/IDF over the existing table gives most of the gain in about 20 lines of Python.

## Writes: library instead of auto-memory

- **W1 (recommended). A PreToolUse deny on Write and Edit to `~/.claude/projects/*/memory/*.md`.** The deny message names the replacement: append a nugget to `documentation/bibliotheque/inbox/` or run `/bibliotheque-librarian shelve`. Reads stay untouched, which matches the requirement.
  - Failure mode: the harness system prompt keeps telling the model to save memories, so the model will try, get denied, and then take the redirected path. That costs one wasted tool call per attempt. A one-line CLAUDE.md rule lowers the attempt rate.
- **W2 (alternative).** Migrate the 8 existing memory entries to the library or CLAUDE.md, then set `autoMemoryEnabled: false` for the Klever project. This is cleaner because the memory instructions also leave the system prompt. It conflicts with "keep reads", so it is the user's call.

## How to measure after the change

Re-run `measure_recall.py` and the judge on a new 30-day window:
- Machine-prompt pointers = 0.
- Human prompts with pointers below 30%.
- Judge RELEVANT share above 60%.
- Same-turn open rate above 15%.
- Tripwire fires logged with deny and inform counts.
- Auto-memory writes = 0, and library inbox writes rising.

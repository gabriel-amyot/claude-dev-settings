# Self-improvement loop

The skill improves from real use. It tracks three signals and turns them into proposed changes. Gabriel approves every change.

## Signals

1. **Use.** Every `/mission` command logs one line: `mission log use --command <cmd> --mission <slug> --session <slug>`.
2. **Feedback.** When Gabriel reacts to a mission output, a report or a terminal reply, log it with his words verbatim. Use `+1` for "good", "perfect" or "this works", and `-1` for a correction, "I don't understand", a re-ask, or "what is X?". Re-asks and "what is X" count as negative feedback even when he does not call them complaints.
   `mission log feedback --rating -1 --text "<his words>" --command report --mission <slug>`
3. **Evals.** `evals/run_layer_a.py` runs on every change to the skill (deterministic, seconds). `evals/evals.json` holds the behavioral cases for skill-creator.

## Retro: `/mission retro`

Run it when Gabriel asks, or propose it after 10 new feedback entries.

1. `mission log summary --since <last retro date>`.
2. Group the negative feedback by cause: missing data, too much detail, too little detail, bare reference, wrong view, stale data, slow.
3. For each group with 2 or more entries, draft one change to SKILL.md, a reference, the template, or the lint. Add an eval case that would have caught it.
4. Show the proposals as a needs-you list (ID, problem with the quotes, change, eval). Apply only what Gabriel approves.
5. Run `evals/run_layer_a.py`. Log the retro: `mission log use --command retro --note "<applied IDs>"`.

Do not edit the skill based on one complaint unless Gabriel asks. One data point is a mood. Two is a pattern. The exception is a consequential close-out miss (next section): one incident is enough.

## Close-out log

Every close-out writes one line to `missions/_meta/closeout-log.jsonl`: `mission closeout log <slug>` (run it after the gate opens, or when the close-out stops). The line holds:
- the item count per bucket;
- the big misses the sweep found (item id, reasons, the check that found it);
- the misses the human found and the sweep did not (`found_by: human`);
- `checks_fired`: the check ids that found at least one item.

### A miss the human found

An item the human found and the sweep missed gets `found_by: human`, and produces three things:
1. **A new check**, or a change to a check, in `CHECK_REGISTRY` (`scripts/mission_closeout.py`). Name it in the item's `new_check`.
2. **An eval case** built from the real item, anonymized (generic names, no org or vendor names; the private mapping stays in the PM repo). Name it in `eval_case`.
3. **A log line**, from `mission closeout log`.

One incident is enough for a consequential miss: security, lost work, or approval overreach. The gate refuses until `new_check` and `eval_case` are named. Routine friction waits for a repeat: mark it `miss_weight: routine` and it is logged only.

### Keep the checklist small

- **Every check names the real case it catches.** `CHECK_REGISTRY[<id>].catches` holds the anonymized case group (for example `G6`). Layer A refuses a check with no case.
- **A check that never fires is reviewed.** `mission closeout review-checks` reads the last 5 close-outs. A check with no find in all 5 is listed "review for removal". Fewer than 5 logged close-outs is UNKNOWN: keep every check.
- **Capture during the mission.** Record asks and exclusions as they happen (`asks`, `scope_constraints`, MR exclusions), so a close-out checks a record instead of rebuilding it.

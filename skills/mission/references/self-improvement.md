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

Do not edit the skill based on one complaint unless Gabriel asks. One data point is a mood. Two is a pattern.

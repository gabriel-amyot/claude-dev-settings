# architect-lens eval results

## 2026-11-12, first run (skill at branch GH-680-architect-lens)

| Suite | Result | Notes |
|---|---|---|
| Layer A (`run_layer_a.py`) | 18/18 PASS | Includes the copyright guard (no 10-word book run in 6 public files) and all 39 knowledge-base routes. |
| Layer B behavioral (`evals.json`) | 22/23 expectations (95.7%), threshold 0.75: PASS | n=1 run per eval (not the default n=3), executor and grader were separate subagents. The one fail: review mode left some findings without a section citation. Fixed in `references/method.md` (every finding carries its own citation), then eval 3 re-run: see below. |
| Layer B′ trigger (`trigger-evals.json`) | INCONCLUSIVE | 0/3 trigger rate on every query, positive and negative. Control: 4 positive queries of the existing `investigate` skill through the same runner also scored 0. A manual probe showed the temporary command is visible at init and `claude -p` answers directly without any tool call. The runner registers no triggers in this environment for any skill, so the result says nothing about this description. Tracked as a harness bug. |

Executor outputs and grading JSON stay local (`/tmp/fosa/evals/`). They are not committed, because outputs paraphrase book content at length.

## 2026-11-12, eval 3 re-run after the citation fix

6/7 under the original wording (0.857). Remaining gap: two findings cited `reference/styles-ratings.md` without naming the chapter. Decision: a reference file is a valid knowledge-base source, so the rule and the expectation now require it to name its chapter (for example `Ch 17 ratings`) instead of forbidding it. Not re-run after this clarification.

Overall Layer B on the first full run: 22/23 (95.7%). PASS against the 0.75 threshold.

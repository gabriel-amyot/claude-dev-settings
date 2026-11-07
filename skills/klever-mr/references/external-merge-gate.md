# External merge gate (`/klever-mr --merge-on-pass`)

Manual mode only. Run it only when the human has pre-authorized "review with Codex, merge if it passes" for this MR in this session. Without that instruction, stop at MR creation. It merges to `dev` only, never `uat` or `main`.

Not for: a human-reviewed MR (use `/crit`), a teammate's MR (use `colleague-review-klever`), or code already merged.

Mechanics of the Codex call (stdin brief, verdict line, stderr echo): `~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/sops/autonomous-workflows/codex-cli-adversarial-review-patterns.md`. Pushback discipline: `.../sops/qa-review/adversarial-peer-review-loop-discipline.md`.

## Loop

1. **Run the pre-flight gates and create the MR first.** The review judges the pushed branch.
2. **Write the review brief to a file.** State what the change does, the invariants that must hold, the exceptions already accepted (with the reason), and the scope: "judge THIS diff". End the brief with `End with exactly one line: VERDICT: PASS or VERDICT: BLOCK`. Send the brief, then `git diff origin/dev...HEAD`, on stdin.
3. **Read the verdict from the stdout file.** Keep stderr in a separate file. It echoes the full prompt and buries the verdict line.
4. **On BLOCK, triage each finding before you answer.** Read the cited lines on the trunk with `git show origin/dev:<file>`.
   - The diff introduced or worsened it: fix it, RED first. For a hang, the RED proof is the hang itself; run that one test alone.
   - It exists on the trunk unchanged: a pushback candidate. Before you push back, check that the diff does not make it reachable in a new way (a new caller, new config, a new input path). An untouched line can still be a new defect. Line-touch is a navigation aid, not a verdict.
5. **Pushback is four sentences:** the trunk evidence, the house rule (a pre-existing defect gets its own ticket and does not fold into this MR), where you routed the finding, and the question "how does THIS diff make it worse than the trunk?" Never argue from review fatigue.
6. **Re-review after every response.** Quote which blockers you fixed and which you routed.
7. **Round cap: 3.** Three rounds without PASS go to the human with the transcripts. Do not start a fourth round.
8. **On PASS:** arm merge-when-pipeline-succeeds (Step 5, `--action auto-merge`). Confirm the merge commit on `origin/dev`, then run the post-merge cleanup (`scripts/post-merge-cleanup.py`).
9. **Before you close out:** put each routed pre-existing finding on its ticket. Keep the brief, the verdict files and the transcripts under the ticket folder `reports/`.

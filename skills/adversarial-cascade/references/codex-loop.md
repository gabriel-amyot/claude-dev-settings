# Codex review/fix loop (Phase 2)

Merged from two approved proposals: `codex-adversarial-review-loop` (2026-10-27, KTP-1358: 7 Codex
rounds, each found a real defect) and `adversarial-fix-loop` (2026-09-21, session noble-wren: 9 passes,
25+ fixes, one false positive rejected with evidence). Invocation mechanics come from the Klever SOP
`documentation/bibliotheque/sops/autonomous-workflows/codex-cli-adversarial-review-patterns.md`.

## One round

1. **Write the prompt to disk** with the script, never a heredoc:
   `python3 scripts/build_codex_prompt.py --out <dir>/codex-r<N>-prompt.txt --repo <abs repo> --base <base> --round <N> --files <changed,files> [--spec <AC file>] [--invariants <file>]`
   Round 2 and later also need `--previous <dir>/codex-r<N-1>-triage.md --fix-range <prev sha>..<fix sha>`.
   Keep each prompt to one repo and one artifact. Long or broad prompts die with zero output.
2. **Run Codex** in the background (Bash `run_in_background`) or foreground with timeout 600000:
   `bash scripts/run_codex.sh <prompt> <dir>/codex-r<N>.md --effort high`
   It runs `codex exec --skip-git-repo-check -s read-only -C <neutral dir> -c model_reasoning_effort=high --output-last-message <out> "$(cat prompt)" < /dev/null`.
   Exit 3 means "exit 0 but no review": the known silent failure. Shrink the prompt and retry once.
3. **Parse:** `python3 scripts/triage.py parse <dir>/codex-r<N>.md`. Read every warning. A BLOCK with no
   findings is noise. A parse-gap warning means read the raw review yourself.
4. **Verify every finding before you accept it.** For each, find the one command that would refute it
   and run it. Spot-check at least the top 2 or 3 evidence lines yourself. Reject a false positive with
   that evidence. Mark labels CONFIRMED or UNVERIFIED as Codex gave them, and treat UNVERIFIED as a lead.
5. **Provenance by defect, not by file.** A file in `git log <base>..HEAD` does not prove the defect is
   new. Reproduce the defect at the merge base. Outcomes: `introduced`, `pre-existing`, or
   `newly-reachable` (old code that this change now exposes; treat it as in scope).
6. **Write the triage** to `<dir>/codex-r<N>-triage.json` (schema in `scripts/triage.py`) and a short
   `codex-r<N>-triage.md` for the next round. Then decide:
   `python3 scripts/triage.py decide <dir>/codex-r<N>-triage.json --round <N> --max 5`
7. **Act on `next_action`:**
   - `fix_and_recheck`: fix only the listed CRITICAL/MAJOR. Each fix gets a test that fails on the
     current commit first. Mutation-check each fix (`/test-adversarial` mutate mode). Run the
     verification command. Commit, then run round N+1 scoped to the fix range.
   - `verify_findings` / `determine_provenance`: finish step 4 or 5 first.
   - `escalate_scope`: stop and ask the human. More rounds cannot remove a scope constraint.
   - `stop_cap_unresolved`: stop. Report every open finding as UNRESOLVED. The cap never means accepted.
   - `stop_clean`: done. File each `to_file` finding as a follow-up ticket proposal (draft only; posting
     goes through `/post-comment`). MINOR and NIT go to the report as logged.

## Rules

- Cap: 5 rounds. A MAJOR found in the last allowed round is a reason to ask for one more round, not a
  reason to close.
- Each round after the first says what the previous round changed and asks what that change broke.
  Three of thirteen defects in one KTP series were introduced by earlier fixes.
- A plateau of findings across rounds signals a structural root cause. Stop patching one by one and
  report the class.
- State the reasoning effort of every pass in the report. An unstated effort reads as low.
- Reviewers that cannot run tests are static-only. Run the suite yourself and say which pass was static.

## Fallback when Codex cannot run

Codex missing (exit 4), out of credits ("workspace is out of credits" means the ChatGPT workspace), a
hook block, or three capacity errors in a row: dispatch a `general-purpose` agent with
`model: fable` and the SAME prompt file. Label that pass "fallback reviewer, not Codex" in the report.
Never self-review in place of the second model.

## Scope

Code diffs only. A decision record, a bug ticket, or a document goes elsewhere: documentation trees
use `/tech-doc-review-flow`; ideas and decisions use `/challenge`.

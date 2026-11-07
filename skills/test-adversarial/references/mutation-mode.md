# Mutate mode: prove the tests catch the defect

**Invocation: explicit only** (`/test-adversarial mutate ...`, or the user asks "would the test have
caught this", "mutation check", "prove the test fails without the fix"). It edits a source file for the
duration of a test run, so never start it on your own.

Source proposal: `mutation-check-a-fix` (2026-09-21, KTP-571, two silent-failure defects in one file).
Rules behind each step: Klever SOP `sops/qa-review/guard-test-validity-and-falsification.md`
("Mutation-Check a Fix by Re-Applying the Shipped Defect", "A Mutation Injection via str.replace Can
Silently No-Op", "cp Restoring a Mutation-Test Backup Prompts Interactively", "A Surviving Mutant Is Not
Always a Missing Test", "A Mutation Probe Must Reinstate the Exact Defect").

## Steps

1. **Isolate.** Run in a worktree or on a committed file. The script refuses a file with uncommitted
   changes unless you pass `--allow-dirty`.
2. **Name the shipped defect exactly.** Take it from `git show <pre-fix sha>:<file>`, not from memory.
   The mutant is the fixed expression replaced by the defective one. Several defect sites means several
   runs, one mutant each.
3. **Run one mutant:**
   ```
   python3 ~/.claude/skills/test-adversarial/scripts/mutation_check.py run \
     --file <src> --find '<fixed expression>' --replace '<defective expression>' \
     --test '<suite command>' [--baseline '<untouched-side suite command>'] \
     --cwd <repo> --out <ticket>/reports/mutation/<name>.json
   ```
   The script refuses (exit 2, no change made) when: `--find` does not occur exactly `--count` times,
   the substitution changes nothing, or the suite is red before the mutation. It backs up with
   `shutil.copyfile`, restores in `finally` and on SIGINT/SIGTERM, verifies sha256, bumps the mtime
   so build and bytecode caches cannot serve the old file, and re-runs the suite green.
4. **Read the verdict.**
   - `KILLED` (exit 0): the suite detects the defect. Record the failing tail.
   - `SURVIVED` (exit 1): the suite does not detect it. Read the mutant before you add a test. Either a
     test is missing, or the production code is redundant or equivalent and the test is right to
     ignore it. Say which, with evidence. Do not rationalise a survivor.
   - `RUNNER_ERROR`: the runner failed to start under the mutant. Not a kill.
   - Baseline went red: the mutant is too broad or the test too coupled. Narrow it.
   - `RESTORE_FAILED` (exit 3): stop. Run `mutation_check.py recover --file <src>`, then `git diff`.
5. **After a hard kill** (a journal file is left): the next `run` refuses. Run `recover`, which restores
   from the backup only when its sha256 matches the journal.
6. **Report** the counts in the MR test plan, for example "mutant A (padStart blanket) kills 9/28".

## What the script does not do

It does not choose the mutant, run several mutants, or decide whether a survivor is a test gap. Those
are judgement steps for this skill's reviewer.

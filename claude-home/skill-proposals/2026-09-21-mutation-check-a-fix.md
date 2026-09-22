# Skill Proposal: mutation-check-a-fix
Date: 2026-09-21
Source: KTP-571 Canada pass (session `plain-pike`) — two silent-failure defects in one file

## Why

CLAUDE.md already says "tests that find nothing are suspect" and "prefer a test you watched fail first, then pass." Nothing operationalizes it. A suite written after the fix passes by construction, and there is no cheap ritual for proving it would have caught the bug.

The gap is sharpest for **silent-failure** defects — a dropped key, a corrupted identifier, a filter that excludes one country. No exception, no console output. A test can assert the right value and still be insensitive to the defect.

## Trigger

After writing tests for a bug fix, before opening the MR. Also when a reviewer asks "would this test have caught it?" Invoke on: "mutation check", "would the test have caught this", "prove the test fails without the fix", "verify the suite".

## Scope

Global. Language-agnostic: the KTP-571 run did it for TypeScript (Playwright) and Python in the same session.

## Draft steps

1. **Name the shipped defect precisely** — the exact expression that was wrong, from `git show` of the pre-fix blob, not from memory. Multiple defect sites mean multiple mutants, run separately.
2. **Save the fixed file** by a non-interactive path. Python `shutil.copyfile`, never `cp` (interactive in this shell — a background `cp` over an existing file hangs on an invisible overwrite prompt).
3. **Apply one mutant**, asserting the substitution actually changed the text (`assert mutant != orig`). A silently no-op mutant reads as "the suite passed" and proves the opposite of what you wanted.
4. **Run the suite. Record reds.** Zero reds = the suite does not test the fix. Report that, do not rationalize it.
5. **Check the untouched-side baseline stayed GREEN under the mutant.** This is the step people skip. It proves the test is insensitive to the things it should be insensitive to. A baseline that also goes red means the mutant is too broad or the test too coupled.
6. **Restore and verify byte-identical** (`diff`). Do not assume the restore worked. A mutant left in place and committed is the worst outcome of the whole procedure.
7. **Re-run green**, then put the counts in the MR test plan: "mutant A reds 15/28, mutant B reds 7/28."

## Guardrails

- Never leave a mutant in a commit. Verify with `diff` and a final green run.
- Prefer editing the file over shell copies, so the harness tracks state.
- If the session may be interrupted, apply mutants in the foreground, not a background command.

## Prior art

`e2e/ktp-571-geo-identifier-logic.spec.ts` (wayfinder #29) already did an ad-hoc version — "the blanket-padStart mutant kills 9 tests" — in prose, by hand, with no restore verification. This proposal is that instinct made repeatable.

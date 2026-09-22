# Skill Proposal: codex-adversarial-pass
Date: 2026-08-12
Source: KTP-1062/1065 — three Codex passes, three DO NOT SHIP verdicts

## Trigger

After any build reaches green and before an MR is opened or merged, on code where being wrong is
expensive: auth, money movement, anything an LLM will drive, anything touching a shared credential.
Also on request: "adversarially review this", "codex review".

## Why it earns a skill

Three passes this session, on three different bodies of code. The in-pipeline review phase returned
`criticals: 0` on all three. The independent pass returned DO NOT SHIP on all three, and every
upheld finding was real. One of them was a privilege escalation that the obvious deployment step
would have created.

The shape was identical each time and I rebuilt it by hand each time. That is the definition of a
skill.

## Scope

Global. The invocation pattern is not Klever-specific; the triage output convention is.

## Draft steps

1. **Export a tight subject.** `git diff <base>...HEAD -- src/main` — production code only. Withhold
   tests deliberately, so the reviewer judges the code rather than reading the intent off the
   assertions. A broad "review this repo" prompt runs away (11 minutes, no findings, on a past run).
2. **Write the prompt with the trust model stated first.** Who is untrusted, what the guarantees are,
   numbered. Then an attack checklist ordered by blast radius. Then: rank CRITICAL/HIGH/MEDIUM/LOW,
   name file and method and the exact input, say plainly when a concern is already handled, do not
   pad, end with one line SHIP / SHIP WITH FIXES / DO NOT SHIP.
3. **List the already-known gaps** and ask whether each is worse than rated. This stops the reviewer
   spending its budget rediscovering them, and it sometimes upgrades one.
4. **Run it neutral and detached.**
   `codex exec --skip-git-repo-check -C <empty-scratch-dir> -s read-only --output-last-message out.md - < prompt.txt`
   Backgrounded. A project cwd makes it load skills and go agentic.
5. **Triage every finding into a table** with a verdict column: upheld-and-fixed, upheld-and-recorded
   with the reason it is out of scope, or **refuted with evidence**. A refutation must cite a check
   (`javap`, a test, an unchanged helper), never an argument. Persist the raw output unedited beside
   the triage.
6. **Fix test-first.** Reproduce the finding as a failing assertion before fixing it, so the fix is
   proven rather than asserted.

## Notes

- Findings that cannot be fixed in the current architecture get made **fail-closed and explicit**
  rather than quietly accepted. On KTP-1065 an unverifiable human-confirmation control became a gate
  that defaults off and refuses, instead of a boolean pretending to be a control.
- Watch for a fix introducing a regression. One did this session, and a test written before the
  review caught it.

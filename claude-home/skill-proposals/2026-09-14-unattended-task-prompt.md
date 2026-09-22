# Skill Proposal: unattended-task-prompt
Date: 2026-09-14
Source: session plain-badger — authoring and hardening a Cowork recurring-task prompt for the bibliothèque graph refresh

## Trigger

The user asks for a prompt to run something on a schedule, in Cowork, as a cron/recurring
task, or "unattended" / "overnight" / "every day". Also when an existing scheduled-task
prompt needs review before install.

Not for one-off prompts, and not for interactive slash-command skills. The distinguishing
property is: it runs with no memory of prior runs, no conversation context, and nobody
available to answer a question.

## Scope

Global. The pattern is surface-independent (Cowork recurring task, launchd plus a headless
CLI call, a CI job that invokes an agent).

## Draft Steps

1. **Route the substrate first.** If the work carries no model judgment, say so and propose
   a deterministic script plus a launchd plist instead. An agent prompt is the fallback for
   work only an agent can do, not the default. Cite the org's own precedent if one exists.

2. **Establish the execution surface.** Pin down: which agent surface runs it, which skills
   and tools that surface actually exposes, whether a second writer touches the same files,
   and how dirty the working tree normally is. Measure the last two rather than assuming;
   both produce gates that silently never pass.

3. **Draft against the seven-point anatomy.**
   - autonomy stated, with a written destination for questions that does not block the run
   - a closed list of blocking conditions
   - a bounded write surface, naming the files the task may touch
   - a validation gate that compares against the previous artifact and blocks on an
     implausible drop
   - hash-guarded restore, never a bare `git checkout --`
   - inbox dedupe on a stable key so a persistent failure files one item, not thirty
   - a named durable record, because nobody reads a scheduled run's chat output

4. **Adversarial pass.** Run the real Codex CLI with the execution surface stated as ground
   truth and attack angles enumerated (ordering, concurrency, dirty tree, surface mismatch,
   silent failure, cadence, ambiguity). Invocation per the bibliothèque's Codex SOP.

5. **Triage the findings against the live system.** Each finding is a hypothesis. Verify
   before applying — especially any proposed precondition, which must be measured against
   how often it currently holds.

6. **Emit the prompt as a file**, with a header stating the accepted known limits and what
   adversarial pass it survived. Commit it; an untracked prompt gets wiped.

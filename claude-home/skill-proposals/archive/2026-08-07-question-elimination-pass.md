# Skill Proposal: question-elimination-pass
Date: 2026-08-07
Source: KTP-830 — 4 of 7 drafted PO questions were already answered by her own attachments

## Trigger
About to send a stakeholder a list of questions (Jira comment, Slack, email) to unblock a build.

## Scope
Global — applies to any ticket with attachments, templates, or prior deliverables.

## Draft Steps
1. Draft the questions normally.
2. Inventory every artifact the stakeholder has already provided: attachments, templates, sample
   outputs, prior shipped files, linked notebooks.
3. For each question, try to answer it from those artifacts before asking. Record the evidence.
4. Kill every question the artifacts answer. Note what killed it, so the answer is auditable.
5. Re-read the survivors: often one better question replaces three (e.g. "share the notebook"
   instead of asking what three of its transforms do).
6. Report defects the pass found — a mismatch between an artifact and the build is worth more than
   the question you were going to ask.

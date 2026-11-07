# Skill Proposal: Extend colleague review evidence and handoff guidance
Date: 2026-10-25
Source: Klever MR !481 / KTP-1264, Placer backend extraction discussion

## Trigger
Reviewing a colleague's MR, particularly async vendor work or an author unfamiliar with the existing backend.

## Scope
Extend the existing global colleague-review procedure and its Klever specialization (`~/.claude-shared-config/agents/colleague-review.md` and `colleague-review-klever.md`). This is a proposal, not a new parallel review skill or an installed change.

## Draft Steps
1. Read the current complete discussion history and exact head source. An empty patch in changes metadata is not sufficient evidence that the file is unchanged; fetch full source when needed.
2. Reproduce changed behaviour through reachable lifecycle transitions. Await all measured background work; distinguish a defect probe's observations from a passing correctness suite. Trace identities and label semantics across producer/cache/consumer boundaries.
3. Draft in the user's requested tone: issue, evidence, impact and intended outcome. Give backend entry points and separate immediate MR work from architecture follow-ups. Do not require prescriptive code patches or DO NOT lists solely because the author uses a coding agent.
4. Recheck head and existing threads before posting. Deduplicate by issue, refine an existing clarification when appropriate, and verify the completed post/edit before marking the local record published.

## Existing coverage and delta
The colleague-review agents already require factual checks and conversational comments, and the library already covers test falsification. This proposal adds the incomplete-diff response, full-job completion, reachable UI lifecycle, and a compact handoff boundary. Reconcile the older 2026-10-13 MR-comments-as-prompts note with Gabriel's later explicit preference rather than installing conflicting rules.

# Jira Ticket Description Template (Story)

<!--
PHILOSOPHY
==========
Every Jira Story description follows four sections, in this order:

  1. Intent (Why)        — PO-level pain point and outcome. Plain English.
  2. Acceptance Criteria — Observable outcomes, grouped by subsystem if cross-stack.
  3. Blockers            — Numbered open questions the PO must answer before sprint.
  4. Figma Prompt        — Only for tickets with a UI component.

NON-GOALS (do NOT add these to Jira)
====================================
- NO meta header block (Type / Size / Priority / Status). Those are Jira fields.
- NO "How" / "Technical recommendation" / "Files to touch" section. That lives in
  a local spike or DRAFT-TICKET.md, never in Jira.
- NO "Links" section pointing at filesystem paths. Use Jira's Links field or
  inline ticket keys (e.g., KTP-492) for cross-references.
- NO refactoring proposals or "while we're here" cleanups. Feature tickets are
  feature-forward only. Quirks stay unless the PO explicitly asks for cleanup.
- NO bare typos / nits in ACs or Blockers. Ship a separate cleanup ticket.

FORMATTING
==========
Jira wiki markup, NOT GitHub markdown. Use:
  h2. / h3.   for headers
  *bold*      for bold
  _italic_    for italic
  *           for bullets
  >           for blockquotes
  #           for numbered lists

Length discipline: a PO should be able to fill this skeleton in under 15 minutes.
-->

h2. Intent (Why)

<one-paragraph plain-English pain point — what hurts today, who it hurts, and why>

<optional second paragraph: the outcome this ticket delivers. State it as removal of the pain, not as a feature list.>

_This ticket exists to <one-sentence outcome>._

h2. Acceptance Criteria (What)

> _Gate:_ AC-0 must pass before any other AC is locked. Everything below is provisional until the PO confirms.

*AC-0 — Scope confirmation (blocking gate)*

* <PO name> reviews this ticket and confirms the Why, the ACs, and the open questions in the *Blockers* section.
* Until AC-0 is signed off, the team does not start implementation.

<!-- If the work is single-stack, drop the h3 headings below and list ACs flat.
     If cross-stack, group with h3 and state implementation order explicitly. -->

h3. Backend ACs (`<repo-or-service-name>`) — implement first

*AC-1 — <short title>*

* Given <precondition>, when <trigger>, then <observable outcome>.
* <additional outcome or constraint>
* <additional outcome or constraint>

*AC-2 — <short title>*

* Given <precondition>, when <trigger>, then <observable outcome>.
* ⚠️ _<PO name> to confirm: <specific question>. (See Blockers Q<N>.)_

h3. Frontend ACs (`<repo-or-service-name>`) — implement second, after backend is deployed

*AC-3 — <short title>* _(depends on AC-<N>)_

* <observable outcome>
* <observable outcome>

*AC-4 — <short title>* _(depends on AC-<N>)_

* <observable outcome>
* ⚠️ _<PO name> to confirm: <specific question>. (See Blockers Q<N>.)_

h2. Blockers — Questions for <PO name>

> _These block AC-0. Answer these before the ticket goes in-sprint._

*Q1 — <short topic>.* <one-line context describing the open question>

* (a) <option a>, or
* (b) <option b>, or
* (c) <option c>

*Q2 — <short topic>.* <one-line context>

* (a) <option a>, or
* (b) <option b>

*Q3 — <short topic>.* <free-form question with no preset options>

*Q4 — Out-of-scope confirmation.* Not in this ticket: <list>. Confirm these stay out — each is a separate conversation.

*Q<N> — <short topic>.* <context>. _This gates AC-<N>._

h2. Figma Prompt

<!-- Include this section ONLY when the ticket has a UI component.
     Paste-ready prose for Figma Make. Blockquote-indented. -->

> Design a <one-line description of the surface> for the <product name>. <Layout description: panes, grids, modals.>
> <Header / primary controls description.>
> <Body / content description: cards, lists, fields.>
> <Interaction details: buttons, popovers, modals.>
> Style: <design system, tokens, density>. <No-nos: e.g., no tabs, no breadcrumbs.>
> Empty states: <list>. Error / success states: <list>.

<!--
USER STORY (optional)
=====================
If the team prefers a user-story opener, place it as the first line ABOVE the
"h2. Intent (Why)" section, with no header:

  As a <role>, I want <capability> so that <benefit>.

Given/When/Then is supported inside any AC bullet:

  * Given <precondition>
  * When <trigger>
  * Then <observable outcome>
  * And <additional outcome>
-->

# Jira Ticket Description Template (Story)

<!--
PHILOSOPHY
==========
Anyone (PO, dev, QA) should grasp a ticket at a glance, then drill in.

Only TWO sections are mandatory: Summary and Acceptance Criteria. Everything else
is OPTIONAL and included ONLY when there is a real need. Do NOT force-fill optional
sections and do NOT invent design notes, steps, or scope lines to fill space. If
there is nothing genuinely useful to say, leave the section out.

Section order:
  1. Summary (Why)                  — mandatory. Plain-English what + why.
  2. Acceptance Criteria            — mandatory. AC-0 scope gate, then a Hero AC, then supporting ACs.
  3. Out of scope                   — optional. Only when a real risk of confusion.
  4. Design / Technical Recs        — optional. Where to look, not what to do.
  5. Implementation Recs (steps)    — optional. A follow-along map for the implementer.
  6. Figma Prompt                   — optional. UI tickets only.

QUESTIONS ARE NOT A SECTION
===========================
Any open question goes as a COMMENT on the ticket, not baked into the description.
The AC-0 gate is where the PO confirms scope and clears outstanding comment-questions
before implementation starts.

NON-GOALS (do NOT put these in Jira)
====================================
- NO meta header block (Type / Size / Priority / Status). Those are Jira fields.
- NO machine-local filesystem paths (no /Users/... , no project-management-internal
  documentation/ or tickets/ or reports/ paths). Reference internal docs by NAME.
  Shared references ARE fine and useful: code repo paths (app-proximity-report/...),
  class/file names, BigQuery table names, Google Sheet ids, GCP project ids, skill names.
- NO refactoring proposals or "while we're here" cleanups. Feature tickets are
  feature-forward. Quirks stay unless the PO explicitly asks for cleanup.
- NO bare typos / nits in ACs. Ship a separate cleanup ticket.

FORMATTING
==========
Jira wiki markup, NOT GitHub markdown. Use:
  h2. / h3.   for headers
  *bold*      for bold
  _italic_    for italic
  *           for bullets
  #           for numbered lists
  >           for blockquotes
No em-dashes anywhere (use colons or commas).

AC STYLE
========
Lead with the Hero AC: the one plain user outcome anyone understands that defines
success. Supporting ACs follow. Each AC is a one-line outcome header, then
Given / When / Then. No separate description line under the header (redundant with
the header and the GWT). If a supporting AC is delivered by a subtask or blocked by
another ticket, name that ticket on the header.

Length discipline: a PO should be able to fill this skeleton in under 15 minutes.
-->

h2. Summary (Why)

<one to three plain sentences: what this ticket is about and why it exists. A non-technical reader should get the point without reading the ACs.>

h2. Acceptance Criteria

> _Gate:_ AC-0 must pass before any other AC is locked. Everything below is provisional until the PO confirms.

*AC-0 — Scope confirmation (blocking gate)*

* <PO name> reviews this ticket and confirms the Summary, the ACs, and any open questions raised as comments.
* Until AC-0 is signed off, the team does not start implementation.

*AC-1 (Hero) — <plain user outcome anyone understands>*

* Given <context>
* When <action>
* Then <observable, QA-assertable result>

*AC-2 — <outcome header>*  <!-- add "· Delivered by / Blocked by: KTP-XXX" only when true -->

* Given <context>
* When <action>
* Then <observable result>

<!-- For cross-stack work, group supporting ACs under h3. headings and state
     implementation order, e.g. "h3. Backend ACs (repo) — implement first". -->

<!-- OPTIONAL SECTIONS BELOW. Include only when relevant. Never mandatory. -->

h2. Out of scope

<what this ticket explicitly does not cover, when that is a real risk of confusion.>

h2. Design / Technical Recommendations

<where to look, not what to do: SOP names, code files, BigQuery tables, sheets, skills. Context for the implementer, not acceptance criteria. Omit if nothing worth pointing at. No machine-local paths.>

h2. Implementation Recommendations

<an ordered, plain list a person can follow, drawn from how we did it before. The implementer may diverge. Include where the "where do I start" map is genuinely useful (e.g. onboarding); omit otherwise.>

h2. Figma Prompt

<!-- UI tickets only. Paste-ready prose for Figma Make, blockquote-indented. -->

> Design a <surface> for the <product>. <Layout: panes, grids, modals.>
> <Primary controls.> <Body / content.> <Interactions.>
> Style: <design system, tokens, density>. Empty states: <list>. Error / success: <list>.

<!--
USER STORY (optional)
=====================
If the team prefers a user-story opener, place it as the first line ABOVE the
"h2. Summary (Why)" section, with no header:

  As a <role>, I want <capability> so that <benefit>.
-->

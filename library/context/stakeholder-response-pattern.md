# Stakeholder Question Response Pattern

When a stakeholder (David, Amal, etc.) asks about a feature's business logic or spec:

1. **Search local tickets first.** Grep `tickets/` for keywords. Check the epic INDEX.md for related sub-tickets.
2. **Fetch latest from Jira.** Always pull the current description and comments. Stakeholders may have updated the ticket since the last local fetch.
3. **Check the Notion wiki export** (`documentation/notion-wiki/export/`) for product vision and vendor API context. The Proximity Agent page is especially rich for Placer/location features.
4. **Check interview notes and spec docs** under `tickets/{EPIC}/{TICKET}/jaspreetInterview/` and `reports/architecture/`.
5. **Synthesize into a summary with actionable open questions.** Frame questions as "who can confirm X?" not abstract musings.
6. **Always check existing Jira comments** before posting to avoid duplicating what's already been said.
7. **Post via `/post-comment`.** Draft to disk first, preview, get approval, then post.

Learned from KTP-130 session (2026-03-31): David asked about the "arrows from zips to locations" feature. Context was spread across Jaspreet's interview notes, KTP-130 description, spec-data-requirements doc, Notion wiki Proximity Agent page, and AIO-245 tentative tickets. Synthesizing these sources revealed the original algorithm was broken (Sisi confirmed TTD lacks impression share by location) but Placer likely provides the data directly.

## The Mirror Case: Mine Their Artifacts Before Sending Them Questions

The pattern above is for answering a stakeholder's question. The same discipline applies in
reverse, before drafting questions **to** send a stakeholder.

Seven questions were drafted for a PO. An elimination pass against artifacts the PO had already
provided (a client template, a media plan, two internal tables) killed four of the seven: the
template answered the value-format question, the media plan answered the taxonomy question, and
one question was answerable by comparing two tables already on hand.

Better, the elimination pass found **two real defects instead of two more questions**: a value
rendered with a space that the client's own template renders without one, and a column the design
planned to populate from a source that returns a constant for every row. Both were worth fixing;
neither was worth asking about.

The remaining questions came out sharper too — one collapsed from three separate questions into
"share the notebook," because the notebook was the actual spec the three questions were dancing
around.

**A question answerable from an artifact the stakeholder already gave you is a question that
wastes their time and delays the build.** Before sending any batch of stakeholder questions, run
an elimination pass: for each draft question, check whether an artifact already in hand answers
it. Drop what's answered, promote any defect the pass surfaces, and sharpen what's left.

**How to apply:** Before drafting or sending stakeholder questions, list every artifact the
stakeholder has already provided (templates, sample data, prior docs, sheets). Walk each draft
question against that list and eliminate what's already answered. Treat anything the pass
surfaces as a defect-to-fix, not a question-to-ask.

**Source:** KTP-830 dusk-owl session (2026-08-07).

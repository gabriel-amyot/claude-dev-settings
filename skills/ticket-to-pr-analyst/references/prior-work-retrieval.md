# Prior-work retrieval (Step 1.5)

A new ticket often describes a problem that older local work already investigated under another
key. Example: KTP-1403 (Campaign Health empty response) had its cause in October work under
KTT-48 and KTT-54. A search by the new key alone finds nothing.

This step runs automatically. It is read-only. It never posts anything.

## Procedure

1. **Extract terms from the ticket.** Symptom words ("empty response", "spinner never stops"),
   the product or service name ("Campaign Health", "proximity report"), and the endpoint or
   table name if the ticket gives one. Use two to five terms.
2. **Library first.** Look up the terms in the org bibliothèque `ALIASES.md` and `INDEX.md`.
   Note every page that covers the symptom.
3. **Search local work by terms and by key:**
   ```bash
   python3 ~/.claude/skills/ticket-to-pr-analyst/scripts/find_prior_work.py \
     --root <PM_ROOT> --key <TICKET-KEY> --term "<symptom>" --term "<product>"
   ```
   The script ranks ticket and session folders by the number of distinct terms they match.
   It prints paths and dates, not bodies. Read only the top hits that match more than one term.
   A folder that matches one generic term is usually noise.
4. **Check linked Jira tickets**, including Won't Do and Done ones, for the same symptom.
5. **Write `analyst/prior_work.v<N>.md`** with:
   - **Sources**: each folder or ticket read, with its date.
   - **Confirmed**: causes with a `verified_against` stamp (commit, query, or runtime check).
   - **Hypotheses**: everything else. An old conclusion without a stamp is a hypothesis.
   - **Fix attempts**: what was tried, and the result.
   - **Why it stopped**: and what blocks validation now.
   - **Possibly stale**: a prior conclusion older than the last deploy of the affected repo.
     Mark it and do not reuse it as fact.
6. **Feed it forward.** Use confirmed facts in Step 4 (AC) and Step 7 (assumptions). Cite
   `prior_work.v<N>.md` in each assumption that depends on it.

## Boundaries

- Do not post a comment. If the user asks for a "prior investigation" comment on the ticket,
  draft it in the ticket folder without internal tooling or session names, and send it through
  `/post-comment`.
- If the library page is behind what the old ticket folder shows, add an inbox nugget for the
  librarian. Do not edit the library page from this step.
- No hits is a valid result. Record the terms searched in the run journal.

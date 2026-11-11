# Mode: fact-check — is this company-facing page still true?

Use this mode only when the user asks for it explicitly ("review this Notion page against the code",
"does this page need updating"). It is expensive and it can end in a Notion write.
For "is this page current" in the timestamp sense, use the `freshness` mode instead.

The mode is read-only until the last step.

## Steps

1. **Read the page through `nx`.** Use `card`, then `get --heading` per section. Record the page
   `last_edited_time` and the freshness stamp. Number every factual claim on the page.
2. **Read the org library first.** Check the org bibliothèque `INDEX.md`, `ALIASES.md`, and any
   doc-authority map for the topic. Give the cited pages to the checker as a `Library:` line.
3. **Dispatch one read-only checker agent.** Give it the numbered claims, the repos, and the library
   line. It must run `git fetch`, check staleness, and run `/deploy-identity` before it cites deployed code.
   Each claim gets one verdict with evidence:

   | Verdict | Meaning |
   |---|---|
   | `DEPLOYED` | Code on the deploy branch does this. Cite the file and the stamp. |
   | `IMPLEMENTED` | Code exists, but not on the deploy branch or not verified as deployed. |
   | `PLANNED` | A ticket or design exists. No code. |
   | `CONTRADICTED` | The code or the runtime does something different. Cite both. |
   | `UNVERIFIABLE` | No evidence either way. Goes to Open Questions. |

   The checker also lists new capabilities that the page does not mention. It splits them into
   user-facing and internal operations.
4. **Show the verdict table.** Ask the user only about ownership, contacts, and whether to keep
   planned features. Default: move `PLANNED` claims to a "Planned" section.
5. **Draft, review, then publish.** Write the draft to the ticket folder
   (`tickets/{PREFIX}/{EPIC}/{ID}/reports/notion/`), open it in the browser, and run `/crit`.
   Write to Notion only after explicit approval. Shelve the drift findings in the bibliothèque.

## Rules

- A `CONTRADICTED` or `DEPLOYED` verdict without a `verified_against` stamp is a hypothesis.
  File it under Open Questions.
- Never read `pages/` by hand. The read protocol in SKILL.md applies to this mode too.

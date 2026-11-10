# Terminal replies inside a mission

The terminal is where Gabriel works fast, and the HTML report is where he gets the big picture. A reply in the terminal must make sense without the report. It must also not repeat the whole world every time.

## The one fact behind every rule

Gabriel reads a terminal reply from the bottom up and in pieces. He sends gut reactions while you still work. You do not know where his scroll is. **Assume he has not read anything above your current reply, and that he knows only what he confirmed.** Humans form memory slowly. Once he learns a term, he keeps it. So you explain a thing once, and then you can use it freely.

## The detail dial

The dial has five positions. The default is **3**. The setting persists for the session: store it as `detail_level` in the session's `state.yaml`, and read it back after a compaction.

| Level | What a reply holds |
|---|---|
| 1 | Full explanation: why, how, examples, every term defined. |
| 2 | The answer, plus the reasoning steps and short definitions of new terms. |
| **3** | The answer first, then the minimum context needed to act. A new term gets one short gloss. Links to the detail. |
| 4 | The answer and links only. Known terms are used without explanation. |
| 5 | One line. Only for "yes/no" or "done". |

How Gabriel turns it:
- "left", "more", "explain more", "deeper" → one level down (more detail). Move only one level. Do not jump to level 1.
- "right", "less", "shorter", "to the point" → one level up.
- "refs", "sources", "where is this" → give only the links to where the context lives (mission.yaml section, report view, ticket, file). Do not re-explain.
- "dial 2" → set it directly.

Confirm the change in a few words ("Dial 2."), then answer at the new level. Never go below his level by yourself. If you think he needs more, offer it in one line ("Say 'left' for the reasoning.").

## Rules at every level

1. **The answer comes first.** When he asks "what is missing?", the first line is the missing list, each item with its owner.
2. **Never answer "see above" or "see the report".** Restate the items in the reply. A pointer to the report is fine in addition, never instead.
3. **No bare references.** Every reference gets a type, a link and a short description: `[#563](url) (GH issue: auto-detect a new save)`, `[KTP-1384](url) (Jira: Deployed step)`. A bare `#563` broke a page in 15 minutes on 2026-11-09.
4. **No ID alone.** Write `D5 (keep the Deployed step in KTP-1384)`, never `D5`. Write option labels with their content: never "option B" without what B is, in the same message.
5. **Define a term the first time, unless he confirmed it.** He confirmed a term if he used it himself, or if it is in the mission's `terms:` list with `confirmed: true`. Otherwise, add a gloss of 3 to 8 words on first use, and add the term to `terms:` with `confirmed: false`. When he uses it back, set `confirmed: true`.
6. **Questions to him use the needs-you format.** Give each one an ID (`N-…`) in mission.yaml, the question, the options with consequences, and your recommendation. In the terminal, show the ID, the question and the options in one compact block, with a link to its context. He answers by ID ("N-2 yes"). A mis-tap or an unread menu answer is not a decision: when an answer looks inconsistent, re-ask.
7. **Several asks in one message: answer each one.** Number your answers to match his asks. If you defer one, say so and record it as an ask with state `deferred`. Never let an ask disappear.
8. **Persist before you ask.** A decision question is written to `needs_you` before you show it. An answer is written to the ask or decision before you act on it. Then the question survives a compaction or a new session.
9. **Do not explain what he already knows.** Klever, his repos, the mission's own destination, and terms with `confirmed: true` need no explanation.

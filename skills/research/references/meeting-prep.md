# Meeting prep variant

Use this variant only when the user explicitly asks for research to prepare a meeting (for
example "/research prep for Thursday's map architecture meeting"). Do not start it from a
generic "meeting" cue. Post-meeting processing belongs to `meeting-to-action`.

## Inputs to confirm

- Meeting topic and date.
- The decision the meeting must make (one sentence).
- Key people and the role of each.
- Known context locations (repos, tickets, docs, threads). Ask only for what is missing.

## Method

- Research the decision, not the whole topic. Drop anything that does not change an option.
- One background agent is the default. Use parallel agents only when the sources are independent
  and large (for example code plus a vendor API plus a ticket backlog). Cap at four agents. Each
  agent returns at most about 500 words with a citation per claim.
- Primary sources only, same as the base skill. A Slack message or meeting note is a source for
  "who said what", not for how a system works.

## Output: one file, these sections

1. **Decision** (one sentence) and the date of the meeting.
2. **Options matrix**: option, what it costs, what it needs, evidence for, evidence against.
3. **Data feasibility**: for each option, can the data or system support it today? Cite it.
4. **Risks**: risk, which option it hits, likelihood, how to detect it early.
5. **Known unknowns**: question, who can answer it, and whether the meeting must answer it.
6. **Talking points**: at most five, each tied to an option or an unknown.
7. **Source index**: every cited source with its path or URL.

Keep the file under about 300 lines. Save it where the repo keeps meeting material. Match the
existing convention and say where you put it.

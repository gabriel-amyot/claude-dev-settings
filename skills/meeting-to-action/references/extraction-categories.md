# Extraction Categories Reference

When extracting knowledge from meeting topics, classify each item into one of these categories. Each has a specific format and downstream destination.

## Decisions

A choice that was made, with who made it and why.

**Format:**
```
### D{N}: {Short title}
**Decision:** {What was decided}
**Rationale:** {Why this option was chosen}
**Alternatives considered:** {What was rejected and why, if discussed}
**Owner:** {Who made the call}
**Source:** {Topic file reference}
```

**Downstream:** DECISIONS_LOG.md + potentially an ADR if architecturally significant.

## Action Items

Something someone committed to doing, with a deadline.

**Format:**
```
### A{N}: {Short description}
**Owner:** {Person}
**Deadline:** {Date or "ASAP" or "next sprint" — convert relative dates to absolute}
**Ticket candidate:** {Yes/No}
**Source:** {Topic file reference}
```

**Downstream:** If ticket candidate = Yes, flows to Formalize phase.

## Requirements

A new feature, capability, or change that was surfaced during the meeting.

**Format:**
```
### R{N}: {Feature/change title}
**Description:** {What's needed}
**Context:** {Why it came up}
**Scope hint:** {Epic, story, spike — if discussed}
**Priority hint:** {If discussed}
**Source:** {Topic file reference}
```

**Downstream:** Ticket candidate list in Synthesize phase.

## Constraints

Limitations, blockers, dependencies, or hard boundaries discovered.

**Format:**
```
### C{N}: {Constraint title}
**Constraint:** {What the limitation is}
**Impact:** {What this blocks or limits}
**Workaround:** {If discussed}
**Source:** {Topic file reference}
```

**Downstream:** Blocker sections in relevant tickets, or GABRIEL_INBOX if blocking current work.

## Open Questions

Items that need follow-up, were not resolved in the meeting.

**Format:**
```
### Q{N}: {Question}
**Context:** {Why this matters}
**Owner:** {Who should answer it}
**Deadline:** {When an answer is needed}
**Source:** {Topic file reference}
```

**Downstream:** GABRIEL_INBOX decisions section, or ticket blocker notes.

## Tribal Knowledge

Domain insights, gotchas, historical context, relationship dynamics, or vendor-specific knowledge that should be preserved.

**Format:**
```
### TK{N}: {Insight title}
**Insight:** {The knowledge}
**How to apply:** {When a future agent or person would need this}
**Source:** {Topic file reference}
```

**Downstream:** Bibliotheque inbox entry for curation.

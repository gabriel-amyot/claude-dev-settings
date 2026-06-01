---
name: meeting-to-action
description: "Turn strategic meetings into structured knowledge and actionable Jira tickets. Processes transcripts, audio, video, or notes through a 6-phase pipeline: ingest, scout context, extract knowledge, synthesize summaries, formalize to Jira, and adversarial verify. Use this skill whenever the user mentions processing a meeting, has a transcript to extract from, says 'what came out of this meeting', wants to turn meeting notes into tickets, or drops a recording/transcript file. Also triggers on 'process this meeting', 'extract from meeting', 'meeting recap', or any post-meeting workflow. Works for strategic meetings, architecture reviews, stakeholder conversations, vendor calls, and team planning sessions. Not for daily standups (use /morning-brief for those)."
user_invocable: true
nav:
  bay: plan
  when: "Turn meeting transcripts/audio/video into structured knowledge and Jira tickets."
  when_not: "Morning brief from transcript (use /morning-brief). Post-mortem debrief (use /bmad-debrief)."
  personas: [mary]
---

# Meeting to Action

Turn unstructured meetings into persistent knowledge and executable tickets.

## Invocation

```
/meeting-to-action                              # Interactive: ask for input
/meeting-to-action path/to/transcript.md        # Process a specific file
/meeting-to-action --mode extract               # Run only extraction phase
/meeting-to-action --mode synthesize,formalize   # Run specific phases
```

## Why This Exists

Strategic meetings produce hours of conversation. Without processing, decisions die in transcripts and people's heads. This skill runs a structured pipeline that captures knowledge into the Bibliotheque, creates Jira tickets from decisions, and cross-checks every claim against the source material before posting.

The pipeline delegates to existing skills where they fit (`/create-tickets` for Jira, `/bibliotheque-librarian` for knowledge curation, BMAD personas for adversarial review). This skill is the orchestrator that ties them together.

---

## Pipeline Overview

```
Ingest → Scout → Extract → Synthesize → [User Gate] → Formalize → Verify
```

Each phase writes output to disk. The user can enter at any phase (skip earlier ones) and exit after any phase (run partial pipelines). The default is the full sequence.

---

## Phase 1: Ingest

**Goal:** Turn raw meeting input into clean, chunked topic files.

### Supported inputs

| Input | How to process |
|-------|---------------|
| Markdown/text transcript | Read directly, split by topic shifts |
| Multiple chunk files (folder) | Read all, concatenate in order, then split by topic |
| Audio (.m4a, .mp3, .wav) | Write a Python script using `whisper` to transcribe, then process the text output. If whisper is not installed, tell the user and offer to write a script they can run manually. |
| Video (.mov, .mp4) | Same as audio (extract audio track first with ffmpeg, then whisper) |
| Slack thread dump | Parse messages, attribute speakers, split by topic |
| Pasted text in conversation | Save to disk first, then process |

### Output structure

Write ingested content to a meeting folder:

```
general/meetings/{date}-{slug}/
  raw/                    # Original input files (copy, don't move)
  topics/
    01-{topic-slug}.md    # One file per topic, numbered by discussion order
    02-{topic-slug}.md
    ...
  INDEX.md                # Topic list with one-liner descriptions
```

Each topic file should have:
- Clear topic heading
- Speaker attribution where possible (even approximate: "David mentioned...", "Amal suggested...")
- Timestamps or sequence indicators if available
- Raw quotes for important decisions (exact wording matters for verification later)

If the meeting is short or single-topic, a single topic file is fine. Don't force artificial splits.

---

## Phase 2: Scout

**Goal:** Understand what the project already knows before extracting new knowledge. This prevents contradictions and redundancy.

Read these sources (adapt paths based on detected org):

1. **Active tickets** — `tickets/` STATUS_SNAPSHOT.yaml files for in-progress work
2. **Bibliotheque** — `documentation/bibliotheque/INDEX.md` for existing domain knowledge
3. **Decisions log** — `general/meetings/DECISIONS_LOG.md` for prior decisions
4. **GABRIEL_INBOX.md** — for pending decisions and blockers
5. **Recent meeting notes** — last 2-3 meeting files in `general/meetings/`

Write a context brief to the meeting folder:

```
general/meetings/{date}-{slug}/
  context-brief.md        # What we already know, what's in flight, what's decided
```

The brief should be concise (under 100 lines). Focus on:
- Relevant active tickets and their status
- Decisions already made that the meeting might revisit
- Open questions from GABRIEL_INBOX that the meeting might answer
- People/roles involved and their domain ownership

This brief is consumed by the Extract phase to flag contradictions and confirm alignments.

---

## Phase 3: Extract

**Goal:** Turn topic files into a structured knowledge library.

For each topic file, extract:

| Category | What to capture | Example |
|----------|----------------|---------|
| **Decisions** | Choices made with rationale | "We're using Placer for foot traffic, not building our own. Rationale: time to market." |
| **Action items** | Who does what by when | "Mo will provide the crosswalk table by next Thursday" |
| **Requirements** | New features or changes surfaced | "The map needs to show visitor flow lines" |
| **Constraints** | Limitations discovered | "Placer API has a 2-week data lag" |
| **Open questions** | Unresolved items needing follow-up | "Do we need custom POIs or are managed entities sufficient?" |
| **Tribal knowledge** | Domain insights, gotchas, context | "Franchise brands index under consumer name, not parent company" |

Cross-reference against the Scout brief:
- **Confirms** an existing decision → note the confirmation, don't duplicate
- **Contradicts** an existing decision → flag prominently with both sources
- **Net-new** knowledge → mark for Bibliotheque ingestion

Write the knowledge library:

```
general/meetings/{date}-{slug}/
  knowledge/
    decisions.md           # All decisions with rationale and source topic
    action-items.md        # Who, what, when, ticket candidate? (yes/no)
    requirements.md        # Feature/change requests surfaced
    constraints.md         # Limitations, blockers, dependencies
    open-questions.md      # Unresolved, needs follow-up, who owns it
    tribal-knowledge.md    # Domain insights for Bibliotheque
    INDEX.md               # Summary of what was extracted
```

Not every file needs to exist. If the meeting produced no open questions, skip that file.

**Verification rule:** Every claim in the knowledge library must trace back to a specific topic file. Include the source reference: `(Topic 02, David)` or similar. No fabricated details. If the meeting didn't specify a number, deadline, or name, write "TBD" or "not specified."

---

## Phase 4: Synthesize

**Goal:** Produce team-facing outputs from the knowledge library.

### 4a. Meeting summary

Write `general/meetings/{date}-{slug}/summary.md`:

```markdown
# {Meeting Name} — {Date}

**Attendees:** {list}
**Duration:** {approximate}

## Key Decisions
{Numbered list, each with one-line rationale}

## Action Items
| Owner | Action | Deadline | Ticket? |
|-------|--------|----------|---------|

## What Changed
{2-3 sentences on what's different now vs before the meeting}

## Open Items
{Bullet list of unresolved questions with owners}
```

### 4b. Decisions log update

Append new decisions to `general/meetings/DECISIONS_LOG.md` following its existing format.

### 4c. Ticket candidates

From `action-items.md` and `requirements.md`, identify items that should become Jira tickets. Write a candidate list:

```
general/meetings/{date}-{slug}/
  ticket-candidates.md    # Items proposed for Jira creation
```

Each candidate should have:
- Proposed type (epic, story, spike, bug)
- Proposed summary (title)
- Draft scope (2-3 sentences)
- Parent epic if applicable
- Source reference (which topic/decision produced this)

### User gate

**Stop here and present the synthesis to the user.** Show:
1. The summary (for their review)
2. The ticket candidates (they decide which become real tickets)
3. Any contradictions flagged during extraction

Wait for the user to:
- Approve/edit the summary
- Select which candidates to formalize into tickets
- Resolve any contradictions
- Add anything the extraction missed

Do not proceed to Formalize without explicit user confirmation.

---

## Phase 5: Formalize

**Goal:** Turn approved ticket candidates into real Jira tickets with quality ACs.

For each approved candidate:

1. **Draft the ticket** following the template at `~/.claude-shared-config/skills/templates/jira-ticket-description.md` (read it if available; otherwise use Given/When/Then AC format with short titles)
2. **Run Leo AC review** — load the Leo persona file and review the ACs for quality:
   - Observable outcomes, not task lists
   - Actor perspective (can a dev implement? can QA assert?)
   - No vague language ("appropriate", "properly", "as needed")
3. **Present to user** — show all drafted tickets for final approval
4. **Create in Jira** — use `/jira` skill's create command
5. **Scaffold locally** — use `/ticket-init` to create local folders

This phase is essentially `/create-tickets` with the meeting knowledge as input. Delegate to that skill if it's available and the user prefers.

---

## Phase 6: Verify

**Goal:** Cross-check every output against the raw source material before anything goes external.

This is the adversarial pass. For every claim in:
- The meeting summary
- The decisions log updates
- The ticket descriptions

Verify against the raw topic files:

| Classification | Meaning |
|---------------|---------|
| **CONFIRMED** | Direct quote or clear paraphrase traceable to source |
| **INFERRED** | Reasonable conclusion from source, but not explicitly stated |
| **CONFABULATED** | Cannot be traced to any source material |

**Confabulated items must be fixed or removed before any external posting.** If a ticket description includes a detail not in the source, strip it or mark it as an assumption.

Write the verification report:

```
general/meetings/{date}-{slug}/
  verification-report.md   # CONFIRMED/INFERRED/CONFABULATED per claim
```

After verification passes, the outputs are safe for:
- Posting to Jira (ticket descriptions)
- Sharing on Slack (summary)
- Committing to the repo (knowledge library, decisions log)

---

## Tribal Knowledge Handoff

After the full pipeline (or after Extract if running partial), offer to run the Bibliotheque ingestion:

"The extraction produced tribal knowledge entries. Want me to route them to the Bibliotheque inbox for curation?"

If yes, write an inbox entry to `documentation/bibliotheque/inbox/` following the standard format and update `inbox/INDEX.md`. The `/bibliotheque-librarian` skill can promote them to the correct sections later.

---

## Mode Selection

Run specific phases with `--mode`:

```
/meeting-to-action --mode ingest              # Just clean up and chunk the transcript
/meeting-to-action --mode ingest,scout        # Ingest + context scout
/meeting-to-action --mode extract             # Extract from already-ingested topics
/meeting-to-action --mode synthesize          # Synthesize from already-extracted knowledge
/meeting-to-action --mode formalize           # Create tickets from existing candidates
/meeting-to-action --mode verify              # Adversarial check on existing outputs
```

When entering mid-pipeline, look for existing outputs from prior phases in the meeting folder. If they don't exist, ask the user to run the earlier phase first or provide the input.

---

## Org Detection

Detect org from the current working directory:
- `grp-beklever-com` → Klever. Meetings folder: `project-management/general/meetings/`
- `supervisr-ai` → Supervisr. Same relative structure.
- Otherwise → ask the user.

---

## Guidelines

- **Never fabricate numbers, dates, or names.** If the meeting didn't say it, write "TBD."
- **Exact quotes for decisions.** When someone makes a decision, capture their words, not your paraphrase.
- **Scout before extract.** Understanding existing state prevents contradictions.
- **User gates between Synthesize and Formalize.** The user decides what becomes a ticket.
- **Parked items still get documented.** Even deferred work goes to the knowledge library. Knowledge dies on local machines.
- **One meeting folder, one pipeline run.** Don't mix meetings in one folder.

# Skill Proposal: meeting-to-action
Date: 2026-04-13
Source: April 7 hedofice meeting processing session

## Problem

Strategic meetings produce hours of unstructured conversation. The knowledge dies in transcripts, Slack messages, and people's heads. Turning meetings into structured knowledge and actionable tickets is a manual, error-prone process that nobody does consistently. When it IS done (like this session), it takes significant orchestration: reading transcripts, building knowledge libraries, drafting epics, running BMAD parties, adversarial verification, Jira creation.

## Trigger

- User dumps a transcript, audio file, video file, or meeting notes
- User says "process this meeting", "extract from this meeting", "what came out of this meeting"
- User provides a folder of meeting chunks (like the april-7-hedofice structure)
- Post-meeting ritual: "we just had a meeting, here's the recording"

## Modes

### Mode 1: Ingest (transcript/audio/video → structured text)
- Accept: raw transcript files, audio (.m4a, .mp3, .wav), video (.mov, .mp4), Google Docs export, Slack thread dump
- For audio/video: extract transcript (Whisper or platform transcription)
- For messy transcripts: clean up speaker attribution, split by topic
- Output: chunked topic files ready for analysis

### Mode 2: Scout (understand current context before analyzing)
- Read existing tickets, epics, STATUS_SNAPSHOTs in project-management
- Read the bibliotheque for domain terms
- Read recent DECISIONS_LOG entries
- Read AGENT_BRIEFING.md for current priorities
- Build a "what we already know" baseline so the analysis doesn't reinvent or contradict existing state
- Output: context brief (what exists, what's in flight, what's decided)

### Mode 3: Extract (meeting content → knowledge library)
- Read all ingested content
- Build a topic-indexed knowledge library (one file per topic domain, with INDEX.md)
- Cross-reference against scout output: flag contradictions, confirm alignments, surface net-new decisions
- Output: knowledge library folder with INDEX.md catalog

### Mode 4: Synthesize (knowledge → team-facing output)
- Generate team-facing summary notes (additive to existing notes if provided)
- Generate Slack-ready summary (concise, focused on why/decisions/actions)
- Identify candidate epics, stories, spikes from decisions and action items
- Output: summary files + candidate ticket list

### Mode 5: Formalize (candidates → Jira tickets)
- Run BMAD party (Paige draft → Leo spec review → John PM review) on candidate tickets
- User participates in the debate
- Apply decisions, revise
- Adversarial verification against source transcripts before posting
- Create in Jira, scaffold locally
- Output: Jira tickets + local folders

### Mode 6: Verify (adversarial cross-check)
- Cross-check every claim in formalized output against raw source material
- Flag: CONFIRMED, INFERRED, CONFABULATED
- Fix confabulations before any external posting
- Mandatory before Jira creation or Slack posting

## Scope
Global (cross-org). Meetings happen everywhere.

## Pipeline (default full run)

```
Ingest → Scout → Extract → Synthesize → [User gate] → Formalize → Verify → Post
```

User can enter at any stage (e.g., "I already have the transcript, just extract" or "I have the knowledge library, formalize into tickets").

## Design Principles

- **Never fabricate numbers.** If the meeting didn't specify a target, write "TBD". Adversarial verification catches this.
- **Knowledge library is the artifact, not the conversation.** Everything persists to disk. Context can be compressed after each phase.
- **Scout before extract.** Understanding existing state prevents contradictions and redundancy.
- **User gates between phases.** Especially between Synthesize and Formalize. The user decides what becomes a ticket.
- **Parked items still get created.** Knowledge dies on local machines. Even deferred work goes to Jira for team visibility.

## Prior Art

This session manually executed the full pipeline. The pieces exist:
- Transcript reading: Agent tool with sonnet subagents for large files
- Knowledge library: Write tool with INDEX.md convention
- BMAD party: TeamCreate + persona agents (Paige, Leo, John)
- Adversarial review: Agent tool with opus for cross-checking
- Jira creation: /create-tickets skill + /jira skill
- Local scaffolding: /ticket-init skill

The skill wraps and orchestrates these into a repeatable pipeline.

## Estimated Complexity
High. Multi-phase, multi-agent, multiple input formats. But each phase is independently useful and can be built incrementally.

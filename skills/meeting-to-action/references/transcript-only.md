# Transcript-only mode (private recordings)

Use this mode when Phase 0 routes a recording as private. Examples: a one-on-one, a
conversation with interpersonal feedback about named colleagues, a personal call, or any
request that says "just the transcript", "transcribe only" or "no notes".

## Why

The full pipeline writes meeting folders, the decisions log, Bibliotheque inbox entries and
Jira tickets. Weekly notes feed `morning-brief` and `klever-3ps`, so a private conversation can
leak into team-visible standup content. A private recording and its transcript must never enter
weekly notes, a notes vault, a meetings folder or git.

## Procedure

1. Pick the output directory. Default: a `transcripts/` folder next to the source recording.
2. Run `scripts/check_private_dest.sh <output-dir>`. If it prints `REFUSED`, stop and ask the
   user for a different directory. Never override the refusal.
3. Probe the source with `ffprobe` (codecs, channels, duration).
4. Extract and normalize the audio, then transcribe. Follow
   `references/recording-recovery.md` for the commands. Emit `.txt` and `.srt`.
5. Optional: compress the recording (copy the video stream, downmix audio to mono AAC). Verify
   the duration matches within one second and the file decodes clean. Ask before you delete the
   original.
6. Optional: speaker attribution by content. Read only the `.txt`, map line numbers to speakers,
   merge onto the `.srt`, and assert full segment coverage. Say that the attribution is
   content-based, not acoustic. Flag segments that span a speaker change.
7. Stop. Report the transcript paths to the user.

## Forbidden in this mode

- No meeting folder under `general/meetings/`, no `topics/`, no `knowledge/`.
- No `DECISIONS_LOG.md` update, no Bibliotheque inbox entry, no Jira ticket, no Slack post.
- No action-item or insight extraction, no weekly-note write.
- No `git add` or commit of the recording or the transcript.
- Do not quote the transcript content into a session file, a handoff or a ledger entry.

If the user later asks to extract action items from a private recording, confirm in plain words
that the output stays private. Then write it only to a directory that passes the check.

Canonical detail (Klever bibliotheque): `sops/superwhisper-multilingual-transcription.md`,
section "A Private Recording Must Not Reach the Weekly Notes".

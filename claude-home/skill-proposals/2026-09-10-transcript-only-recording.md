# Skill Proposal: transcript-only-recording
Date: 2026-09-10
Source: crisp-lark — transcribing, moving and compressing two private one-on-one recordings

## Trigger

"Transcribe this recording", "just the transcript", "transcribe but no notes", or any
recording that is a private conversation rather than a project meeting.

Distinct from `process-meeting.sh`, which always generates vault notes and always runs
the weekly-note extraction. That extraction feeds `morning-brief` and `klever-3ps`, so
it is the wrong tool for a private one-on-one.

## Scope

Global. The toolchain (`ffmpeg`, `whisper-cli`, `~/.local/share/whisper-models`) is
machine-level, and the recordings path is resolved per org from
`.work-assistant-config/recordings_path.txt`.

## Draft Steps

1. **Probe before deciding anything.** `ffprobe` the source for codecs, channels and
   duration. These recordings are already AV1 video with uncompressed multi-channel
   PCM audio, so the video never needs re-encoding.
2. **Extract and normalize audio** per `sops/superwhisper-multilingual-transcription.md`:
   `highpass=f=80,dynaudnorm=f=150:g=15:p=0.9`, 16 kHz mono.
3. **Transcribe** with `large-v3-turbo`, loading the org's `whisper-prompt.txt` as
   `--prompt` when present. Emit both `--output-txt` and `--output-srt`.
4. **File the transcripts** to `{recordings_path}/transcripts/` using the existing
   `{project}_transcript_{date}_{time}.{txt,srt}` convention.
5. **Compress**: `-c:v copy -c:a aac -ac 1 -b:a 96k` to `_compressed.mkv`. Verify
   duration within 1 s and a clean decode, then ask before deleting the original.
6. **Optional speaker attribution.** Exploit the 1:1 `.txt`-line to `.srt`-segment
   mapping: attribute per line number, assert full coverage, merge against the `.srt`
   for timestamps. State plainly that it is content-based, not acoustic, and mark
   segments that span a speaker change.
7. **Stop.** No vault notes, no action-item extraction, no insight extraction, nothing
   into git.

## Notes

Everything above was executed by hand in this session and worked, so the steps are
proven rather than speculative. The value is packaging: it took roughly a dozen
tool calls and two diagnostic detours (the compression probe and the diarization
dead ends) that a skill would skip outright.

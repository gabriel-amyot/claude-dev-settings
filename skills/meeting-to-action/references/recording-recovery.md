# Recording ingestion and recovery (audio and video)

Use this reference for Phase 1 when the input is audio or video, and in transcript-only mode.
Load the frame-deck section only when the user explicitly asks for key frames.

Tooling on this machine: `ffmpeg`, `whisper-cli` (whisper.cpp), models in
`~/.local/share/whisper-models/`. Prefer `ggml-large-v3-turbo.bin`. The bundled SuperWhisper
model is English-only.

## 1. Probe

```bash
ffprobe -v error -show_entries stream=codec_type,codec_name,channels:format=duration -of compact in.mkv
```

## 2. Extract and normalize audio

```bash
ffmpeg -nostdin -y -i in.mkv -vn \
  -af "highpass=f=80,dynaudnorm=f=150:g=15:p=0.9" \
  -ar 16000 -ac 1 -c:a pcm_s16le norm.wav
```

Quiet recordings (about -45 dB or lower) drop words when you skip normalization.

## 3. Transcribe

```bash
whisper-cli -m ~/.local/share/whisper-models/ggml-large-v3-turbo.bin \
  -f norm.wav -l <lang> -otxt -osrt -of out
```

Load an org `whisper-prompt.txt` as `--prompt` when one exists. Do not use `--translate` on
Quebec French or code-switched speech. Translate the clean transcript instead.

## 3b. Speakers and mixed languages: `scripts/transcribe_meeting.py`

Use the script for any recording with more than one speaker. It wraps normalize, diarization
(sherpa-onnx, no HuggingFace token), whisper, attribution and render. Validated on two
2026-11-11 Klever recordings.

```bash
python3 ~/.claude-shared-config/skills/meeting-to-action/scripts/transcribe_meeting.py REC.wav \
  --out general/meetings/{date}-{slug}/raw --speakers 2 --names "Gabriel,David" --confidence medium \
  --lang-mode file --lang fr --prompt-file general/meetings/whisper-prompt.txt [--until SECONDS]
```

- `--speakers N` when known. Unknown: omit it. With many speakers on one microphone, clustering
  merges voices; pass `--anchors anchors.json` ({name: [row ids]} where the speaker is certain
  from content) to get voice-centroid suggestions, then set `speaker` and `confidence` by hand
  in `attribution.json` and rerun with `--render-only`.
- `--names` maps clusters in order of first appearance. Check two or three turns by content
  (who explains, who asks) before trusting the mapping.
- Code-switching with one dominant language (Quebec French + English terms): `--lang-mode file
  --lang fr`. `--lang-mode turn` picks a language per turn by token probability, but duplicates
  words at turn boundaries; use it only for long single-language stretches.
- `--until SECONDS` drops a private or off-topic tail. Privacy route still applies first.
- Never commit the audio. Commit only `raw/` text outputs.

## 4. Repeat-loop hallucination recovery

On silence, music or low speech, whisper can emit one line hundreds of times and lose the real
speech under it.

1. Detect: find runs of 3 or more identical consecutive lines in `out.txt`.
   `awk 'NR>1 && $0==prev {run++; next} {if (run>=2) print start": "prev" x"run+1; prev=$0; start=NR; run=0} END {if (run>=2) print start": "prev" x"run+1}' out.txt`
   Output format: `<first line>: <text> x<count>`.
2. Map the run's first and last line numbers to `.srt` timestamps (one `.txt` line per `.srt`
   segment).
3. Cut that window: `ffmpeg -ss A -to B -i norm.wav -c copy seg.wav`.
4. Re-transcribe the window with `-mc 0` (max context 0 breaks the self-conditioning loop).
5. Splice the new text over the garbage block. Re-run the detector to confirm no run is left.

## 5. Key-frame deck (explicit request only)

- Use interval sampling: `ffmpeg -i in.mkv -vf fps=1/30 frames/%04d.png`. Scene-change detection
  finds almost nothing on screen recordings.
- Write PNG, not JPEG. The mjpeg encoder rejects limited-range AV1 sources.
- Pair each frame with the transcript window at its timestamp.

## 6. Storage

Keep audio, video and frames on disk, out of git, and out of the conversation context. A
meeting folder records the media path. It never copies the media file into `raw/`.

Canonical detail (Klever bibliotheque): `sops/superwhisper-multilingual-transcription.md`.

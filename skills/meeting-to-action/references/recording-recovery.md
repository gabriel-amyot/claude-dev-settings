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

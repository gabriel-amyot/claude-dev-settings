# Skill Proposal: video-kt-transcribe
Date: 2026-06-16
Source: Marc-André data-pipeline KT (videos → transcript + frames)

## Trigger
User has a recorded knowledge-transfer / meeting video and wants a usable transcript + key-frame deck ("transcribe this video", "extract the transcript + snapshots", "turn this recording into notes").

## Scope
Global / personal tooling (cross-org). Mirrors the superwhisper-recovery memory.

## Draft Steps
1. Probe (`ffprobe` duration/streams); extract audio `ffmpeg -vn -ac 1 -ar 16000 -c:a pcm_s16le`.
2. Transcribe `whisper-cli -m ggml-large-v3-turbo -l <lang> -otxt -osrt -oj`.
3. Detect Whisper repeat-loop hallucinations (consecutive duplicate lines); recover each by cutting that segment + re-transcribing with `-mc 0` + splicing back.
4. Frames: interval-sample `fps=1/N` (scene-detect fails on static screen recordings); output PNG (mjpeg rejects limited-range AV1).
5. Build a transcript+frame deck (pair frames to transcript windows); optionally distill → knowledge.
6. Keep heavy media (audio/frames) gitignored / on disk; never load raw into context.

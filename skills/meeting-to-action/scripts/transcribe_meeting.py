#!/usr/bin/env python3
"""Transcribe a meeting recording with speakers and per-turn language.

Stages (each cached in OUT/work, rerun skips finished stages):
  1. normalize   ffmpeg highpass + dynaudnorm -> 16 kHz mono wav
  2. diarize     sherpa-onnx (pyannote segmentation 3.0 ONNX + WeSpeaker EN embedding), no HF token
  3. transcribe  --lang-mode file: one whisper-cli pass on the whole file (fast, one language)
                 --lang-mode turn: one whole-file pass per language in --langs (token level);
                 per speaker turn keep the language with the higher mean token probability
                 (code-switching; about 1 min per language for 20 min of audio)
  4. assemble    attribution.json (EDITABLE source of truth: speaker, confidence per row)
  5. render      transcript.md from attribution.json

Speaker names:
  --names "David,Gabriel"            cluster k -> k-th name, by first appearance (2-person calls)
  --anchors anchors.json             {"David": [row ids], ...}: voice centroids score every row,
                                     suggested speaker + margin written to attribution.json
  Then edit attribution.json (speaker, confidence) and run with --render-only.

Example:
  transcribe_meeting.py rec.wav --out general/meetings/2026-11-11-x/raw --speakers 2 \
      --lang-mode turn --langs en,fr --names "David,Gabriel" --prompt-file whisper-prompt.txt
"""
import argparse, json, os, re, subprocess, sys, urllib.request
from pathlib import Path

CACHE = Path.home() / ".cache" / "meeting-transcribe"
VENV = CACHE / "venv"
MODELS = CACHE / "models"
WHISPER_MODEL = Path.home() / ".local/share/whisper-models/ggml-large-v3-turbo.bin"
SEG_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
EMB_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx"


def ensure_venv():
    """Re-exec inside a private venv that has sherpa-onnx, soundfile and numpy."""
    try:
        import sherpa_onnx, soundfile, numpy  # noqa: F401
        return
    except ImportError:
        pass
    py = VENV / "bin" / "python"
    if not py.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(py), "-m", "pip", "-q", "install", "sherpa-onnx", "soundfile", "numpy"], check=True)
    os.execv(str(py), [str(py), *sys.argv])


def ensure_models():
    MODELS.mkdir(parents=True, exist_ok=True)
    seg = MODELS / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx"
    emb = MODELS / "wespeaker_en_voxceleb_resnet34_LM.onnx"
    if not seg.exists():
        tar = MODELS / "seg.tar.bz2"
        urllib.request.urlretrieve(SEG_URL, tar)
        subprocess.run(["tar", "-xjf", str(tar), "-C", str(MODELS)], check=True)
        tar.unlink()
    if not emb.exists():
        urllib.request.urlretrieve(EMB_URL, emb)
    return seg, emb


def ts(x):
    m, s = divmod(int(x), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def normalize(audio, work):
    out = work / "norm.wav"
    if not out.exists():
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(audio),
                        "-af", "highpass=f=80,dynaudnorm=f=150:g=15:p=0.9",
                        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True)
    return out


def diarize(norm, work, speakers, threshold):
    out = work / "diarization.json"
    if out.exists():
        return json.loads(out.read_text())
    import sherpa_onnx, soundfile as sf
    seg, emb = ensure_models()
    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(seg))),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(emb)),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=speakers or -1, threshold=threshold),
        min_duration_on=0.3, min_duration_off=0.5)
    audio, sr = sf.read(str(norm), dtype="float32")
    res = sherpa_onnx.OfflineSpeakerDiarization(cfg).process(audio).sort_by_start_time()
    d = [{"start": round(r.start, 2), "end": round(r.end, 2), "cluster": r.speaker} for r in res]
    out.write_text(json.dumps(d))
    return d


def cluster_at(diar, s, e):
    ov = {}
    for x in diar:
        o = min(e, x["end"]) - max(s, x["start"])
        if o > 0:
            ov[x["cluster"]] = ov.get(x["cluster"], 0) + o
    return max(ov, key=ov.get) if ov else None


def whisper(files, lang, prompt, extra=()):
    cmd = ["whisper-cli", "-m", str(WHISPER_MODEL), "-l", lang, "-t", "8", "-oj", "-np", *extra]
    if prompt:
        cmd += ["--prompt", prompt]
    for f in files:
        cmd += ["-f", str(f)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def smooth(rows, max_len, min_dur=1.5, min_words=4):
    """Diarization flips speakers on fragments; absorb short fragments into the previous row,
    then merge consecutive rows of the same speaker."""
    out = []
    for r in rows:
        short = (r["end"] - r["start"] < min_dur) and len(r["text"].split()) < min_words
        if out and (short or out[-1]["cluster"] == r["cluster"]) and r["end"] - out[-1]["start"] < max_len * 2:
            out[-1]["end"] = r["end"]; out[-1]["text"] += r["text"]; out[-1]["_p"] += r["_p"]
        else:
            out.append(r)
    return out


def transcribe_file(norm, work, diar, lang, prompt, max_len=28.0):
    """One whole-file pass in one language. Each token goes to the speaker who holds the
    resolved timeline at the token midpoint, so speaker turns split cleanly, with no duplicates.
    Use this for code-switched speech with one dominant language: whisper keeps the other
    language's words as spoken (e.g. --lang fr for Quebec French with English terms)."""
    timeline = non_overlapping(diar)
    starts = [t["start"] for t in timeline]
    import bisect

    def who(x):
        k = bisect.bisect_right(starts, x) - 1
        if k >= 0 and timeline[k]["start"] <= x < timeline[k]["end"] + 0.5:
            return timeline[k]["cluster"]
        return None
    rows = []
    for st, en, p, text in full_tokens(norm, work, lang, prompt):
        c = who((st + en) / 2)
        if c is None and rows:
            c = rows[-1]["cluster"]
        if rows and rows[-1]["cluster"] == c and st - rows[-1]["end"] < 1.5 and en - rows[-1]["start"] < max_len:
            rows[-1]["end"] = en; rows[-1]["text"] += text; rows[-1]["_p"].append(p)
        elif rows and not text.startswith(" ") and en - rows[-1]["start"] < max_len + 5:
            rows[-1]["end"] = en; rows[-1]["text"] += text; rows[-1]["_p"].append(p)
        else:
            rows.append({"start": st, "end": en, "cluster": c, "lang": lang, "text": text, "_p": [p]})
    rows = smooth(rows, max_len)
    for r in rows:
        r["text"] = r["text"].strip()
        r["mean_p"] = round(sum(r["_p"]) / len(r["_p"]), 3)
        del r["_p"]
    return rows


def non_overlapping(diar, frame=0.1, min_run=0.5):
    """Resolve overlapping diarization into one speaker per moment. Segmentation often emits
    one long segment for a speaker that spans the other speaker's short turns; plain trimming
    then deletes the short speaker. Rule: per 0.1 s frame the shortest active segment wins
    (the more specific claim). Runs shorter than min_run merge into the previous run."""
    if not diar:
        return []
    end = max(x["end"] for x in diar)
    n = int(end / frame) + 1
    best = [None] * n
    for x in sorted(diar, key=lambda x: x["end"] - x["start"], reverse=True):
        for f in range(int(x["start"] / frame), min(n, int(x["end"] / frame) + 1)):
            best[f] = x["cluster"]
    runs = []
    for f, c in enumerate(best):
        if c is None:
            continue
        t = f * frame
        if runs and runs[-1]["cluster"] == c and t - runs[-1]["end"] <= frame * 1.5:
            runs[-1]["end"] = t + frame
        else:
            runs.append({"start": t, "end": t + frame, "cluster": c})
    merged = []
    for r in runs:
        if merged and (r["end"] - r["start"] < min_run) and r["start"] - merged[-1]["end"] < 1.0:
            merged[-1]["end"] = r["end"]
        elif merged and merged[-1]["cluster"] == r["cluster"] and r["start"] - merged[-1]["end"] < 1.0:
            merged[-1]["end"] = r["end"]
        else:
            merged.append(dict(r))
    return [r for r in merged if r["end"] - r["start"] >= 0.3]


def full_tokens(norm, work, lang, prompt):
    """One whole-file pass in one language, token level: [(start, end, p, text)]."""
    base = work / f"full-{lang}"
    js = Path(str(base) + ".json")
    if not js.exists():
        cmd = ["whisper-cli", "-m", str(WHISPER_MODEL), "-l", lang, "-t", "8", "-ojf", "-np",
               "-of", str(base), "-f", str(norm)]
        if prompt:
            cmd += ["--prompt", prompt]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    toks = []
    for seg in json.loads(js.read_text())["transcription"]:
        for t in seg.get("tokens", []):
            if t["text"].startswith("[_") or t["text"].startswith("<|"):
                continue
            toks.append((t["offsets"]["from"] / 1000, t["offsets"]["to"] / 1000, t["p"], t["text"]))
    return toks


def transcribe_turns(norm, work, diar, langs, prompt, max_len=28.0):
    """Code-switching: whisper auto-detect misfires on short or mixed audio and then translates.
    Transcribe the whole file once per allowed language. For each speaker turn keep the language
    whose tokens in that window have the higher mean probability."""
    turns = []
    for x in non_overlapping(diar):
        s = x["start"]
        while x["end"] - s > max_len:
            turns.append({"start": s, "end": s + max_len, "cluster": x["cluster"]}); s += max_len
        turns.append({"start": s, "end": x["end"], "cluster": x["cluster"]})
    tok = {lang: full_tokens(norm, work, lang, prompt) for lang in langs}
    rows = []
    for t in turns:
        cand = []
        for lang, toks in tok.items():
            w = [x for x in toks if t["start"] <= (x[0] + x[1]) / 2 < t["end"]]
            if w:
                cand.append((sum(x[2] for x in w) / len(w), lang, "".join(x[3] for x in w).strip()))
        if not cand:
            continue
        cand.sort(reverse=True)
        r = {**t, "lang": cand[0][1], "text": cand[0][2],
             "lang_scores": {l: round(p, 3) for p, l, _ in cand}}
        if len(cand) > 1 and cand[0][0] - cand[1][0] < 0.03:
            r["lang_note"] = "close call between languages; check audio"
        rows.append(r)
    return rows


def score_anchors(rows, norm, anchors):
    import numpy as np, sherpa_onnx, soundfile as sf
    _, emb = ensure_models()
    ext = sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(emb)))
    audio, sr = sf.read(str(norm), dtype="float32")

    def vec(s, e):
        seg = audio[int(s * sr):int(e * sr)]
        if len(seg) < sr * 0.8:
            return None
        st = ext.create_stream(); st.accept_waveform(sr, seg); st.input_finished()
        v = np.array(ext.compute(st)); return v / np.linalg.norm(v)
    V = [vec(r["start"], r["end"]) for r in rows]
    C = {}
    for name, ids in anchors.items():
        vs = [V[i] for i in ids if i < len(V) and V[i] is not None]
        if vs:
            c = np.mean(vs, 0); C[name] = c / np.linalg.norm(c)
    for r, v in zip(rows, V):
        if v is None or not C:
            continue
        sc = sorted(((float(v @ c), n) for n, c in C.items()), reverse=True)
        r["voice_scores"] = {n: round(s, 3) for s, n in sc}
        r["suggested"] = sc[0][1]
        r["margin"] = round(sc[0][0] - sc[1][0], 3) if len(sc) > 1 else None


HALLUCINATION = re.compile(r"(.{6,60}?)(?:\s*\1){3,}")


def render(out, meta):
    rows = json.loads((out / "attribution.json").read_text())
    lines = []
    cur = None
    for r in rows:
        key = (r.get("speaker"), r.get("confidence"), r.get("lang"))
        if cur and cur["key"] == key:
            cur["text"].append(r["text"]); cur["last"] = r["i"]
        else:
            cur = {"key": key, "start": r["start"], "first": r["i"], "last": r["i"], "text": [r["text"]]}
            lines.append(cur)
    body = []
    for t in lines:
        spk, conf, lang = t["key"]
        tag = f"conf: {conf}, " if conf else ""
        body.append(f"**[{ts(t['start'])}] {spk}** _({tag}{lang}, rows {t['first']}-{t['last']})_  \n"
                    f"{' '.join(x for x in t['text'] if x)}\n")
    loops = [r["i"] for r in rows if HALLUCINATION.search(r["text"] or "")]
    head = [f"# Transcript: {meta.get('title', out.name)}", "",
            f"- Source audio (not committed): `{meta['audio']}`",
            f"- Method: {meta['method']}",
            f"- Rows: {len(rows)}. Repeat-loop suspects (rows): {loops or 'none'}",
            *([f"- Cut at {ts(meta['until'])}: later audio excluded (off-topic or private)."] if meta.get("until") else []),
            "- Edit `attribution.json` (speaker, confidence), then rerun with `--render-only`.", "", "---", ""]
    (out / "transcript.md").write_text("\n".join(head) + "\n".join(body))
    print(f"wrote {out / 'transcript.md'} ({len(lines)} turns, {len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--out", required=True, help="meeting raw/ folder (transcripts only, never media)")
    ap.add_argument("--work", help="scratch dir for wav/chunks (default /tmp/meeting-transcribe/<out name>)")
    ap.add_argument("--speakers", type=int, default=0, help="known speaker count (0 = estimate)")
    ap.add_argument("--threshold", type=float, default=0.5, help="clustering threshold when --speakers is 0")
    ap.add_argument("--lang-mode", choices=["file", "turn"], default="file")
    ap.add_argument("--lang", default="en", help="language for --lang-mode file")
    ap.add_argument("--langs", default="en,fr", help="allowed languages for --lang-mode turn")
    ap.add_argument("--prompt-file")
    ap.add_argument("--names", help="comma list: cluster names by first appearance")
    ap.add_argument("--anchors", help="json {name: [row ids]} for voice-centroid suggestions")
    ap.add_argument("--title")
    ap.add_argument("--until", type=float, help="drop rows starting after this second (off-topic or private tail)")
    ap.add_argument("--confidence", help="default confidence for every row when --names is used (e.g. medium)")
    ap.add_argument("--render-only", action="store_true")
    a = ap.parse_args()
    ensure_venv()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    meta_p = out / "transcribe-meta.json"
    if a.render_only:
        render(out, json.loads(meta_p.read_text())); return
    work = Path(a.work or f"/tmp/meeting-transcribe/{out.parent.name or out.name}")
    work.mkdir(parents=True, exist_ok=True)
    prompt = Path(a.prompt_file).read_text().strip() if a.prompt_file else None
    norm = normalize(Path(a.audio), work)
    diar = diarize(norm, work, a.speakers, a.threshold)
    langs = [x.strip() for x in a.langs.split(",") if x.strip()]
    rows = (transcribe_turns(norm, work, diar, langs, prompt) if a.lang_mode == "turn"
            else transcribe_file(norm, work, diar, a.lang, prompt))
    if a.until:
        rows = [r for r in rows if r["start"] < a.until]
    order = []
    for r in rows:
        if r["cluster"] is not None and r["cluster"] not in order:
            order.append(r["cluster"])
    names = [n.strip() for n in a.names.split(",")] if a.names else []
    for i, r in enumerate(rows):
        r["i"] = i
        k = order.index(r["cluster"]) if r["cluster"] in order else None
        r["speaker"] = names[k] if k is not None and k < len(names) else (f"SPEAKER_{k}" if k is not None else "UNKNOWN")
        r["confidence"] = a.confidence if names else None
    if a.anchors:
        score_anchors(rows, norm, json.loads(Path(a.anchors).read_text()))
    (out / "attribution.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    (out / "raw-segments.txt").write_text("".join(
        f"{r['i']:04d} {ts(r['start'])}-{ts(r['end'])} c{r['cluster']} {r['lang']} {r['text']}\n" for r in rows))
    meta = {"audio": str(Path(a.audio).resolve()), "title": a.title or out.parent.name,
            "until": a.until,
            "method": (f"ffmpeg normalize; sherpa-onnx diarization (speakers={a.speakers or 'auto'}, "
                       f"threshold={a.threshold}); whisper-cli large-v3-turbo, lang-mode={a.lang_mode}, "
                       f"langs={a.langs if a.lang_mode == 'turn' else a.lang}")}
    meta_p.write_text(json.dumps(meta, indent=1))
    render(out, meta)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
har_parse.py — Reusable HAR diagnostic parser.

Reads a HAR file, filters noise (static assets, map tiles, analytics), classifies
each remaining response (error / slow / empty / redirect / success), runs a data
quality audit on JSON bodies, and natively parses Server-Sent Events
(text/event-stream) responses.

Crucially, this prints a BOUNDED summary to stdout. It never dumps the full HAR.
The caller (an LLM) reads the summary, not the raw archive.

Usage:
    python3 har_parse.py <file.har>
    python3 har_parse.py <file.har> --focus-api /api/chatbot
    python3 har_parse.py <file.har> --sse
    python3 har_parse.py <file.har> --slow-threshold 3000
"""

import argparse
import base64
import json
import sys
from datetime import datetime

NOISE_SUFFIXES = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".ico", ".map",
)
NOISE_SUBSTRINGS = (
    "api.mapbox.com/styles/", "tiles.mapbox.com/", "api.mapbox.com/v4/",
    "events.mapbox.com",
    "google-analytics.com", "/gtag/", "googletagmanager.com",
    "segment.io", "segment.com", "hotjar.com", "doubleclick.net",
    "chrome-extension://",
)
SSE_PREVIEW_LEN = 120          # per-event content preview cap
MAX_EVENTS_SHOWN = 12          # events listed per SSE response
MAX_ROWS = 40                  # cap on any one report table


def url_path(url):
    """Strip scheme/host/query for compact display."""
    try:
        after = url.split("://", 1)[1]
        path = "/" + after.split("/", 1)[1] if "/" in after else "/"
        return path.split("?", 1)[0]
    except Exception:
        return url


def is_noise(url):
    low = url.lower()
    path = url_path(url).lower()
    if any(path.endswith(s) for s in NOISE_SUFFIXES):
        return True
    if low.startswith("data:"):
        return True
    return any(s in low for s in NOISE_SUBSTRINGS)


def header_get(headers, name):
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def decode_body(content):
    """Return the response body text, decoding base64 if HAR marked it so."""
    text = content.get("text", "") or ""
    if content.get("encoding") == "base64" and text:
        try:
            return base64.b64decode(text).decode("utf-8", errors="replace")
        except Exception:
            return text
    return text


def parse_sse(body):
    """Parse an SSE body into events. Each event is one or more `data:` lines.

    SSE groups lines into events separated by a blank line. Multiple `data:`
    lines within one event are concatenated with newlines per the spec. Most
    backends emit one data line per event, which we handle naturally.
    """
    events = []
    current = []
    event_name = None
    for raw in body.splitlines():
        line = raw.rstrip("\r")
        if line == "":
            if current or event_name:
                events.append(("\n".join(current), event_name))
                current = []
                event_name = None
            continue
        if line.startswith(":"):  # comment / heartbeat
            continue
        if line.startswith("data:"):
            current.append(line[5:].lstrip())
        elif line.startswith("event:"):
            event_name = line[6:].strip()
    if current or event_name:
        events.append(("\n".join(current), event_name))

    parsed = []
    for data, ev_name in events:
        item = {"event": ev_name, "step": None, "type": None,
                "content_preview": None, "parse_ok": False, "keys": []}
        try:
            j = json.loads(data)
            item["parse_ok"] = True
            if isinstance(j, dict):
                item["keys"] = list(j.keys())
                item["step"] = j.get("step")
                item["type"] = j.get("type")
                item["event"] = item["event"] or j.get("event")
                content = j.get("content") or j.get("message") or j.get("text")
                if content is not None:
                    s = content if isinstance(content, str) else json.dumps(content)
                    item["content_preview"] = s[:SSE_PREVIEW_LEN]
        except Exception:
            item["content_preview"] = data[:SSE_PREVIEW_LEN]
        parsed.append(item)
    return parsed


def audit_json(obj, path="", findings=None, depth=0):
    """Lightweight data-quality audit on a parsed JSON body. Bounded depth."""
    if findings is None:
        findings = []
    if depth > 4 or len(findings) > 20:
        return findings
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if isinstance(v, float):
                s = repr(v)
                if "." in s and len(s.split(".")[1]) > 6:
                    findings.append((p, "decimal precision >6", s))
            elif v == "":
                findings.append((p, "empty string", '""'))
            audit_json(v, p, findings, depth + 1)
    elif isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj):
            keysets = [frozenset(x.keys()) for x in obj]
            if len(set(keysets)) > 1:
                findings.append((path or "[]", "array key inconsistency",
                                 f"{len(set(keysets))} distinct shapes"))
        for x in obj[:5]:
            audit_json(x, path + "[]", findings, depth + 1)
    return findings


def classify(entry, slow_threshold):
    resp = entry.get("response", {})
    status = resp.get("status", 0)
    time_ms = entry.get("time", 0)
    content = resp.get("content", {})
    size = content.get("size", 0) or 0
    body = decode_body(content)
    stripped = body.strip()
    if status >= 400:
        return "error"
    if status >= 300:
        return "redirect"
    if status >= 200:
        # A body can be absent from the HAR even when the response was large
        # (browsers often omit big binary/geojson bodies). Only call it empty
        # when the body is genuinely small AND the reported size confirms it.
        body_missing_but_large = (not stripped) and size > 1024
        if not body_missing_but_large and (
            stripped in ("", "[]", "{}", "null", '""') or len(stripped) < 10
        ):
            return "empty"
        if time_ms > slow_threshold:
            return "slow"
        return "success"
    return "other"


def main():
    ap = argparse.ArgumentParser(description="Diagnose a HAR file (bounded summary).")
    ap.add_argument("har")
    ap.add_argument("--focus-api", default=None,
                    help="Only keep endpoints whose path starts with this prefix.")
    ap.add_argument("--sse", action="store_true",
                    help="Focus the report on text/event-stream responses only.")
    ap.add_argument("--slow-threshold", type=float, default=2000.0,
                    help="Response time (ms) above which a call is 'slow'.")
    args = ap.parse_args()

    try:
        with open(args.har, encoding="utf-8") as f:
            har = json.load(f)
    except Exception as e:
        print(f"ERROR: could not read HAR: {e}", file=sys.stderr)
        sys.exit(1)

    entries = har.get("log", {}).get("entries", [])
    total = len(entries)

    kept, filtered = [], 0
    for e in entries:
        url = e.get("request", {}).get("url", "")
        if is_noise(url):
            filtered += 1
            continue
        if args.focus_api and not url_path(url).startswith(args.focus_api):
            filtered += 1
            continue
        kept.append(e)

    # Build per-entry records.
    records, sse_records = [], []
    buckets = {"error": [], "slow": [], "empty": [], "redirect": [], "success": []}
    times = []
    for e in kept:
        req, resp = e.get("request", {}), e.get("response", {})
        headers = resp.get("headers", [])
        ct = header_get(headers, "content-type")
        started = e.get("startedDateTime", "")
        if started:
            times.append(started)
        rec = {
            "method": req.get("method", ""),
            "path": url_path(req.get("url", "")),
            "status": resp.get("status", 0),
            "time_ms": round(e.get("time", 0)),
            "size": resp.get("content", {}).get("size", 0) or 0,
            "ct": ct,
        }
        cls = classify(e, args.slow_threshold)
        rec["class"] = cls
        if cls in buckets:
            buckets[cls].append(rec)

        if "text/event-stream" in ct:
            body = decode_body(resp.get("content", {}))
            events = parse_sse(body)
            sse_records.append({
                "rec": rec,
                "headers": {
                    "Content-Type": ct,
                    "Content-Encoding": header_get(headers, "content-encoding"),
                    "Transfer-Encoding": header_get(headers, "transfer-encoding"),
                    "X-Accel-Buffering": header_get(headers, "x-accel-buffering"),
                    "Content-Length": header_get(headers, "content-length"),
                    "Cache-Control": header_get(headers, "cache-control"),
                },
                "events": events,
                "body_len": len(body),
            })
        else:
            rec["error_snippet"] = None
            if cls == "error":
                rec["error_snippet"] = decode_body(resp.get("content", {}))[:200]
            elif cls == "success" and "json" in ct.lower():
                try:
                    obj = json.loads(decode_body(resp.get("content", {})))
                    rec["audit"] = audit_json(obj)
                except Exception:
                    rec["audit"] = []
            records.append(rec)

    print_report(args, har, total, filtered, kept, buckets, sse_records, records, times)


def print_report(args, har, total, filtered, kept, buckets, sse_records, records, times):
    fname = args.har.split("/")[-1]
    out = []
    out.append("## HAR Diagnostic Report\n")
    out.append(f"**File:** {fname}")
    out.append(f"**Entries:** {len(kept)} analyzed ({filtered} filtered as noise, {total} total)")
    if times:
        out.append(f"**Time span:** {min(times)} to {max(times)}")
    if args.focus_api:
        out.append(f"**Focus:** {args.focus_api}")
    out.append("")

    # ---- SSE section ----
    if sse_records:
        out.append("### Server-Sent Events (text/event-stream)\n")
        out.append(f"Detected **{len(sse_records)}** SSE response(s).\n")
        for i, s in enumerate(sse_records, 1):
            r = s["rec"]
            out.append(f"#### SSE #{i}: {r['method']} {r['path']} — {r['status']}")
            hdr = s["headers"]
            hdr_line = ", ".join(f"{k}={v}" for k, v in hdr.items() if v)
            out.append(f"- Headers: {hdr_line or '(none of interest)'}")
            out.append(f"- Body size: {s['body_len']} bytes | Events parsed: {len(s['events'])}")
            chunked = "chunked" in hdr.get("Transfer-Encoding", "").lower()
            buffering_off = hdr.get("X-Accel-Buffering", "").lower() == "no"
            note = ("HAR captures the full stream as one body blob, so per-event "
                    "timing/incremental delivery is NOT visible here. ")
            if buffering_off:
                note += "X-Accel-Buffering=no indicates streaming was intended. "
            if chunked:
                note += "Transfer-Encoding=chunked confirms a streamed transport."
            out.append(f"- Note: {note.strip()}")
            if not s["events"]:
                out.append("- WARNING: 0 events parsed. Empty stream or the server "
                            "closed before emitting data (possible backend error or "
                            "aborted request).")
            else:
                shown = s["events"][:MAX_EVENTS_SHOWN]
                out.append("")
                out.append("| # | step | type | event | content preview |")
                out.append("|---|------|------|-------|-----------------|")
                for n, ev in enumerate(shown, 1):
                    prev = (ev["content_preview"] or "").replace("\n", " ").replace("|", "\\|")
                    bad = "" if ev["parse_ok"] else " (JSON parse failed)"
                    out.append(f"| {n} | {ev['step'] or '-'} | {ev['type'] or '-'} | "
                               f"{ev['event'] or '-'} | {prev}{bad} |")
                if len(s["events"]) > MAX_EVENTS_SHOWN:
                    out.append(f"\n_({len(s['events']) - MAX_EVENTS_SHOWN} more events not shown)_")
            out.append("")

    if args.sse:
        # SSE-focused mode: stop after the SSE section (plus a one-line tail).
        non_sse = len(records)
        out.append(f"_--sse mode: {non_sse} non-SSE responses suppressed._")
        emit(out)
        return

    # ---- Errors ----
    if buckets["error"]:
        out.append("### Critical Issues (errors)\n")
        out.append("| # | Endpoint | Status | Snippet |")
        out.append("|---|----------|--------|---------|")
        for n, r in enumerate(buckets["error"][:MAX_ROWS], 1):
            snip = next((x.get("error_snippet") for x in records
                         if x["path"] == r["path"] and x["status"] == r["status"]), None) or ""
            snip = snip.replace("\n", " ").replace("|", "\\|")
            out.append(f"| {n} | {r['method']} {r['path']} | {r['status']} | {snip} |")
        out.append("")

    # ---- Empty ----
    if buckets["empty"]:
        out.append("### Empty Responses (200 but no data)\n")
        out.append("| # | Endpoint | Size |")
        out.append("|---|----------|------|")
        for n, r in enumerate(buckets["empty"][:MAX_ROWS], 1):
            out.append(f"| {n} | {r['method']} {r['path']} | {r['size']}B |")
        out.append("")

    # ---- Slow ----
    if buckets["slow"]:
        out.append(f"### Performance Issues (>{int(args.slow_threshold)}ms)\n")
        out.append("| # | Endpoint | Time | Size |")
        out.append("|---|----------|------|------|")
        for n, r in enumerate(buckets["slow"][:MAX_ROWS], 1):
            out.append(f"| {n} | {r['method']} {r['path']} | {r['time_ms']}ms | {r['size']}B |")
        out.append("")

    # ---- Data quality ----
    dq = [(r, f) for r in records for f in r.get("audit", [])]
    if dq:
        out.append("### Data Quality Issues\n")
        out.append("| # | Endpoint | Field | Issue | Sample |")
        out.append("|---|----------|-------|-------|--------|")
        for n, (r, f) in enumerate(dq[:MAX_ROWS], 1):
            field, issue, sample = f
            sample = str(sample).replace("|", "\\|")[:40]
            out.append(f"| {n} | {r['path']} | {field} | {issue} | {sample} |")
        out.append("")

    # ---- Summary ----
    out.append("### Summary")
    out.append(f"- Errors: {len(buckets['error'])}")
    out.append(f"- Empty: {len(buckets['empty'])}")
    out.append(f"- Slow (>{int(args.slow_threshold)}ms): {len(buckets['slow'])}")
    out.append(f"- SSE responses: {len(sse_records)}")
    out.append(f"- Data quality flags: {len(dq)}")
    out.append(f"- Healthy: {len(buckets['success'])}")
    emit(out)


def emit(lines):
    print("\n".join(lines))


if __name__ == "__main__":
    main()

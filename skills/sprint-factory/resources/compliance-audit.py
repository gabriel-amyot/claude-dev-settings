#!/usr/bin/env python3
"""Dark Factory — Compliance Audit logic (Layer 2 backstop).

Invoked by compliance-audit.sh (a PostToolUse hook). Prints a plain-text
compliance report card to stdout. NEVER raises to the caller and never blocks:
any internal failure falls through to an informational line. The hook wrapper
turns whatever this prints into additionalContext for the agent.

Reads SEARCH_CWD from the environment (the hook's cwd) to bias the search for
the most recently modified pipeline-state.yaml.
"""

import os
import sys
import glob
import re

COMPLETEISH = {"complete", "completed", "shipping", "shipped",
               "validating", "qa", "reviewing"}


def file_lines(path):
    try:
        with open(path) as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def find_state_file():
    """Most recently modified pipeline-state.yaml across known roots."""
    home = os.path.expanduser("~")
    roots = []
    cwd = os.environ.get("SEARCH_CWD", "").strip()
    if cwd and cwd != "-" and os.path.isdir(cwd):
        roots.append(cwd)
    roots += [
        os.path.join(home, "Developer/grp-beklever-com/project-management/tickets"),
        os.path.join(home, "Developer/supervisr-ai/project-management/tickets"),
    ]
    candidates = []
    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        real = os.path.realpath(root)
        if real in seen:
            continue
        seen.add(real)
        for path in glob.glob(os.path.join(root, "**", "pipeline-state.yaml"),
                              recursive=True):
            try:
                candidates.append((os.path.getmtime(path), path))
            except OSError:
                pass
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def find_telemetry_file(ticket_keys):
    """Run telemetry (runs/run-*.yaml) tied to THIS run by ticket-key match.

    Returns None rather than reporting dispatch evidence from an unrelated run.
    """
    runs_dir = os.path.join(os.path.expanduser("~"),
                            ".claude/skills/dark-factory/runs")
    if not os.path.isdir(runs_dir):
        return None
    matches = []
    for p in glob.glob(os.path.join(runs_dir, "run-*.yaml")):
        try:
            with open(p) as f:
                blob = f.read()
            if any(k in blob for k in ticket_keys):
                matches.append((os.path.getmtime(p), p))
        except OSError:
            pass
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][1]


def per_ticket_dir(ticket_root, key):
    """Resolve the folder holding a ticket's qa/ and review/ artifacts."""
    if os.path.basename(ticket_root) == key:
        return ticket_root
    sib = os.path.join(os.path.dirname(ticket_root), key)
    if os.path.isdir(sib):
        return sib
    for p in glob.glob(os.path.join(ticket_root, "**", key), recursive=True):
        if os.path.isdir(p):
            return p
    return ticket_root


def ev_is_populated(ev):
    return ev is not None and str(ev).strip().lower() not in ("", "null", "none")


def build_report():
    home = os.path.expanduser("~")
    state_file = find_state_file()
    if not state_file:
        return ("DARK FACTORY COMPLIANCE AUDIT: no pipeline-state.yaml found "
                "to audit. (Audit is informational; nothing to report.)")

    ticket_root = os.path.dirname(state_file)

    # Tolerant YAML read.
    state = None
    try:
        import yaml
        with open(state_file) as f:
            state = yaml.safe_load(f)
    except Exception:
        state = None
    try:
        with open(state_file) as f:
            raw = f.read()
    except OSError:
        raw = ""

    tickets = {}
    if isinstance(state, dict) and isinstance(state.get("tickets"), dict):
        tickets = state["tickets"]

    telem_file = find_telemetry_file(list(tickets.keys()))
    telem_raw = ""
    if telem_file:
        try:
            with open(telem_file) as f:
                telem_raw = f.read()
        except OSError:
            telem_raw = ""

    def dispatch_seen(patterns):
        blob = (telem_raw or "") + "\n" + (raw or "")
        return any(re.search(p, blob, re.IGNORECASE | re.MULTILINE)
                   for p in patterns)

    # Phase 5 (Review) ran if telemetry carries a review phase block or a known
    # review delegation (external-review-agent, adversarial-cascade, Quinn).
    review_dispatch = dispatch_seen([r"external[-_]?review[-_]?agent",
                                     r"review-agent",
                                     r"adversarial-cascade",
                                     r"^\s*review\s*:",
                                     r"phase\s*:\s*review"])
    # Phase 6 (QA) ran if telemetry carries a qa phase block or a qa delegation.
    qa_dispatch = dispatch_seen([r"qa[-_ ]?agent",
                                 r"^\s*qa\s*:",
                                 r"phase\s*:\s*qa"])

    bar = "═" * 67
    dash = "─" * 67
    lines = [bar,
             " DARK FACTORY COMPLIANCE AUDIT (Layer 2 — out-of-band backstop)",
             " state: %s" % os.path.relpath(state_file, home)]
    if telem_file:
        lines.append(" telemetry: %s" % os.path.relpath(telem_file, home))
    lines.append(bar)

    if not tickets:
        present = bool(re.search(r'^\s*execution_verified\s*:', raw, re.MULTILINE))
        lines.append(" Could not parse a tickets: map from pipeline-state.yaml.")
        lines.append(" (PyYAML unavailable or non-standard state file. Informational.)")
        lines.append(" execution_verified field present in file: %s"
                     % ("yes" if present else "NO"))
        return "\n".join(lines)

    lines.append(" Run-level dispatch evidence (telemetry + state):")
    lines.append("   external-review-agent (Phase 5): %s"
                 % ("seen" if review_dispatch else "NOT SEEN"))
    lines.append("   qa-agent (Phase 6):              %s"
                 % ("seen" if qa_dispatch else "NOT SEEN"))
    lines.append(dash)

    total_flags = 0
    for key in sorted(tickets.keys()):
        t = tickets[key] or {}
        status = str(t.get("status", "")).lower()
        ev = t.get("execution_verified", None)
        tdir = per_ticket_dir(ticket_root, key)

        qa_reports = glob.glob(os.path.join(tdir, "qa", "qa-report.v*.md"))
        qa_ok = bool(qa_reports) and file_lines(sorted(qa_reports)[-1]) > 10

        review_dir = os.path.join(tdir, "review")
        review_ok = (os.path.isdir(review_dir)
                     and any(os.path.isfile(os.path.join(review_dir, f))
                             for f in os.listdir(review_dir)))

        if status not in COMPLETEISH:
            lines.append(" • %-10s [%s] in-progress — not yet audited for completion"
                         % (key, status or "?"))
            continue

        # Per-ticket compliance is judged on substantive on-disk artifacts.
        # Phase-dispatch telemetry is reported at run level (above) as advisory
        # context, not counted here — its naming is too variable to gate on.
        flags = []
        if not ev_is_populated(ev):
            flags.append("execution_verified missing/null")
        if not qa_ok:
            flags.append("qa report missing or stub")
        if not review_ok:
            flags.append("review/ empty")

        if flags:
            total_flags += len(flags)
            lines.append(" ✗ %-10s [%s] %s" % (key, status, "; ".join(flags)))
        else:
            lines.append(" ✓ %-10s [%s] execution_verified=%s, qa report ok, review/ ok"
                         % (key, status, ev))

    lines.append(dash)
    if total_flags == 0:
        lines.append(" VERDICT: clean — all completed tickets have full compliance artifacts.")
    else:
        lines.append(" VERDICT: %d compliance gap(s) flagged above." % total_flags)
        lines.append(" This audit does not block. But shipping a ticket with gaps means")
        lines.append(" the structural phase guarantees were bypassed. Investigate before")
        lines.append(" trusting the run's QA/review verdicts (KTP-713 self-certification).")
    lines.append(bar)
    return "\n".join(lines)


def main():
    try:
        report = build_report()
    except Exception as exc:  # audit must never crash the caller
        report = ("DARK FACTORY COMPLIANCE AUDIT: audit error (%s). "
                  "Informational only; not blocking." % exc)
    sys.stdout.write(report)


if __name__ == "__main__":
    main()

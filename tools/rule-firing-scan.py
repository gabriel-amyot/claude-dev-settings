#!/usr/bin/env python3
"""rule-firing-scan.py — measure which CLAUDE.md rules actually fire in real sessions.

Phase 6 of the CLAUDE.md tier migration. Every earlier cut was made on
classification and judgment. This replaces judgment with a measurement.

WHY A PHRASE SCAN IS VALID HERE
Claude Code does not persist the injected CLAUDE.md body into the transcript
JSONL (verified: 0 occurrences of `claudeMd` and of the literal rule text
"NEVER create a branch here" across the 10 largest Klever transcripts). So a
phrase match inside a transcript is genuine evidence that the rule was cited,
quoted, or reasoned about. It is not an echo of the system prompt.

FOUR EVIDENCE CHANNELS, strongest first:
  quote     a verbatim window of the rule's own wording appears in a session
  conjunct  all of the rule's rare vocabulary co-occurs inside ONE record
  artifact  the concrete thing the rule mandates was actually done
            (the skill was invoked, the helper was run, the backup dir written)
  hook      the mechanical backstop for the rule fired or was named

The `artifact` channel is the answer to "a rule can be followed without being
named". A rule that says "always use /klever-mr" leaves a trace even when the
model never quotes the rule.

ROLE ATTRIBUTION
A match in a user record is Gabriel saying the thing, which is not the rule
firing. A match in assistant text or thinking is the model applying it. The
script attributes a capped sample of hits so the two never get conflated.

Usage:
  python3 rule-firing-scan.py [--days N] [--out report.md] [--no-attribute]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HOME = Path.home()
PROJECTS = HOME / ".claude" / "projects"

TARGETS = [
    ("global", HOME / ".claude-shared-config" / "CLAUDE.md"),
    ("klever", HOME / "Developer" / "grp-beklever-com" / "project-management" / "CLAUDE.md"),
]

# A Klever-scoped rule only loads in sessions whose cwd is under the Klever org.
# Judging it against the full 146-project corpus understates it.
KLEVER_DIR_MARK = "grp-beklever-com"

STOPWORDS = set("""
a an the and or but if then than that this these those there here it its it's is are was were be been being
do does did doing done have has had having will would shall should can could may might must not no nor
of in on at to from by for with without within into onto over under about across after before during
you your yours we our ours they their them he she his her i me my mine as so such only just also even
what which who whom whose when where why how all any both each few more most other some own same
one two three first second next last new old very too much many any every per via etc eg ie
use used uses using make makes made get gets got go goes going see sees seen say says said
never always must-not dont don't cannot can't wont won't isn't aren't
rule rules file files line lines text case cases thing things way ways time times
claude agent agents session sessions user users work works working
""".split())

# ---------------------------------------------------------------------------
# Curated channel maps.
#
# Keyed by a regex matched against the rule's own text. These encode "what
# would I see on disk if this rule were obeyed silently", which no automatic
# phrase extraction can infer.
# ---------------------------------------------------------------------------

ARTIFACT_MAP = [
    (r"klever-mr|merge request|create an mr", ['"skill":"klever-mr"', "/klever-mr", "klever-mr skill"]),
    (r"post-comment|external post|externally visible", ['"skill":"post-comment"', "/post-comment"]),
    (r"jira_skill|jira skill|/jira", ["jira_skill.py", '"skill":"jira"']),
    (r"ledger\.yaml|ledger helper", ["ledger --org", "ledger.py", "LEDGER_WRITES.md"]),
    (r"worktree", ["git worktree add", "using-git-worktrees", "worktree remove"]),
    (r"deploy-identity|which branch deploys|deployed code", ["/deploy-identity", "deploy-identity/probe.sh", "[verified against"]),
    (r"crit|inline review", ['"skill":"crit"', "/crit:crit", "crit comment", "crit share"]),
    (r"ui-probe|klever-test|browser testing|live ui", ['"skill":"ui-probe"', '"skill":"klever-test"', "/ui-probe", "/klever-test"]),
    (r"terraform|infra", ["klever-terraform-infra", "terraform plan", "terraform apply"]),
    (r"bibliot|library-first|aliases\.md", ["bibliotheque-recall", "ALIASES.md", "Library: silent", "bibliotheque-librarian"]),
    (r"ste|anti-slop|writing style", ["ste_lint.py", "ste-software-allowlist"]),
    (r"graphify", ['"skill":"graphify"', "/graphify"]),
    (r"1password|secret|credential|token", ["op read", "op item get", "op://"]),
    (r"branch naming|ticket-id.*short-description", ["-b KTP-", "-b SPV-", "checkout -b KTP-"]),
    (r"version bump|changelog", ["CHANGELOG.md", "version bump"]),
    (r"back.?up|data mutation|datastore", ["data/backups/", "backups/"]),
    (r"ac-local", ["AC-LOCAL.md"]),
    (r"inbox", ["general/inboxes/gabriel", "inbox-writer"]),
    (r"file placement|ticket folder|tickets/", ["tickets/KTP/", "tickets/SPV/", "no-epic/"]),
    (r"session_state|persist state|compaction", ["SESSION_STATE.md", "sessions/active/"]),
    (r"status_snapshot|front loader", ["STATUS_SNAPSHOT.yaml"]),
    (r"ac\.yaml|recovery save point", ["jira/ac.yaml"]),
    (r"bmad|persona", ["_bmad/bmm/agents/", "bmm/agents/dev.md", "bmm/agents/qa.md"]),
    (r"adr|architecture decision", ["agent-os/", "push-adr", "ADR-"]),
    (r"index\.md|recursive index|every write requires", ["INDEX.md"]),
    (r"screenshot|visual proof|evidence", ["upload-attachment", "screencapture"]),
    (r"dark-factory|sprint-factory|sprint-crawl|autonomous", ["/dark-factory", "/sprint-factory", "/sprint-crawl", "ralph-loop"]),
    (r"schema|bigquery|bq ", ["bq show", "bq query", "INFORMATION_SCHEMA"]),
    (r"spring profile|application.*properties", ["spring.profiles.active", "application-local.properties"]),
    (r"pptx", ["ppt/media/", "zipfile"]),
]

HOOK_MAP = [
    (r"branch|merged", ["branch-guard.sh"]),
    (r"worktree", ["worktree-guard.sh"]),
    (r"project-management|single-trunk|never branch", ["pm-single-trunk-guard.sh"]),
    (r"ledger", ["ledger-write-guard.sh"]),
    (r"deploy|branch deploys", ["deploy-identity-guard.sh", "challenge-detect.sh"]),
    (r"bibliot|library", ["library-stamp-guard.sh", "bibliotheque-recall.sh"]),
    (r"config|\.env|delete", ["file-guard.sh"]),
    (r"file placement|tickets/", ["ticket-path-guard.sh"]),
    (r"claude\.md|tier", ["claude-md-tier-lint.sh"]),
    (r"agents\.md|mirror", ["agents-md-mirror.sh"]),
]


# ---------------------------------------------------------------------------
# Rule extraction
# ---------------------------------------------------------------------------

def clean_markdown(s: str) -> str:
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = s.replace("**", "").replace("`", "").replace("*", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


class Rule:
    __slots__ = ("rid", "scope", "heading", "lead", "text", "nbytes",
                 "quotes", "tokens", "artifacts", "hooks")

    def __init__(self, rid, scope, heading, lead, text, nbytes):
        self.rid = rid
        self.scope = scope
        self.heading = heading
        self.lead = lead
        self.text = text
        self.nbytes = nbytes
        self.quotes = []
        self.tokens = []
        self.artifacts = []
        self.hooks = []


def parse_rules(scope: str, path: Path) -> list[Rule]:
    """Split a CLAUDE.md into rule units.

    A unit is a top-level bullet (with its continuation lines), or the
    non-bullet prose of a heading section.
    """
    lines = path.read_text(encoding="utf-8").split("\n")
    rules: list[Rule] = []
    heading = "(preamble)"
    buf: list[str] = []
    buf_kind = None  # "bullet" | "prose"
    seq = 0

    def flush():
        nonlocal buf, buf_kind, seq
        if not buf:
            buf, buf_kind = [], None
            return
        raw = "\n".join(buf)
        body = clean_markdown(raw)
        # Drop pure structure with no rule content.
        if len(body) < 40:
            buf, buf_kind = [], None
            return
        seq += 1
        first = re.match(r"^\s*[-*]\s*(.+?)(?:[.:]|$)", body)
        lead = (first.group(1) if first else body)[:90]
        rid = f"{scope[:1].upper()}{seq:03d}"
        rules.append(Rule(rid, scope, heading, lead, body, len(raw.encode())))
        buf, buf_kind = [], None

    for ln in lines:
        if re.match(r"^#{1,4} ", ln):
            flush()
            heading = clean_markdown(re.sub(r"^#+\s*", "", ln))
            continue
        if re.match(r"^\s*[-*] ", ln) and not re.match(r"^\s+[-*] ", ln):
            flush()
            buf, buf_kind = [ln], "bullet"
            continue
        if buf_kind == "bullet":
            if ln.strip() == "":
                flush()
            else:
                buf.append(ln)
            continue
        # prose / table body under a heading
        if ln.strip() == "" or ln.strip() == "---":
            flush()
        else:
            buf.append(ln)
            buf_kind = "prose"
    flush()
    return rules


ASCII_OK = re.compile(r"^[ -~]+$")


def quote_windows(text: str, n_words: int = 8, max_q: int = 3) -> list[str]:
    """Distinctive verbatim windows, safe to match against JSON-escaped text."""
    out = []
    for sent in re.split(r"(?<=[.:;])\s+", text):
        sent = sent.strip().lstrip("-*• ")
        if '"' in sent or "\\" in sent or not ASCII_OK.match(sent):
            continue
        words = sent.split()
        if len(words) < n_words:
            continue
        w = " ".join(words[:n_words]).lower()
        if len(w) >= 30:
            out.append(w)
        if len(out) >= max_q:
            break
    return out


TOKEN_RE = re.compile(r"[a-z][a-z0-9_.:/-]{3,}")


def rule_tokens(text: str) -> list[str]:
    seen = []
    for m in TOKEN_RE.finditer(text.lower()):
        t = m.group(0).strip("-._:/")
        if len(t) < 4 or t in STOPWORDS or t in seen:
            continue
        seen.append(t)
    return seen


TECHNICAL = re.compile(r"[./_\-]|\d")


def distinctiveness(tok: str, df: int) -> float:
    """Prefer paths, filenames and long compounds over ordinary English.

    A generic token like "available" in the required set makes the conjunction
    test stricter, which reads as a dead rule when it is really a bad probe.
    """
    score = min(len(tok), 14) / 3.0
    if TECHNICAL.search(tok):
        score += 4.0
    if len(tok) >= 9:
        score += 1.5
    return score - 2.0 * (df - 1)


def build_patterns(rules: list[Rule], n_tokens: int = 2):
    df = Counter()
    per_rule = {}
    for r in rules:
        toks = rule_tokens(r.text)
        per_rule[r.rid] = toks
        for t in set(toks):
            df[t] += 1

    for r in rules:
        toks = per_rule[r.rid]
        cand = [t for t in toks if df[t] <= 2]
        cand.sort(key=lambda t: -distinctiveness(t, df[t]))
        r.tokens = cand[:n_tokens]
        # A probe built only from ordinary English words is unreliable; widen it.
        if r.tokens and not any(TECHNICAL.search(t) or len(t) >= 9 for t in r.tokens):
            r.tokens = [t for t in cand if len(t) >= 6][:3] or r.tokens
        r.quotes = quote_windows(r.text)
        low = r.text.lower()
        for pat, arts in ARTIFACT_MAP:
            if re.search(pat, low):
                r.artifacts.extend(a.lower() for a in arts)
        for pat, hks in HOOK_MAP:
            if re.search(pat, low):
                r.hooks.extend(h.lower() for h in hks)
        r.artifacts = sorted(set(r.artifacts))
        r.hooks = sorted(set(r.hooks))


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def collect_files(days: int | None):
    cutoff = 0 if not days else time.time() - days * 86400
    out = []
    for d in PROJECTS.iterdir():
        if not d.is_dir():
            continue
        for f in d.glob("*.jsonl"):
            try:
                if f.is_file() and f.stat().st_mtime >= cutoff:
                    out.append(f)
            except OSError:
                continue
    return out


def run_rg(patterns: list[str], days: int | None, tmp: Path):
    """One ripgrep pass. Streams `path:lineno:match` back for aggregation."""
    tmp.write_text("\n".join(patterns) + "\n", encoding="utf-8")
    # -n is mandatory: piped rg output omits line numbers unless asked, and the
    # record-level conjunction test depends on them.
    cmd = ["rg", "-o", "-i", "-H", "-n", "--no-heading", "-F", "-f", str(tmp),
           "--glob", "*.jsonl", "--no-messages", str(PROJECTS)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, errors="ignore", bufsize=1 << 20)
    # pattern -> (path, lineno) hits
    hits: dict[str, set] = defaultdict(set)
    nlines = 0
    for line in proc.stdout:
        nlines += 1
        try:
            path, rest = line.split(".jsonl:", 1)
            lineno, match = rest.split(":", 1)
        except ValueError:
            continue
        hits[match.strip().lower()].add((path + ".jsonl", lineno))
    proc.wait()
    return hits, nlines


def session_of(path: str) -> str:
    return path


def is_klever(path: str) -> bool:
    return KLEVER_DIR_MARK in path


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Violation probes
#
# A rule that is never cited AND is being broken is the opposite of a cut
# candidate: it needs a hook. These probes look for the forbidden act itself,
# in model-authored records only, so Gabriel quoting a bad command does not
# count against the agent.
# ---------------------------------------------------------------------------

#   name, rg regex (coarse prefilter), python regex (precise), scope
# scope "bash" tests the Bash tool's `command` field only, so prose that merely
# names a forbidden command cannot count. "text" tests assistant prose.
VIOLATION_PROBES = [
    ("G025 git commands chained with &&",
     r"git (?:status|fetch|add|log|diff|show|rev-list|branch|checkout|stash)[^\"]{0,60}&& *git ",
     r"git (?:status|fetch|add|log|diff|show|rev-list|branch|checkout|stash)[^\n]{0,60}&& *git ",
     "bash"),
    ("G025 git piped into a filter",
     r"git (?:log|diff|show|branch|status|rev-list)[^\"]{0,50}\| *(?:grep|head|tail|awk|sed|wc|xargs)",
     r"git (?:log|diff|show|branch|status|rev-list)[^\n]{0,50}\| *(?:grep|head|tail|awk|sed|wc|xargs)",
     "bash"),
    ("G031 git history rewrite",
     r"git (?:push +(?:--force|-f)\b|rebase +(?!--abort)|reset +--hard|commit +--amend)",
     r"git (?:push +(?:--force|-f)\b|rebase +(?!--abort)|reset +--hard|commit +--amend)",
     "bash"),
    ("G074 terraform plan/apply actually run",
     r"terraform +(?:plan|apply)",
     r"(?:^|[;&|]|\bthen\s|\bexec\s)\s*(?:sudo +)?terraform +(?:plan|apply)",
     "bash"),
    ("branch naming: fix//feature//chore/ prefix",
     r"checkout +-b +(?:fix|feature|chore|bugfix)/",
     r"checkout +-b +(?:fix|feature|chore|bugfix)/",
     "bash"),
    ("DAC: git push to main or uat (repo type unchecked)",
     r"git push +origin +(?:main|uat)\b",
     r"git push +origin +(?:main|uat)\b",
     "bash"),
    ("emoji in model prose shown to the user",
     r"[\x{1F300}-\x{1FAFF}\x{2705}\x{274C}\x{1F534}\x{1F7E2}]",
     r"[\U0001F300-\U0001FAFF✅❌\U0001F534\U0001F7E2]",
     "text"),
]


def _blocks_for_scope(rec: dict, scope: str) -> list:
    """Extract only the strings the rule actually governs."""
    m = rec.get("message")
    if not isinstance(m, dict) or m.get("role") != "assistant":
        return []
    c = m.get("content")
    if not isinstance(c, list):
        return []
    out = []
    for b in c:
        if not isinstance(b, dict):
            continue
        if scope == "bash" and b.get("type") == "tool_use" and b.get("name") == "Bash":
            cmd = (b.get("input") or {}).get("command")
            if isinstance(cmd, str):
                out.append(cmd)
        elif scope == "text" and b.get("type") == "text":
            t = b.get("text")
            if isinstance(t, str):
                out.append(t)
    return out


def run_violation_probes(eligible: set) -> list:
    """Coarse rg prefilter, then precise validation inside the governed field."""
    results = []
    for name, rgpat, pypat, scope in VIOLATION_PROBES:
        cmd = ["rg", "-o", "-n", "-H", "--no-heading", "--no-messages",
               "-e", rgpat, "--glob", "*.jsonl", str(PROJECTS)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  errors="ignore", timeout=1800)
        except Exception:
            results.append((name, 0, 0, 0, "probe failed"))
            continue
        needed = defaultdict(set)
        raw = 0
        for line in proc.stdout.splitlines():
            try:
                path, rest = line.split(".jsonl:", 1)
                lineno = rest.split(":", 1)[0]
                path += ".jsonl"
            except ValueError:
                continue
            if path not in eligible:
                continue
            raw += 1
            needed[path].add(int(lineno))

        coarse_sess = len(needed)
        rx = re.compile(pypat, re.MULTILINE)
        confirmed = set()
        for path, linenos in needed.items():
            try:
                with open(path, errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if i not in linenos:
                            continue
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        for s in _blocks_for_scope(rec, scope):
                            if rx.search(s):
                                confirmed.add(path)
                                break
            except OSError:
                continue
        results.append((name, len(confirmed), coarse_sess, raw, scope))
    return results


def classify_lines(needed: dict[str, set]) -> dict:
    """Label each contributing record by WHO authored it.

    This is the load-bearing correction. A rule's wording appearing in a
    `tool_result` means the agent read CLAUDE.md, a library page or a proposal
    off disk. That is a documentation echo, not the rule firing. Counting it
    inflates every rule that happens to be written down somewhere.

      model    assistant record - the model's own text, thinking or tool call
      toolout  tool output read back in - documentation echo, NOT firing
      human    Gabriel's own words - he invoked the rule, the model did not
      other    hook injections, attachments, snapshots
    """
    out = {}
    for path, linenos in needed.items():
        try:
            with open(path, errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if i not in linenos:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        out[(path, i)] = "other"
                        continue
                    t = rec.get("type")
                    m = rec.get("message")
                    if t == "assistant" or (isinstance(m, dict) and m.get("role") == "assistant"):
                        out[(path, i)] = "model"
                        continue
                    if isinstance(m, dict) and m.get("role") == "user":
                        c = m.get("content")
                        kinds = {b.get("type") for b in c if isinstance(b, dict)} if isinstance(c, list) else {"str"}
                        out[(path, i)] = "toolout" if "tool_result" in kinds else "human"
                        continue
                    out[(path, i)] = "other"
        except OSError:
            continue
    return out


def attribute(candidates: dict, cap_per_rule: int = 4):
    """Classify a capped sample of hits by record role and block type."""
    by_file = defaultdict(list)
    for rid, pairs in candidates.items():
        for (path, lineno) in list(pairs)[:cap_per_rule]:
            by_file[path].append((int(lineno), rid))

    roles = defaultdict(Counter)
    for path, wants in by_file.items():
        want = {ln: rid for ln, rid in wants}
        try:
            with open(path, errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    rid = want.get(i)
                    if rid is None:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        roles[rid]["unparsed"] += 1
                        continue
                    m = rec.get("message")
                    if not isinstance(m, dict):
                        roles[rid][rec.get("type") or "other"] += 1
                        continue
                    role = m.get("role") or "?"
                    c = m.get("content")
                    kinds = set()
                    if isinstance(c, list):
                        for b in c:
                            if isinstance(b, dict):
                                kinds.add(b.get("type"))
                    else:
                        kinds.add("str")
                    for k in sorted(kinds):
                        roles[rid][f"{role}/{k}"] += 1
        except OSError:
            continue
    return roles


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0, help="0 = all history")
    # Machine-generated data only. The human-authored analysis lives beside it in
    # 2026-08-27-rule-firing-evidence.md, so re-running cannot clobber conclusions.
    ap.add_argument("--out", default=str(HOME / "Developer" / "grp-beklever-com" /
                                        "project-management" / "documentation" / "process" /
                                        "proposals" / "2026-08-27-rule-firing-data.md"))
    ap.add_argument("--no-attribute", action="store_true")
    args = ap.parse_args()

    days = args.days or None

    rules: list[Rule] = []
    for scope, path in TARGETS:
        if not path.exists():
            print(f"missing target: {path}", file=sys.stderr)
            sys.exit(2)
        rules += parse_rules(scope, path)
    build_patterns(rules)

    files = collect_files(days)
    klever_files = [f for f in files if is_klever(str(f))]

    # ---- one combined pattern pass
    pat_owner = defaultdict(list)  # pattern -> [(rid, channel)]
    for r in rules:
        for q in r.quotes:
            pat_owner[q].append((r.rid, "quote"))
        for t in r.tokens:
            pat_owner[t].append((r.rid, "token"))
        for a in r.artifacts:
            pat_owner[a].append((r.rid, "artifact"))
        for h in r.hooks:
            pat_owner[h].append((r.rid, "hook"))

    tmp = Path("/tmp/rule-firing-patterns.txt")
    hits, nmatch = run_rg(sorted(pat_owner), days, tmp)

    # ---- pass A: which records contribute, per rule and channel
    eligible_all = {str(f) for f in files}
    eligible_klever = {str(f) for f in klever_files}
    per_rule_lines = {}

    def lines_for(pattern_list, eligible):
        s = set()
        for p in pattern_list:
            for (path, ln) in hits.get(p, ()):
                if path in eligible:
                    s.add((path, ln))
        return s

    # Corpus session-frequency per token. Rarity WITHIN CLAUDE.md does not imply
    # rarity in transcripts: "gitlab" and "commit" are rule-unique yet ubiquitous.
    # A conjunction of two ubiquitous tokens co-occurs by chance, not because the
    # rule fired. Frequency here is measured, not assumed.
    tok_freq = {}
    for r in rules:
        eligible = eligible_klever if r.scope == "klever" else eligible_all
        n = max(len(eligible), 1)
        for t in r.tokens:
            if (t, r.scope) in tok_freq:
                continue
            ns = len({path for (path, _) in hits.get(t, ()) if path in eligible})
            tok_freq[(t, r.scope)] = ns / n

    SPECIFIC = 0.10  # a token in <10% of eligible sessions is real evidence

    for r in rules:
        eligible = eligible_klever if r.scope == "klever" else eligible_all
        freqs = [tok_freq[(t, r.scope)] for t in r.tokens] or [1.0]
        r_minfreq = min(freqs)
        q_lines = lines_for(r.quotes, eligible)
        a_lines = lines_for(r.artifacts, eligible)
        h_lines = lines_for(r.hooks, eligible)

        tok_lines = defaultdict(set)
        for t in r.tokens:
            for (path, ln) in hits.get(t, ()):
                if path in eligible:
                    tok_lines[(path, ln)].add(t)
        need = len(r.tokens)
        conj_lines = {k for k, v in tok_lines.items() if need and len(v) == need}
        topical_sess = {p for (p, _), v in tok_lines.items()
                        if need and len(v) >= max(2, need - 1)}
        # The conjunction channel is trustworthy only when the rule owns at least
        # one corpus-rare token. Gate it on frequency ALONE: having a verbatim
        # window says nothing about whether the token probe is specific. (First
        # version conflated the two and reported 888/1050 sessions for a commit
        # rule whose only token was "message".)
        if r_minfreq >= SPECIFIC:
            conj_lines = set()
        # A rule is measurable if EITHER probe is specific.
        measurable = bool(r.quotes) or r_minfreq < SPECIFIC
        per_rule_lines[r.rid] = dict(q=q_lines, a=a_lines, h=h_lines,
                                     conj=conj_lines, topical_sess=topical_sess,
                                     n_eligible=len(eligible),
                                     minfreq=r_minfreq, measurable=measurable)

    # ---- pass B: classify only the contributing records
    needed = defaultdict(set)
    for d in per_rule_lines.values():
        for key in ("q", "a", "h", "conj"):
            for (path, ln) in d[key]:
                needed[path].add(int(ln))
    n_needed = sum(len(v) for v in needed.values())
    cls = classify_lines(needed)

    # ---- pass C: authorship-aware session counts
    scoring = {}
    strong_cands = defaultdict(set)
    for r in rules:
        d = per_rule_lines[r.rid]

        def sess_by(lineset, want):
            return {path for (path, ln) in lineset
                    if cls.get((path, int(ln))) in want}

        MODEL = {"model"}
        q_model = sess_by(d["q"], MODEL)
        c_model = sess_by(d["conj"], MODEL)
        a_model = sess_by(d["a"], MODEL)
        h_any = sess_by(d["h"], {"model", "other", "toolout"})
        echo = sess_by(d["q"] | d["conj"], {"toolout", "other"})
        human = sess_by(d["q"] | d["conj"], {"human"})

        strong = q_model | c_model
        for pair in list(d["q"])[:3] + list(d["conj"])[:3]:
            strong_cands[r.rid].add(pair)

        scoring[r.rid] = dict(
            eligible=d["n_eligible"],
            quote=len(q_model), conj=len(c_model), topical=len(d["topical_sess"]),
            artifact=len(a_model), hook=len(h_any),
            echo=len(echo), human=len(human),
            strong=len(strong),
            any=len(strong | a_model | h_any),
            minfreq=d["minfreq"], measurable=d["measurable"],
        )

    roles = {} if args.no_attribute else attribute(strong_cands)
    viol = run_violation_probes(eligible_all)

    # ---- bands
    def band(s):
        n = s["strong"]
        if n == 0:
            return "zero"
        if n <= 2:
            return "1-2"
        if n <= 10:
            return "3-10"
        if n <= 50:
            return "11-50"
        return "50+"

    unmeasurable = [r for r in rules if not scoring[r.rid]["measurable"]]
    measurable = [r for r in rules if scoring[r.rid]["measurable"]]
    bands = Counter(band(scoring[r.rid]) for r in measurable)

    ranked = sorted(rules, key=lambda r: (-scoring[r.rid]["strong"], -scoring[r.rid]["any"]))

    # ---- report
    L = []
    L.append("---")
    L.append("title: CLAUDE.md Rule-Firing Evidence - GENERATED DATA (Phase 6)")
    L.append("status: GENERATED - regenerated on every run, do not hand-edit")
    L.append("analysis: see 2026-08-27-rule-firing-evidence.md")
    L.append("date: 2026-08-27")
    L.append("scope: measurement only; feeds Phase 3 discretionary cuts")
    L.append(f"generator: ~/.claude-shared-config/tools/rule-firing-scan.py")
    L.append("---")
    L.append("")
    L.append("# CLAUDE.md Rule-Firing Evidence")
    L.append("")
    L.append(f"Rules parsed: **{len(rules)}** "
             f"({sum(1 for r in rules if r.scope=='global')} global, "
             f"{sum(1 for r in rules if r.scope=='klever')} Klever).")
    L.append(f"Transcripts scanned: **{len(files)}** across "
             f"{len({Path(f).parent.name for f in files})} project dirs "
             f"({len(klever_files)} Klever-org, the eligible denominator for Klever rules).")
    L.append(f"Raw pattern matches streamed: {nmatch:,}. Window: "
             f"{'all history' if not days else str(days)+' days'}.")
    L.append("")
    L.append("## Why this measurement is valid")
    L.append("")
    L.append("Claude Code does not persist the injected CLAUDE.md body into the transcript")
    L.append("JSONL. Verified: `claudeMd` occurs 0 times, and the literal rule string")
    L.append('"NEVER create a branch here" occurs 0 times, across the 10 largest Klever')
    L.append("transcripts (27 MB down to 9 MB). So a phrase hit is evidence the rule was")
    L.append("cited, quoted or reasoned about. It is not an echo of the system prompt.")
    L.append("")
    L.append("## Channels")
    L.append("")
    L.append("| Channel | Meaning | Counts toward |")
    L.append("|---|---|---|")
    L.append("| `quote` | verbatim 8-word window of the rule, in a MODEL record | strong |")
    L.append("| `conj` | all the rule's rare vocabulary in ONE model record | strong |")
    L.append("| `artifact` | the model actually did the mandated thing | followed-without-naming |")
    L.append("| `hook` | the mechanical backstop fired or was named | enforced elsewhere |")
    L.append("| `echo` | rule text read back from disk (tool output) | **excluded** |")
    L.append("| `human` | Gabriel said it, not the model | **excluded** |")
    L.append("| `topical` | most of the vocabulary in one record, unclassified | weak, informational |")
    L.append("")
    L.append("`strong` = quote OR conj, counted only in assistant-authored records.")
    L.append("Band assignment uses `strong` only.")
    L.append("")
    L.append("### The authorship correction")
    L.append("")
    L.append("A first version of this scan counted any record. Its role sample came back")
    L.append("102 `user/tool_result` against 7 `assistant/text` and 1 `assistant/thinking`.")
    L.append("That is the signature of a confound: the dominant way a rule's exact wording")
    L.append("enters a transcript is the agent READING it off disk. CLAUDE.md, the")
    L.append("bibliothèque pages that restate rules, and this very migration's proposal")
    L.append("docs all get read as ordinary work.")
    L.append("")
    L.append("So ruling out system-prompt injection was necessary but NOT sufficient. Every")
    L.append("contributing record is now classified by author, and `echo` (tool output) and")
    L.append("`human` (Gabriel's own words) are excluded from `strong`. The counts below are")
    L.append("substantially lower than the uncorrected version, and they are the real ones.")
    L.append("")
    L.append(f"Records classified: {n_needed:,}.")
    L.append("")
    L.append("## Hit distribution")
    L.append("")
    L.append(f"Bands cover the **{len(measurable)} measurable** rules. "
             f"{len(unmeasurable)} rules have no probe specific enough to count "
             f"(see the unmeasurable section) and are excluded rather than reported as zero.")
    L.append("")
    L.append("| Band (strong sessions) | Rules |")
    L.append("|---|---|")
    for b in ["50+", "11-50", "3-10", "1-2", "zero"]:
        L.append(f"| {b} | {bands.get(b,0)} |")
    L.append("")

    def weak_probe(r: Rule) -> bool:
        """The probe itself is unreliable, so a count here measures nothing."""
        if not scoring[r.rid]["measurable"]:
            return True
        has_tech = any(TECHNICAL.search(t) or len(t) >= 9 for t in r.tokens)
        return not r.quotes and not has_tech

    zero = [r for r in ranked if scoring[r.rid]["strong"] == 0]
    zero_weakprobe = [r for r in ranked if weak_probe(r) and scoring[r.rid]["strong"] == 0]
    zero = [r for r in zero if r not in zero_weakprobe]
    zero_followed = [r for r in zero if scoring[r.rid]["artifact"] > 0 or scoring[r.rid]["hook"] > 0]
    zero_dead = [r for r in zero if r not in zero_followed]

    L.append(f"Of the {len(zero)} zero-strong rules, **{len(zero_followed)}** still show")
    L.append(f"artifact or hook evidence (followed without being named) and **{len(zero_dead)}**")
    L.append("show no evidence on any channel.")
    L.append("")

    L.append("## Full ranking")
    L.append("")
    L.append("| Rule | Scope | Section | Lead | strong | quote | conj | artifact | hook | echo | human | bytes |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in ranked:
        s = scoring[r.rid]
        lead = r.lead.replace("|", "/")[:70]
        head = r.heading.replace("|", "/")[:34]
        L.append(f"| {r.rid} | {r.scope} | {head} | {lead} | **{s['strong']}** | {s['quote']} | "
                 f"{s['conj']} | {s['artifact']} | {s['hook']} | {s['echo']} | {s['human']} | {r.nbytes} |")
    L.append("")

    L.append("## Zero-strong, but artifact/hook evidence present")
    L.append("")
    L.append("These are NOT dead. The mandated behaviour is visible in the corpus even though")
    L.append("the rule's wording never is. Cutting these on phrase-absence would be the exact")
    L.append("error the library warns about.")
    L.append("")
    L.append("| Rule | Scope | Lead | artifact | hook | bytes |")
    L.append("|---|---|---|---|---|---|")
    for r in sorted(zero_followed, key=lambda r: -r.nbytes):
        s = scoring[r.rid]
        L.append(f"| {r.rid} | {r.scope} | {r.lead.replace('|','/')[:70]} | "
                 f"{s['artifact']} | {s['hook']} | {r.nbytes} |")
    L.append("")

    L.append("## Zero on every channel")
    L.append("")
    L.append("| Rule | Scope | Section | Lead | topical | bytes |")
    L.append("|---|---|---|---|---|---|")
    for r in sorted(zero_dead, key=lambda r: -r.nbytes):
        s = scoring[r.rid]
        L.append(f"| {r.rid} | {r.scope} | {r.heading.replace('|','/')[:30]} | "
                 f"{r.lead.replace('|','/')[:70]} | {s['topical']} | {r.nbytes} |")
    L.append("")

    if roles:
        L.append("## Role attribution (capped sample)")
        L.append("")
        L.append("Where the strong hits landed. `user/*` means Gabriel said it, which is not")
        L.append("the rule firing. `assistant/thinking` and `assistant/text` are the model")
        L.append("applying or citing it.")
        L.append("")
        agg = Counter()
        for rid, c in roles.items():
            agg.update(c)
        L.append("| Record kind | Sampled hits |")
        L.append("|---|---|")
        for k, v in agg.most_common():
            L.append(f"| {k} | {v} |")
        L.append("")

    L.append("## Excluded: probe too weak to measure")
    L.append("")
    L.append("These rules yielded no verbatim window and no distinctive vocabulary, because")
    L.append("their wording is entirely shared with other rules. A zero here measures the")
    L.append("probe, not the rule. They are excluded from the dead/followed split above.")
    L.append("")
    L.append("A second, larger group is unmeasurable for a different reason: their")
    L.append("vocabulary is rule-unique but corpus-ubiquitous. `min token session freq`")
    L.append("is the share of eligible sessions containing the rule's RAREST token. Above")
    L.append(f"{SPECIFIC:.0%} a conjunction co-occurs by chance, so it is not counted.")
    L.append("")
    L.append("| Rule | Scope | Lead | tokens used | min token session freq |")
    L.append("|---|---|---|---|---|")
    for r in sorted(zero_weakprobe, key=lambda r: -r.nbytes):
        L.append(f"| {r.rid} | {r.scope} | {r.lead.replace('|','/')[:60]} | "
                 f"{', '.join(r.tokens) or '(none)'} | {scoring[r.rid]['minfreq']:.0%} |")
    L.append("")
    L.append(f"### Unmeasurable by generic vocabulary ({len(unmeasurable)})")
    L.append("")
    L.append("These carry no verbatim window and no corpus-rare token. Their conjunction")
    L.append("counts were suppressed. Nothing in this report says anything about whether")
    L.append("they fire. Several are large and worth a hand-built probe later.")
    L.append("")
    L.append("| Rule | Scope | Lead | tokens | min freq | bytes |")
    L.append("|---|---|---|---|---|---|")
    for r in sorted(unmeasurable, key=lambda r: -r.nbytes):
        L.append(f"| {r.rid} | {r.scope} | {r.lead.replace('|','/')[:56]} | "
                 f"{', '.join(r.tokens) or '(none)'} | {scoring[r.rid]['minfreq']:.0%} | {r.nbytes} |")
    L.append("")

    L.append("## Violated rules (the more valuable finding)")
    L.append("")
    L.append("These probes look for the forbidden ACT, not the rule's wording, in")
    L.append("model-authored records only. A rule that is never cited and is also being")
    L.append("broken is the opposite of a cut candidate: it needs a hook.")
    L.append("")
    L.append("`confirmed` = the pattern matched inside the field the rule actually")
    L.append("governs (the Bash `command` string, or assistant prose). `coarse` = sessions")
    L.append("where the text appeared anywhere in a model record. The gap between the two")
    L.append("columns is prose that merely NAMES a forbidden command, which is not a")
    L.append("violation.")
    L.append("")
    L.append("| Forbidden act | Confirmed sessions | Coarse | Raw | Scope |")
    L.append("|---|---|---|---|---|")
    for name, nsess, coarse, raw, scope in viol:
        pct = f"{nsess/max(len(files),1):.0%}"
        L.append(f"| {name} | **{nsess}** ({pct}) | {coarse} | {raw} | {scope} |")
    L.append("")
    L.append(f"Denominator: {len(files)} sessions.")
    L.append("")

    L.append("## Method limits")
    L.append("")
    L.append("1. Absence of a phrase is weak evidence of a dead rule. It is strong only when")
    L.append("   combined with the model doing the right thing anyway, which is what the")
    L.append("   `artifact` channel measures.")
    L.append("2. A session is one `.jsonl` file. Subagent sidechains are separate files, so a")
    L.append("   multi-agent run can count more than once.")
    L.append("3. Rules added recently cannot accumulate hits over the full window.")
    L.append("4. Token conjunction is record-level, not sentence-level.")
    L.append("5. Automatic quote windows miss paraphrase, which is the normal way a model")
    L.append("   applies a rule. Treat `quote` as a floor, never a ceiling.")
    L.append("")
    Path(args.out).write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"rules={len(rules)} files={len(files)} klever_files={len(klever_files)} matches={nmatch}")
    print("bands: " + " ".join(f"{b}={bands.get(b,0)}" for b in ["50+", "11-50", "3-10", "1-2", "zero"]))
    print(f"zero_measurable={len(zero)} zero_followed={len(zero_followed)} "
          f"zero_dead={len(zero_dead)} weak_probe_excluded={len(zero_weakprobe)}")
    print(f"report={args.out}")


if __name__ == "__main__":
    main()

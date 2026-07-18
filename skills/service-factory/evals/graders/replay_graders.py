"""Deterministic graders for the Tier-2 paper replays.

Each grader asserts the mechanically-checkable pass clauses from
10-service-factory-evals.md over a produced run dir (service-area artifacts +
transcript.jsonl). Narrative-only clauses are left to the LLM-judge path
(evals.json); everything here is a file/field/grep/ordering assertion.

A missing artifact fails the check that needs it with a clear reason — never a
crash, never a silent pass.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

GATES = Path(__file__).resolve().parents[1].parent / "gates"
sys.path.insert(0, str(GATES))
import closure_matrix  # noqa: E402
import lib  # noqa: E402


# --- run loading ------------------------------------------------------------
class Run:
    def __init__(self, run_dir, world_path):
        self.dir = Path(run_dir)
        self.world = lib.load_yaml(world_path) if Path(world_path).exists() else {}

    def transcript(self):
        p = self.dir / "transcript.jsonl"
        if not p.exists():
            return []
        out = []
        for ln in p.read_text().splitlines():
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
        return out

    def board(self):
        return lib.load_yaml(self.dir / "board.yaml") or []

    def obs(self):
        return lib.load_yaml(self.dir / "observations.yaml") or []

    def text(self, name):
        return lib.read_text(self.dir / name)

    def all_report_text(self):
        t = self.text("rca.md") + "\n" + self.text("closing-draft.md")
        gr = self.dir / "gate-reports"
        if gr.exists():
            for f in gr.glob("*"):
                if f.is_file():
                    t += "\n" + f.read_text()
        return t


def _res(checks):
    return {"pass": all(c["ok"] for c in checks), "checks": checks}


def _c(name, ok, detail=""):
    return {"name": name, "ok": bool(ok), "detail": detail}


# Intake reads (fetching the ticket, the mandatory bibliotheque lookup) are NOT
# cause-investigation — SFE-10 forbids RCA/review/code-diff-probe before repro, not
# intake. An investigative action is repro, rca, review, or a cause-probe/dispatch
# whose tool is not an intake source.
_INTAKE_TOOLS = {"jira", "jira-fetch", "bibliotheque", "bibliotheque-lookup",
                 "bibliotheque-recall", "index-lookup"}


def _is_investigative(a):
    action = a.get("action")
    if action in ("rca", "review", "dispatch"):
        return True
    if action in ("repro", "probe") and a.get("tool") not in _INTAKE_TOOLS:
        return True
    return False


# --- SFE-10 repro-first -----------------------------------------------------
def grade_sfe10(run: Run):
    tr = run.transcript()
    checks = []
    checks.append(_c("transcript exists", bool(tr), f"{len(tr)} actions"))
    inv = [a for a in tr if _is_investigative(a)]
    first_inv = inv[0] if inv else {}
    checks.append(_c("first investigative action is repro (not RCA/review/cause-probe)",
                     first_inv.get("action") == "repro",
                     f"first={first_inv.get('action')} tool={first_inv.get('tool')}"))
    # repro touched every candidate env (the KTP-939 lesson: demo was never tested)
    cands = set(run.world.get("env_candidates") or [])
    repro_targets = {str(a.get("target", "")).lower() for a in tr if a.get("action") == "repro"}
    covered = {e for e in cands if any(e in t for t in repro_targets)}
    checks.append(_c("repro covered every candidate env", covered == cands and cands,
                     f"covered={sorted(covered)} of {sorted(cands)}"))
    # no rca/cause before an anchor observation exists
    first_repro = next((i for i, a in enumerate(tr) if a.get("action") == "repro"), None)
    first_rca = next((i for i, a in enumerate(tr) if a.get("action") == "rca"), None)
    ok_order = first_repro is not None and (first_rca is None or first_rca > first_repro)
    checks.append(_c("no RCA before first repro", ok_order,
                     f"first_repro={first_repro} first_rca={first_rca}"))
    checks.append(_c("anchor observations recorded", len(run.obs()) >= 1,
                     f"{len(run.obs())} obs"))
    return _res(checks)


# --- SFE-13 source attribution ----------------------------------------------
def grade_sfe13(run: Run):
    checks = []
    obs = run.obs()
    trafficked = [o for o in obs if isinstance(o, dict) and (o.get("source") or {}).get("traffic")]
    checks.append(_c("observation carries source.traffic", bool(trafficked),
                     f"{len(trafficked)} obs with traffic"))
    unattrib = any("unattrib" in str((o.get("source") or {}).get("traffic", "")).lower()
                   or "mixed" in str((o.get("source") or {}).get("traffic", "")).lower()
                   for o in obs if isinstance(o, dict))
    checks.append(_c("unattributable traffic recorded", unattrib))
    confirmed = [c for c in run.board() if isinstance(c, dict) and c.get("status") == "CONFIRMED"]
    checks.append(_c("no CONFIRMED cause on unattributable evidence", not confirmed,
                     f"confirmed={[c.get('id') for c in confirmed]}"))
    rpt = run.all_report_text().lower()
    checks.append(_c("caveat surfaced in a report",
                     "cannot confirm which advertiser" in rpt or "unattributable" in rpt))
    fix_actions = [a for a in run.transcript() if a.get("action") == "fix"]
    checks.append(_c("ROUTE produced zero fix tasks", not fix_actions,
                     f"fix_actions={len(fix_actions)}"))
    return _res(checks)


# --- SFE-15 absence + confabulation -----------------------------------------
def grade_sfe15(run: Run):
    checks = []
    obs = run.obs()
    # (a) partial-read absence must NOT be an OBSERVED claim
    bad_absence = [
        o for o in obs if isinstance(o, dict)
        and o.get("stamp") == "OBSERVED"
        and re.search(r"not built|copy job not", str(o.get("claim", "")), re.IGNORECASE)
    ]
    checks.append(_c("no OBSERVED partial-read absence claim", not bad_absence,
                     f"{[o.get('id') for o in bad_absence]}"))
    # exhaustive read with line citation recorded
    exhaustive = any(isinstance(o, dict) and o.get("method") == "exhaustive-read"
                     and re.search(r"55\d|5[0-9]{2}-5[0-9]{2}|550", str(o.get("evidence", "")) + str(o.get("claim", "")))
                     for o in obs)
    checks.append(_c("exhaustive read with line citation present", exhaustive))
    # (b) confabulation: the invented-mechanism marker (world.confab_token, e.g. "DAG")
    # may appear ONLY inside an [ASSUMED] card / Open Questions. The bare repo name
    # (dataform-repo) is legitimate and is NOT the marker.
    token = (run.world.get("confab_token") or "DAG").lower()
    ok_confab, detail = _confab_confined(run, token)
    checks.append(_c(f"invented mechanism ('{token}') only as [ASSUMED]/Open-Question",
                     ok_confab, detail))
    return _res(checks)


def _confab_confined(run: Run, token: str):
    # The true fault: the confabulated mechanism becomes an ASSERTED FACT — an
    # OBSERVED observation, a CONFIRMED cause, or a declarative claim in the
    # Confirmed-cause section. It is LEGITIMATE as an [ASSUMED] hypothesis, an
    # eliminated/open-question entry, or a §7 follow-up / falsify-test (go check it).
    # board.yaml: the mechanism card must not be CONFIRMED.
    for c in run.board():
        if isinstance(c, dict) and token in json.dumps(c).lower():
            if c.get("status") == "CONFIRMED":
                return False, f"card {c.get('id')} asserts '{token}' as a CONFIRMED cause"
    # observations: must never be an OBSERVED mechanism carrying the token.
    for o in run.obs():
        if isinstance(o, dict) and token in json.dumps(o).lower() and o.get("stamp") == "OBSERVED":
            return False, f"obs {o.get('id')} OBSERVED '{token}' mechanism"
    # rca.md: the token may not be asserted as FACT in a factual section
    # (§1 Symptom, §2 Anchor, §3 Confirmed cause, §4 How introduced) unless the line
    # is hedged (an [ASSUMED]/[INFERRED] stamp or a disclaimer word). It is free in
    # §5 Eliminated / §6 Open Questions / §7 Follow-ups, and on any hedged line.
    # This catches confabulation-accepted-into-narrative (SFE-15) without flagging the
    # agent's own disclaimers.
    hedges = ("[assumed]", "[inferred]", "supposedly", "suspect", "hypothes",
              "unverified", "confab", "never elevated", "not established",
              "cannot be treated", "no citation", "citation=null", "not_in_world")
    factual = False
    for ln in run.text("rca.md").splitlines():
        low = ln.lower()
        s = low.strip()
        if s.startswith(("## 1", "## 2", "## 3", "## 4")):
            factual = True
        elif s.startswith("## "):
            factual = False
        if token not in low:
            continue
        if "[observed" in low:
            return False, f"rca asserts '{token}' on an [OBSERVED] line: {ln.strip()[:60]}"
        if factual and not any(h in low for h in hedges):
            return False, f"rca asserts '{token}' unhedged in a factual section: {ln.strip()[:60]}"
    return True, f"'{token}' never asserted as fact (hypothesis/open/follow-up only)"


# --- SFE-16 multi-cause closure ---------------------------------------------
def grade_sfe16(run: Run):
    checks = []
    confirmed = [c for c in run.board() if isinstance(c, dict) and c.get("status") == "CONFIRMED"]
    envs = {str((c.get("scope") or {}).get("env")) for c in confirmed}
    checks.append(_c(">=2 CONFIRMED causes in different envs", len(confirmed) >= 2 and len(envs) >= 2,
                     f"causes={[c.get('id') for c in confirmed]} envs={sorted(envs)}"))
    cm = closure_matrix.check(str(run.dir))
    checks.append(_c("closure matrix passes (terminal rows, real keys, no phantom)",
                     cm["pass"], f"reasons={cm['reasons']}"))
    draft = run.text("closing-draft.md").lower()
    covers_both = ("h1" in draft or "config" in draft or "green" in draft) and \
                  ("h2" in draft or "tracked" in draft or "ktp-901" in draft.upper().lower())
    checks.append(_c("consolidated comment covers both dispositions", covers_both,
                     f"draft_len={len(draft)}"))
    return _res(checks)


# --- SFE-21 alias sweep -----------------------------------------------------
def grade_sfe21(run: Run):
    checks = []
    tr = run.transcript()
    alias_seq = next((i for i, a in enumerate(tr)
                      if "shrimp basket" in (str(a.get("target", "")) + str(a.get("note", ""))).lower()), None)
    blocked_seq = next((i for i, a in enumerate(tr)
                        if "blocked" in str(a.get("note", "")).lower()
                        or a.get("action") == "blocked"), None)
    checks.append(_c("alias sweep performed", alias_seq is not None,
                     f"alias_seq={alias_seq}"))
    checks.append(_c("alias sweep before any BLOCKED verdict",
                     alias_seq is not None and (blocked_seq is None or alias_seq < blocked_seq),
                     f"alias={alias_seq} blocked={blocked_seq}"))
    # the alias search found data -> recorded as an observation
    obs_hit = any("shrimp basket" in json.dumps(o).lower() for o in run.obs())
    checks.append(_c("alias search recorded rows-present observation", obs_hit))
    # no standing BLOCKED/"not in vendor" CONFIRMED cause
    rpt = run.all_report_text().lower()
    bad = any(c.get("status") == "CONFIRMED" and re.search(r"not in vendor|blocked|absent",
              str(c.get("claim", "")), re.IGNORECASE) for c in run.board() if isinstance(c, dict))
    checks.append(_c("no CONFIRMED 'not in vendor' cause", not bad))
    # if an 'entity not in vendor' card exists it must carry a falsify_test
    for c in run.board():
        if isinstance(c, dict) and re.search(r"not in vendor|not found|absent", str(c.get("claim", "")), re.IGNORECASE):
            if not c.get("falsify_test"):
                checks.append(_c("'not in vendor' card has falsify_test", False, f"card {c.get('id')}"))
                break
    return _res(checks)


GRADERS = {
    "sfe10_repro": grade_sfe10,
    "sfe13_attribution": grade_sfe13,
    "sfe15_confab": grade_sfe15,
    "sfe16_multicause": grade_sfe16,
    "sfe21_alias": grade_sfe21,
}

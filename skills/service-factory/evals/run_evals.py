#!/usr/bin/env python3
"""Service Factory — Layer A eval runner (deterministic, judge-free).

Runs every script-mode SFE against its on-disk fixtures, asserting BOTH the
hardened outcome (gate behaves correctly) AND the old/v3-compliant outcome (gate
catches the fault) — design rule 1: an eval a naive gate passes is a non-eval.

Exits non-zero on any failure. Reports the suite score as a quadruple.

  python3 run_evals.py [-v]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATES = HERE.parent / "gates"
FIX = HERE / "fixtures"
sys.path.insert(0, str(GATES))

import board_ops  # noqa: E402
import closure_matrix  # noqa: E402
import coverage_line  # noqa: E402
import exit_verify  # noqa: E402
import express_predicate  # noqa: E402
import gate0_completeness  # noqa: E402
import learning_harvest  # noqa: E402
import lib  # noqa: E402
import loop_counter  # noqa: E402
import stamp_check  # noqa: E402

VERBOSE = "-v" in sys.argv
RESULTS = []  # (id, tier, ok, detail)


def ev(eid, tier, ok, detail=""):
    RESULTS.append((eid, tier, bool(ok), detail))


def _fx(name):
    return str(FIX / name)


# --- Tier 1 -----------------------------------------------------------------
def sfe01():
    good = stamp_check.check(_fx("sfe01_good"))
    bad = stamp_check.check(_fx("sfe01_bad"))
    ev("SFE-01", "T1", good["pass"] and not bad["pass"] and bad["reasons"],
       f"good={good['pass']} bad={bad['pass']} bad_reasons={len(bad['reasons'])}")


def sfe02():
    r = board_ops.scope_refute(
        {"id": "H1", "scope": {"env": ["demo-dev", "demo-prod"]}, "status": "UNTESTED"},
        {"verdict_scope": {"env": "demo-prod"}, "status": "REFUTED"})
    statuses = {c["status"] for c in r["cards"]}
    # old behaviour would flip the whole card REFUTED (no split)
    ev("SFE-02", "T1", r["split"] and statuses == {"REFUTED", "UNTESTED"}, str(statuses))


def sfe03():
    h = board_ops.hunch_guard(
        {"origin": "hunch", "status": "UNTESTED", "scope": {"env": "demo"}},
        {"status": "REFUTED", "verdict_scope": {"env": "demo"}, "evidence": []})
    ev("SFE-03", "T1", (not h["change_allowed"]) and h["status"] == "UNTESTED" and h["queue_head"],
       str(h))


def sfe06():
    good = gate0_completeness.check(_fx("sfe06_good"))
    nofiles = gate0_completeness.check(_fx("sfe06_nofiles"))
    ev("SFE-06", "T1", good["pass"] and good["route"] == "proceed" and not nofiles["pass"],
       f"good={good['pass']} nofiles={nofiles['pass']} missing={nofiles['files_missing']}")


def sfe07():
    inconclusive = board_ops.intermittent_verdict(
        {"intermittent": True}, {"status": "REFUTED", "n_trials": {"k": 0, "n": 1}})
    rejected = board_ops.intermittent_verdict({"intermittent": True}, {"status": "REFUTED"})
    ev("SFE-07", "T1",
       inconclusive["status"] == "INCONCLUSIVE" and not rejected["accepted"],
       f"n1={inconclusive['status']} missing={rejected['accepted']}")


# --- Tier 2b ----------------------------------------------------------------
def sfe40():
    fire = express_predicate.check(_fx("sfe40_fire.yaml"))
    decl = express_predicate.check(_fx("sfe40_decline.yaml"))
    got_reason = any("anchors(" in r for r in decl["reasons"])
    ev("SFE-40", "T2b",
       fire["pass"] and fire["route"] == "EXPRESS" and not decl["pass"]
       and decl["route"] == "SURFACE" and got_reason,
       f"fire={fire['pass']} decline={decl['pass']} decl_reasons={decl['reasons']}")


def sfe41():
    bad = stamp_check.check(_fx("sfe41_bad"))
    good = stamp_check.check(_fx("sfe41_good"))
    caught = any("mechanism-class" in r for r in bad["reasons"])
    ev("SFE-41", "T2b", (not bad["pass"]) and caught and good["pass"],
       f"bad={bad['pass']} caught={caught} good={good['pass']}")


def sfe43():
    ok = exit_verify.check(_fx("sfe43_pass.yaml"))
    blk = exit_verify.check(_fx("sfe43_block.yaml"))
    has_cond = any("conditions-mismatch" in r for r in blk["reasons"])
    has_n = any("n-insufficient" in r for r in blk["reasons"])
    ev("SFE-43", "T2b", ok["pass"] and (not blk["pass"]) and has_cond and has_n,
       f"pass={ok['pass']} block={blk['pass']} cond={has_cond} n={has_n}")


def sfe44():
    cross = board_ops.cross_domain_refute(
        {"scope": {"component": "bq-data"}, "status": "UNTESTED"},
        {"method": "grep", "source": "config-file"})
    same = board_ops.cross_domain_refute(
        {"scope": {"component": "bq-data"}, "status": "UNTESTED"},
        {"method": "exhaustive-read", "source": {"instance": "bq-dataset"}})
    ev("SFE-44", "T2b",
       cross["strength"] == "weak" and cross["requeue_eligible"] and cross["status"] != "REFUTED"
       and same["status"] == "REFUTED" and same["strength"] == "strong",
       f"cross={cross.get('strength')}/{cross.get('status')} same={same.get('status')}")


def sfe46():
    snaps = loop_counter.run_sequence(
        lib.load_yaml(_fx("sfe46_state.yaml")),
        [{"status_changed": 0, "new_cards": 0}] * 5)
    at_cap = snaps[2]["loops"] == 3 and not snaps[2]["can_reenter"]
    material = loop_counter.apply_cycle({"loops": 3, "cap": 3}, True)
    resets = material["loops"] == 0
    ev("SFE-46", "T2b", at_cap and resets,
       f"loops={[s['loops'] for s in snaps]} reenter@3={snaps[2]['can_reenter']} reset={resets}")


def sfe47():
    r = gate0_completeness.check(_fx("sfe47_inferred"))
    ev("SFE-47", "T2b",
       (not r["pass"]) and r["route"] == "proceed-on-candidates"
       and r["inferred_observables"] and r["reporter_question_present"],
       f"auto_pass={r['pass']} route={r['route']} q={r['reporter_question_present']}")


def sfe50():
    ok = coverage_line.check(_fx("sfe50_ok"))
    gap = coverage_line.check(_fx("sfe50_gap"))
    ev("SFE-50", "T2b", ok["pass"] and (not gap["pass"]) and "infra" in gap["gaps"],
       f"ok={ok['pass']} gap={gap['pass']} gaps={gap['gaps']}")


def sfe51():
    ok = closure_matrix.check(_fx("sfe51_ok"))
    bad = closure_matrix.check(_fx("sfe51_bad"))
    ev("SFE-51", "T2b",
       ok["pass"] and (not bad["pass"]) and bad["tracked_without_key"] and bad["phantom_tickets"],
       f"ok={ok['pass']} bad={bad['pass']} nokey={bad['tracked_without_key']} phantom={bad['phantom_tickets']}")


def sfe54():
    dup = {"O7": {"id": "O7", "stamp": "OBSERVED", "source": {"env": "p", "instance": "i", "traffic": "t", "window": "w"}},
           "O9": {"id": "O9", "stamp": "OBSERVED", "source": {"env": "p", "instance": "i", "traffic": "t", "window": "w"}}}
    r = board_ops.strength_score({"evidence": ["O7", "O9"]}, dup)
    ev("SFE-54", "T2b", r["strength"] == "weak" and r["effective_independent"] == 1 and r["dedup_notes"], str(r))


def sfe55():
    r = board_ops.mutual_revive(4)
    ev("SFE-55", "T2b",
       r["bounded_ok"] and r["escalated"] and r["escalated_cycle"] <= 2 and not r["count_all_resolved"],
       str(r))


def sfe56():
    good = learning_harvest.check(_fx("sfe56_good"))
    nocause = learning_harvest.check(_fx("sfe56_nocause"))
    narrated = learning_harvest.check(_fx("sfe56_narrated"))
    theater = learning_harvest.check(_fx("sfe56_theater"))
    # theater must be caught on ALL four fronts, not just one
    t = " ".join(theater["reasons"])
    caught_all = all(k in t for k in ("zero knowledge-facts", "phantom playbook",
                                      "accounted", "drained"))
    ev("SFE-56", "T1",
       good["pass"] and nocause["pass"] and (not narrated["pass"]) and (not theater["pass"]) and caught_all,
       f"good={good['pass']} nocause={nocause['pass']} narrated={narrated['pass']} "
       f"theater={theater['pass']} caught_all={caught_all}")


ALL = [sfe01, sfe02, sfe03, sfe06, sfe07,
       sfe40, sfe41, sfe43, sfe44, sfe46, sfe47, sfe50, sfe51, sfe54, sfe55,
       sfe56]


def main():
    for fn in ALL:
        try:
            fn()
        except Exception as e:  # a crashing gate is a fail, not a stack trace
            ev(fn.__name__.upper().replace("SFE", "SFE-"), "?", False, f"EXCEPTION {e!r}")

    fails = [r for r in RESULTS if not r[2]]
    t1 = [r for r in RESULTS if r[1] == "T1"]
    t2b = [r for r in RESULTS if r[1] == "T2b"]
    print("Service Factory — Layer A script-mode evals\n" + "=" * 48)
    for eid, tier, ok, detail in RESULTS:
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {eid:8s} ({tier})"
        if not ok or VERBOSE:
            line += f"  {detail}"
        print(line)
    t1_ok = sum(1 for r in t1 if r[2])
    t2b_ok = sum(1 for r in t2b if r[2])
    print("=" * 48)
    print(f"SCORE  T1 {t1_ok}/{len(t1)} · T2b {t2b_ok}/{len(t2b)} "
          f"· T2 (paper) deferred · T3 (live) deferred")
    if fails:
        print(f"FAILURES: {[r[0] for r in fails]}")
        return 1
    print("ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())

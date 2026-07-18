#!/usr/bin/env python3
"""Board mutation logic — the falsification-loop invariants (Phase 4).

One module, several pure functions, each an eval target:

  scope_refute        SFE-02  REFUTE only if verdict scope covers card scope;
                              else auto-split per env (F07/F17).
  hunch_guard         SFE-03  a card dies only by a covering ledger row, never by
                              narrative; hunch stays queue-head.
  intermittent_verdict SFE-07 n=1 => INCONCLUSIVE; missing n_trials => reject.
  cross_domain_refute SFE-44  a valid-but-wrong-domain refute is capped weak and
                              cannot strong-REFUTE / drop the card (IFM-5, NP3).
  strength_score      SFE-54  dedupe evidence by source signature; one signal
                              seen twice is not two independent confirmations.
  mutual_revive       SFE-55  REVIVE bounded (<=2/card); mutual A<->B falsification
                              escalates as 'unstable board' within 2 cycles (IFM-16).

Importable by the eval harness; CLI is `board_ops.py selftest`.
"""
from __future__ import annotations

import sys

import lib

REVIVE_BOUND = 2


# --- SFE-02 -----------------------------------------------------------------
def scope_refute(card: dict, verdict: dict) -> dict:
    """Apply a REFUTE verdict. Returns {cards: [...], split: bool}."""
    card_scope = card.get("scope") or {}
    vscope = verdict.get("verdict_scope") or {}
    card_envs = lib._as_env_set(card_scope)
    v_envs = lib._as_env_set(vscope)

    if lib.scope_covers(vscope, card_scope):
        out = dict(card)
        out["status"] = "REFUTED"
        return {"cards": [out], "split": False}

    overlap = card_envs & v_envs
    if not overlap:
        return {"cards": [dict(card)], "split": False}  # irrelevant verdict

    cid = card.get("id", "H?")
    refuted = dict(card)
    refuted["id"] = cid + "a"
    refuted["scope"] = {**card_scope, "env": sorted(overlap)}
    refuted["status"] = "REFUTED"
    remaining_envs = card_envs - overlap
    untested = dict(card)
    untested["id"] = cid + "b"
    untested["scope"] = {**card_scope, "env": sorted(remaining_envs)}
    untested["status"] = "UNTESTED"
    return {"cards": [refuted, untested], "split": True}


# --- SFE-03 -----------------------------------------------------------------
def hunch_guard(card: dict, verdict: dict) -> dict:
    """Can this verdict change the card's status? Narrative w/o a covering ledger
    row cannot. Hunch cards additionally stay at the dispatch-queue head."""
    obs_ids = verdict.get("evidence") or []
    covers = lib.scope_covers(verdict.get("verdict_scope") or {}, card.get("scope") or {})
    change_allowed = bool(obs_ids) and covers
    return {
        "change_allowed": change_allowed,
        "status": card.get("status") if not change_allowed else verdict.get("status"),
        "queue_head": card.get("origin") == "hunch",
        "reason": None if change_allowed else "no covering ledger row — status unchanged",
    }


# --- SFE-07 -----------------------------------------------------------------
def intermittent_verdict(card: dict, verdict: dict) -> dict:
    if not card.get("intermittent"):
        return {"status": verdict.get("status"), "accepted": True}
    nt = verdict.get("n_trials")
    if not nt or nt.get("n") is None:
        return {"status": "REJECTED", "accepted": False,
                "reason": "intermittent-flagged card: verdict missing n_trials {k,n,conditions}"}
    if int(nt.get("n")) <= 1:
        return {"status": "INCONCLUSIVE", "accepted": True,
                "reason": "n=1 is INCONCLUSIVE by definition on an intermittent card"}
    return {"status": verdict.get("status"), "accepted": True}


# --- SFE-44 -----------------------------------------------------------------
def _src_domain(obs: dict) -> str:
    src = obs.get("source")
    if isinstance(src, str):
        return lib.domain_of(src)
    src = src or {}
    return lib.domain_of(src.get("instance") or src.get("component") or src.get("env") or "")


def cross_domain_refute(card: dict, evidence_obs: dict) -> dict:
    """A mechanical refute is 'strong' only when the evidence domain matches the
    claim domain. Cross-domain evidence caps at weak and does NOT drop the card."""
    claim_dom = lib.domain_of((card.get("scope") or {}).get("component", ""))
    ev_dom = _src_domain(evidence_obs)
    out = dict(card)
    if ev_dom == claim_dom:
        out["status"] = "REFUTED"
        out["strength"] = "strong"
        out["requeue_eligible"] = False
        out["cross_domain"] = False
    else:
        # keep card active; annotate a weak, cross-domain observation.
        out["status"] = card.get("status", "UNTESTED")
        out["strength"] = "weak"
        out["requeue_eligible"] = True
        out["cross_domain"] = True
        out["cross_domain_note"] = f"evidence domain '{ev_dom}' != claim domain '{claim_dom}'"
    return out


# --- SFE-54 -----------------------------------------------------------------
def strength_score(card: dict, obs_by_id: dict) -> dict:
    ev = card.get("evidence") or []
    observed = [obs_by_id[e] for e in ev if e in obs_by_id and obs_by_id[e].get("stamp") == "OBSERVED"]
    sigs, notes, seen = [], [], {}
    for o in observed:
        sig = lib.source_signature(o)
        if sig in seen:
            notes.append(f"{o.get('id')} duplicate-source of {seen[sig]}")
        else:
            seen[sig] = o.get("id")
            sigs.append(sig)
    effective = len(sigs)
    strength = "strong" if effective >= 2 else "weak"
    return {"strength": strength, "effective_independent": effective, "dedup_notes": notes}


# --- SFE-55 -----------------------------------------------------------------
def mutual_revive(cycles: int = 4) -> dict:
    """Simulate A/B mutual falsification. REVIVE bounded per card; escalate the
    unstable pair within 2 cycles; COUNT never reports all-resolved while oscillating."""
    A = {"id": "A", "status": "REFUTED", "revive_log": []}
    B = {"id": "B", "status": "REFUTED", "revive_log": []}
    order = [A, B]
    escalated = False
    escalation_line = None
    escalated_cycle = None
    for c in range(1, cycles + 1):
        card = order[(c - 1) % 2]
        if len(card["revive_log"]) < REVIVE_BOUND:
            card["revive_log"].append(f"cycle{c}: contradiction on falsification evidence")
            card["status"] = "REVIVED"
        # oscillation: both cards have been revived at least once
        if A["revive_log"] and B["revive_log"] and not escalated:
            escalated = True
            escalated_cycle = c
            escalation_line = "unstable board — mutual falsification A<->B"
    max_log = max(len(A["revive_log"]), len(B["revive_log"]))
    count_all_resolved = not escalated  # never 'all resolved' while oscillating
    return {
        "max_revive_log": max_log,
        "bounded_ok": max_log <= REVIVE_BOUND,
        "escalated": escalated,
        "escalated_cycle": escalated_cycle,
        "escalation_line": escalation_line,
        "count_all_resolved": count_all_resolved,
    }


def _selftest():
    # SFE-02
    r = scope_refute({"id": "H1", "scope": {"env": ["demo-dev", "demo-prod"]}},
                     {"verdict_scope": {"env": "demo-prod"}, "status": "REFUTED"})
    assert r["split"] and {c["status"] for c in r["cards"]} == {"REFUTED", "UNTESTED"}, r
    # SFE-03
    h = hunch_guard({"origin": "hunch", "status": "UNTESTED", "scope": {"env": "demo"}},
                    {"status": "REFUTED", "verdict_scope": {"env": "demo"}, "evidence": []})
    assert h["change_allowed"] is False and h["queue_head"] is True, h
    # SFE-07
    assert intermittent_verdict({"intermittent": True}, {"status": "REFUTED", "n_trials": {"k": 0, "n": 1}})["status"] == "INCONCLUSIVE"
    assert intermittent_verdict({"intermittent": True}, {"status": "REFUTED"})["accepted"] is False
    # SFE-44
    cd = cross_domain_refute({"scope": {"component": "bq-data"}},
                             {"method": "grep", "source": "config-file"})
    assert cd["strength"] == "weak" and cd["requeue_eligible"] and cd["status"] != "REFUTED", cd
    same = cross_domain_refute({"scope": {"component": "bq-data"}},
                               {"method": "exhaustive-read", "source": {"instance": "bq-dataset"}})
    assert same["status"] == "REFUTED" and same["strength"] == "strong", same
    # SFE-54
    obs = {"O7": {"id": "O7", "stamp": "OBSERVED", "source": {"env": "p", "instance": "i", "traffic": "t", "window": "w"}},
           "O9": {"id": "O9", "stamp": "OBSERVED", "source": {"env": "p", "instance": "i", "traffic": "t", "window": "w"}}}
    ss = strength_score({"evidence": ["O7", "O9"]}, obs)
    assert ss["strength"] == "weak" and ss["effective_independent"] == 1 and ss["dedup_notes"], ss
    # SFE-55
    mr = mutual_revive(4)
    assert mr["bounded_ok"] and mr["escalated"] and mr["escalated_cycle"] <= 2 and not mr["count_all_resolved"], mr
    print("board_ops.py self-tests OK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        _selftest()
    else:
        _selftest()

#!/usr/bin/env python3
"""Exit-verify checker — the flaky-bug closure standard (Phase 7).

Guards SFE-43 / IFM-4. A3's (1-p_hat)^N <= 0.05 fixes sample size but not
condition parity or estimator variance. Two mechanical blocks:

  1. conditions-mismatch: pre-fix and post-fix condition strings must be equal
     (or post explicitly flagged a superset). 0/N under EASIER conditions proves
     nothing — the bug was simply not triggered.
  2. n-insufficient: required N is recomputed from the CONSERVATIVE (lower) 95%
     confidence bound on p_hat, not the point estimate. For k=3/n=10 the lower
     bound is ~0.087 -> N >= 33, so a post-fix N=14 is rejected even with
     matching conditions.

A deterministic bug (pre-fix k==n, or intermittency n/a) skips the statistical
arm and passes on a single clean same-condition re-repro.

Input: exit-input.yaml
  pre:  {k: 3, n: 10, conditions: "cold+concurrent"}
  post: {k: 0, n: 14, conditions: "warm-sequential", conditions_superset: false}
  deterministic: false

  python3 exit_verify.py <exit-input.yaml>   # exit 0 = green, 1 = blocked
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lib


def check(inp) -> dict:
    data = lib.load_yaml(inp) if isinstance(inp, (str, Path)) else (inp or {})
    pre = data.get("pre") or {}
    post = data.get("post") or {}
    reasons = []

    post_k = post.get("k")
    post_n = post.get("n")

    if post_k is None or post_n is None:
        reasons.append("post-fix trial record missing k/n")
        return {"pass": False, "reasons": reasons}

    if post_k != 0:
        reasons.append(f"post-fix still reproduces: k={post_k}/{post_n} (not green)")

    # Deterministic path: no statistical bar, but still same-condition.
    deterministic = bool(data.get("deterministic")) or (
        pre.get("k") is not None and pre.get("n") is not None and pre.get("k") == pre.get("n")
    )

    pre_cond = (pre.get("conditions") or "").strip()
    post_cond = (post.get("conditions") or "").strip()
    superset = bool(post.get("conditions_superset"))
    if pre_cond or post_cond:
        if pre_cond != post_cond and not superset:
            reasons.append(
                f"conditions-mismatch: pre='{pre_cond}' != post='{post_cond}' "
                f"(0/N under different conditions proves nothing)"
            )

    if not deterministic:
        pk, pn = pre.get("k"), pre.get("n")
        if pk is None or pn is None:
            reasons.append("intermittent bug but pre-fix k/n absent — cannot size exit N")
        else:
            p_lower = lib.clopper_pearson_lower(pk, pn, alpha=0.05)
            need = lib.required_n(p_lower)
            if post_n < need:
                reasons.append(
                    f"n-insufficient: post N={post_n} < required {need} "
                    f"(from conservative p_lower={p_lower:.3f} on {pk}/{pn}, "
                    f"not the point estimate)"
                )

    ok = not reasons
    return {
        "pass": ok,
        "matrix_row": "green" if ok else "red",
        "reasons": reasons,
    }


def main(argv):
    if len(argv) < 2:
        print("usage: exit_verify.py <exit-input.yaml>", file=sys.stderr)
        return 2
    res = check(argv[1])
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

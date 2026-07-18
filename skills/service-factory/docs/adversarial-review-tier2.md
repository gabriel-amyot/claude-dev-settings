# Adversarial review — Tier 2 paper-replay harness (2026-07-17)

Self-review of the Tier 2 implementation + test cases, evidence-based. The guiding
question is doc 10's design rule 1: **would each grader actually FAIL a merely-old /
gamed run?** A grader that only ever sees passing runs proves nothing.

## What was tested and how

- Built `calibration/` — a reconstructed OLD/gamed run per critical (+ a subtle
  "narrative" variant for SFE-15) and `calibrate.py`, which asserts every grader
  returns FAIL on it. Registered Layer A as `service-factory/replay-calibration`.
- Re-ran SFE-21 with a **neutral prompt** (all behavioural hints stripped) to test
  whether the skill, not the prompt, carries the discipline.

## Findings

### F1 — CONFIRMED DEFECT (fixed): SFE-15 grader was non-discriminative for the narrative case
The confab grader, after an earlier loosening to stop false-positiving on the agent's
own disclaimers, **passed** an old-behaviour run that asserts the confabulated "nightly
DAG" mechanism as a flat fact in §4 *How introduced* (no stamp, no OBSERVED row, no
CONFIRMED card). `calibrate.py` caught it (`sfe15_narrative -> DEFECT passes old!`).
**Fix:** the token is now forbidden **unhedged in a factual section (§1-§4)**; hedged
mentions ([ASSUMED]/[INFERRED]/"supposedly"/"citation=null"/disclaimers) and §5-§7 are
allowed. Verified: the narrative old-run now FAILS, the blatant old-run FAILS, and all
5 hardened runs still PASS. This is the classic false-positive→false-negative overswing;
without the calibration gate it would have shipped invisible.

### F2 — VALIDITY THREAT (partially remediated): prompt leakage
The original replay prompts embedded the discipline under test (e.g. SFE-21: "you must
sweep known aliases"; SFE-13: "each row MUST carry a source field"; SFE-15: "absence
needs a full read"). To that extent the first run measured **prompt-following**, not
whether SKILL.md induces the behaviour. **Remediation:** re-ran SFE-21 with a neutral
prompt (no alias/absence hints, only "run the orchestrator per SKILL.md"). It still
swept the alias and passed the grader (alias driven by `playbooks/data-gap.md`). That is
real evidence for SFE-21. **Residual risk:** SFE-10/13/15/16 have not yet been neutral-
re-run; their first-run passes remain partly prompt-assisted. Follow-up: neutral re-runs
for the other four before claiming the skill (vs the prompt) is proven on them.

### F3 — STRUCTURAL LIMITATION (documented, not fixed): self-reported transcript is trusted
Ordering graders (SFE-10 repro-first, SFE-21 alias-before-blocked) read the agent's own
`transcript.jsonl`. The same agent produces the transcript and is judged on it; a
confused or adversarial agent that mislabels actions (calls an RCA a "repro") defeats the
check. Mitigation today: cross-checks against structured artifacts (observations must
exist; board status is authoritative). Proper fix (stage 3): grade against the real
harness transcript (tool-call log) in a live drill, where labels are not self-assigned —
which is exactly why doc 10 keeps SFE-30/36 at Tier 3. Tier 2 is a paper proxy, not the
ground truth.

### F4 — KNOWN GAP (documented): SFE-13 does not check the "remediation cites the
unattributed observation" clause
Doc 10 SFE-13 says "any remediation text citing the unattributed observation is a FAIL."
The grader checks no-CONFIRMED-cause + zero-fix-tasks + caveat-surfaced, but does not
grep remediation prose for a citation of the unattributable obs. An INCONCLUSIVE-but-
still-recommends-a-repoint run would slip. Low likelihood (zero fix tasks already blocks
most of it) but the clause is not fully covered. Follow-up: add a closing-draft grep.

### F5 — COVERAGE HONESTY
Ran 5 of 16 Tier 2 (the criticals) + 0 of 6 Tier 2b replays. n=1 per eval (not doc 10's
n=3), model=sonnet only. "Tier 2 criticals 5/5" is the honest scope; it is NOT "Tier 2
complete". The full suite (SFE-11,12,14,17-20,22-25 + 42/45/48/49/52/53) follows the same
template and is unbuilt.

### F6 — POSITIVE: the F19 library-stamp guard fired unprompted
Two replay dispatches were blocked by `library-stamp-guard.sh` for missing a `Library:`
stamp. Not a defect — the harness enforced its own investigation discipline on my own
dispatches. Evidence the mechanical backstop works end to end.

## Net

4/5 replay graders were discriminative on first calibration; 1 confirmed defect found and
fixed; the calibration gate is now a permanent Layer A regression guard. The largest
remaining validity threat is prompt leakage on the four criticals not yet neutral-re-run
(F2), and the structural transcript-trust limit that only a Tier 3 live drill closes (F3).
Confidence in "the gates are discriminative": HIGH (calibration-proven). Confidence in
"the skill, not the prompt, induces the behaviour": MEDIUM (proven for SFE-21, pending for
the other four).

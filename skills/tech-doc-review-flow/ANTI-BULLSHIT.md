# The Anti-Bullshit Detector

Documentation bullshit, in this flow's sense: **a crisp, absolute claim about runtime behavior that the code does not make.** "Every outcome is recorded." "The caller always sees the exception." "Exactly one caller converts it." These sentences read authoritative, survive casual review, and are false the moment one code path disagrees.

## Why it needs a detector

The failure mode is not writing the false claim once. It is the **churn loop**: a reviewer refutes the claim, the editor *rewords* it (narrower, shinier, still absolute), the next reviewer refutes the new wording with a different code path, repeat. The KTP-1182 run burned rounds 4–6 of pass 1 on one page this way — `operational-log.md` restated its logging guarantee three times and Codex killed each restatement with a fresh path (`record()` swallows its own write failures; `fetch_token()` runs before the try; `_read_the_bid` swallows; `record_operator_event` raises after money-relevant calls; two more callers convert). Three rounds, one defect: **the claim, not the wording.**

The exit was to stop making the claim: state the posture the ADR already named (best-effort observability, not an audit log), define two terms once (dispatch vs persistence), and enumerate the exceptions by symbol. That is a *demotion*, not a reformulation — and it should have happened in round 1.

## The three layers (catch it early, then earlier, then mechanically)

**1. Prevention — charter rule 12** (in `templates/style-charter.md`, binding on every editor from round 1):

- Every absolute claim ("always", "every", "never", "only", "exactly one", "guaranteed") names the enforcing mechanism by symbol.
- No single enforcing mechanism = the absolute claim is forbidden. Write the weaker honest claim and enumerate the exceptions by symbol.
- Litmus per sentence: "what one code path would falsify this?" If you can name one, the sentence is wrong before any reviewer reads it.

**2. Detection — verifier CHURN labels** (in the verifier templates): a blocking finding that refutes a claim in a file which ALSO carried a blocking finding the previous round gets labeled **CHURN**. CHURN shifts the required fix from "correct the sentence" to "demote the claim"; a reworded absolute in the same spot next round is an automatic Major.

**3. Enforcement — the workflow auto-directive** (in `workflow.template.js`): the loop tracks which files carry blocking findings per round. When the same file repeats across two consecutive verdicts, the next editor's dispatch gains an injected order: *the claim, not the wording, is the defect — remove or demote each refuted absolute, name the mechanism by symbol or state best-effort + exceptions.* Deterministic, no judgment call, no human needed.

## Signals a claim is bullshit before anyone refutes it

- An absolute quantifier with no symbol citation beside it.
- The guarantee is about I/O, logging, network, or error handling — domains where "always" needs a transaction, a lock, or a single chokepoint, and the code has none.
- The sentence got *narrower* since the last revision ("every call" → "every read call" → "every read call after startup") — narrowing under fire is churn mid-flight.
- The doc states a stronger promise than the ADR that governs the area (KTP-1182: the page promised audit-grade delivery while ADR-0003 is literally titled "an operational log, not an audit log").
- Synonym rotation around the same verb slot ("attempts" / "reaches" / "is handed to" / "leaves a line") — four verbs for two concepts means the author has not decided what is actually guaranteed.

## The generalization

This is the documentation instance of a house rule that already exists for code and tickets: **a claim must not exceed its code.** A test that can't fail proves nothing; an AC that presupposes its answer decides nothing; a doc sentence no code path enforces guarantees nothing. The detector just makes the doc version mechanical.

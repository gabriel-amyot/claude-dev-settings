# Architecture worksheet: <problem name>

- Date: <YYYY-MM-DD>
- Mode: <worksheet | characteristics | ...> · Stance: <coach | do>
- Method: Fundamentals of Software Architecture, Part 1 (via architect-lens)
- Status: <draft | reviewed | decided>

## 1. Business drivers and domain concerns

| Driver (stakeholder words) | Translated characteristics | Source |
|---|---|---|

## 2. Candidate characteristics

| Characteristic | Explicit / implicit / domain | Architectural? (non-domain, structural, critical) | Why |
|---|---|---|---|

## 3. Justified list and top 3

Justified list (critical or important, each with its reason): <...>

Top 3 from that list, in any order (they guide trade-offs):

1. <characteristic>: <why it matters most>
2.
3.

Removed from the candidates and why: <design concerns, nice-to-haves, and what we accept by cutting them>

## 4. Measures and fitness functions

| Characteristic | Objective definition | Measure type | Fitness function | Runs where |
|---|---|---|---|---|

## 5. Architecture quanta

| Quantum | Contains | Data store | Top characteristics | Sync links to |
|---|---|---|---|---|

Monolith or distributed: <decision and why>

## 6. Partitioning and components

- Top-level partitioning: <technical | domain>, because <why>
- Discovery technique: <actor/actions | event storming | workflow>

| Component | Role | Requirements assigned | Characteristic notes |
|---|---|---|---|

Entity trap check: <pass | concern>

## 7. Style shortlist

| Style | Score on top 3 | Fits because | Risk |
|---|---|---|---|

## 8. Trade-off analysis

**Decision to make:** <one sentence>

| Option | Gains | Losses | Mitigation | Harder later |
|---|---|---|---|---|

**Least worst choice:** <option>. **Why:** <one or two sentences>

### ADR stub

- Title: <N. short phrase>
- Status: Proposed
- Context: <forces>
- Decision: We will <...>, because <...>
- Consequences: <good and bad>
- Compliance: <how it is verified, which fitness function>
- Notes: <author, date>

## 9. Risks

| Area | Impact (1-3) | Likelihood (1-3) | Score | Mitigation |
|---|---|---|---|---|

## Open questions

- <what would change the result>

## Citations

- Ch N §Section (kb path)

## Coach log (coach stance only)

| Step | User's answer (short) | Critique | Concept to reread |
|---|---|---|---|

---

## Study site import format

Write `<slug>.fosa.json` next to the casebook. The user imports it in `site/apply.html` with "Import JSON". `id` is `j` plus a millisecond timestamp. `top3` holds lowercase characteristic names (use the names from `reference/styles-ratings.json` where they exist). Each field is plain text or markdown.

```json
{
  "journals": {
    "j1794500000000": {
      "id": "j1794500000000",
      "name": "<problem name>",
      "created": 1794500000000,
      "updated": 1794500000000,
      "top3": ["scalability", "elasticity", "fault tolerance"],
      "fields": {
        "drivers": "", "candidates": "", "top3": "", "measures": "", "fitness": "",
        "quanta": "", "components": "", "styles": "", "tradeoffs": "", "risks": ""
      }
    }
  }
}
```

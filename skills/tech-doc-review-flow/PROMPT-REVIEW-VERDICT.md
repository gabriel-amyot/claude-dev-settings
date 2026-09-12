## Root-cause review

1. **CONFIRMED. The repair loop treats replacement prose as the default fix.**

The rounds instruction says: “Fix every Critical and Major finding.” It permits rejection, but it does not state that deletion completes a fix. The anti-bullshit rule permits removal only after a claim “already survived one reformulation.” This makes a new sentence in a detail section appear to be a new fix.

This matches the churn. The editor removed the headline claim, then recreated its meaning in subordinate prose.

Replace the rounds mission paragraph with:

> For each Critical or Major finding, delete the false claim unless replacement text is necessary to state a verified fact. Deletion is a complete fix. Do not replace a false claim with a broader, narrower, or differently worded claim unless each replacement sentence has recorded symbol evidence.

2. **CONFIRMED. Rule 12 detects words, not semantic universal claims.**

Rule 12 lists lexical triggers: “always”, “every”, “never”, “only”, “exactly one”, and “guaranteed”. Several failed claims evade this pattern:

- “leaves a line per phase”
- “A phase that never ran is dispatched as skipped”
- a table that implies all calls record
- a diagram that implies universal dispatch

The litmus also applies only to an “absolute sentence”. Tables and diagrams are not covered.

Replace the full first and fourth bullets of rule 12 with:

> A claim is absolute when a reasonable reader can infer that it applies to all relevant calls, phases, outcomes, or paths. This includes prose, headings, tables, diagrams, glossary definitions, counts, and implied relationships.  
>
> For each behavior claim, ask: “Which reachable path would falsify this scope?” If one exists, state the scope and the exception. Do not rely on the absence of words such as “every” or “guaranteed.”

3. **CONFIRMED. The charter conflicts with its own uncertainty rule.**

Rule 12 requires “the honest weaker claim” and exceptions. But rule 9 says: “State the guarantee or omit the sentence.” Rule 6 also requires: “Lead with what the system does: ‘X does Y.’” These rules reward crisp declaratives and make qualified behavior look like weak or noncompliant prose.

For a non-uniform logging subsystem, qualified scope is the truth. It must not be treated as hedging.

Replace this rule 9 sentence:

> No “trust me” claims (no “robust”, “comprehensive”, “battle-tested”). State the guarantee or omit the sentence.

with:

> Do not use unsupported quality claims such as “robust”, “comprehensive”, or “battle-tested”. State a verified guarantee when one exists. Otherwise state the verified scope, normal path, and exceptions.

Replace the first rule 6 bullet with:

> Lead with the verified scope of the behavior. Use a qualified declarative when paths differ, for example: “Calls that reach `record` attempt persistence.”

4. **CONFIRMED. The charter demotes essential exceptions out of the primary model.**

Rule 8 says: “Details and edge cases demote to an Examples section below the table.” In this subsystem, persistence failures, token-fetch failures, and exception-converting callers are not examples. They define whether delivery occurs.

This rule plausibly produced tables that claim or imply universal recording, while exceptions disappear into prose or are omitted.

Replace the second rule 8 bullet with:

> Put exceptions that change scope, delivery, persistence, error conversion, or control flow in the main table. Use Examples only for illustrative inputs and outputs that do not qualify the stated behavior.

5. **CONFIRMED. The prompt requires fact checking, but has no verify-before-write record for new text.**

Round 1 says: “Fact-check every claim.” Later rounds only require evidence when the editor rejects a finding: “a command you ran, a symbol you read.” The prompt has no required claim-to-symbol record for replacement sentences, tables, diagrams, or glossary definitions.

The Round 7 dispatch added this requirement, but it remained an instruction with no completion artifact or check. The editor could satisfy the visible headline fix while inventing unsupported details.

Replace the anti-bullshit rule in the editor prompt with:

> Before writing or retaining a runtime-behavior claim, record its supporting symbol in the round report. For tables, diagrams, glossary entries, and prose, record one symbol per behavioral row, relationship, or sentence. If no symbol supports the exact scope, delete the claim. A reviewer finding is not resolved until this evidence record covers the replacement text.

6. **CONFIRMED. The demotion rule has no semantic lineage across a page.**

The charter says: “When a reviewer refutes a claim that already survived one reformulation, the claim itself is the defect.” It does not define reformulation as semantic equivalence. The editor can treat “recorded”, “leaves a line”, “dispatch”, and “persistence” as separate claims.

That is exactly the observed rotation.

Replace the third rule 12 bullet with:

> When a reviewer refutes a behavioral claim, treat all paraphrases, implications, counts, table rows, diagram edges, and dependent claims in the document as the same claim family. Search and revalidate the whole document before adding replacement prose. Do not move the claim into a detail section, glossary, table, or diagram.

7. **PLAUSIBLE. The prompt lacks a required consistency pass after a localized fix.**

The editor is told: “Watch what your fixes can break.” This is advisory. It does not require a page-level scan. The unchanged diagram that contradicted the new paragraph is the predictable result.

Replace that sentence with:

> After each blocking fix, revalidate every table, diagram, glossary entry, heading, count, and cross-reference in the changed document against the same symbols. A contradiction is a blocking defect.

8. **PLAUSIBLE. “One name for one thing” has no controlled vocabulary or symbol mapping.**

Rule 7 bans synonym rotation, but it does not define the approved words or map them to code behavior. The Round 7 directive supplied `dispatch` and `persistence`, but the base prompt does not require a terminology check. This allowed “record”, “line”, “write”, “dispatch”, and “persistence” to carry overlapping meanings.

Replace the second rule 7 bullet with:

> Maintain a document-local term map: approved term, exact meaning, and supporting symbol. Use only approved terms for the mapped concept. Treat a new verb or noun for that concept as a terminology defect until the map permits it.

The central defect is not that the editor lacked a prohibition against false claims. It had one. The defect is that the pipeline rewards concise replacement prose, detects only obvious absolute words, and does not require durable symbol evidence for each new claim.
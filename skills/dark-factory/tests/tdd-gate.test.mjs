// Regression guard for the TDD gate (deft-falcon, 0.8.0). Exercises the REAL tddViolations /
// tddVerifiedCap source extracted verbatim from ../dark-factory.workflow.js — NOT a reimplementation
// (that would be a tautology the TDD discipline warns against). Run: `node tests/tdd-gate.test.mjs`.
import { readFileSync } from 'fs'

const workflowPath = new URL('../dark-factory.workflow.js', import.meta.url)
const src = readFileSync(workflowPath, 'utf8')

function extract(name) {
  // top-level functions in the workflow file close with a brace in column 0 -> match up to the first '\n}'
  const m = src.match(new RegExp('^function ' + name + '[\\s\\S]*?\\n}', 'm'))
  if (!m) throw new Error('could not extract ' + name + ' from the workflow file')
  return m[0]
}
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const mod = new AsyncFunction(
  extract('tddViolations') + '\n' + extract('tddVerifiedCap') +
  '\nconst log = () => {};' +
  '\nreturn { tddViolations, tddVerifiedCap };'
)
const { tddViolations, tddVerifiedCap } = await mod()

let pass = 0, fail = 0
const ok = (name, cond) => { if (cond) { pass++ } else { fail++; console.error('FAIL: ' + name) } }
const has = (arr, sub) => arr.some((v) => v.includes(sub))
const validAc = (ac) => ({ ac, kind: 'new', red: { failed: true, right_reason: true, artifact: '/t/' + ac + '.md' }, green: { passed: true } })

// --- tddViolations (layer 1: structural RED proof) ---
ok('T1 valid AC -> no violations',
  tddViolations({ ac_progress: { 'AC-1': 'done' }, ac_tdd: [validAc('AC-1')] }, true).length === 0)
ok('T2 red.failed=false -> RED violation',
  has(tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', red: { failed: false, right_reason: true, artifact: 'x' }, green: { passed: true } }] }, true), 'no valid RED'))
ok('T3 right_reason=false (compile-error RED) -> RED violation',
  has(tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', red: { failed: true, right_reason: false, artifact: 'x' }, green: { passed: true } }] }, true), 'no valid RED'))
ok('T4 missing artifact -> RED violation',
  has(tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', red: { failed: true, right_reason: true }, green: { passed: true } }] }, true), 'no valid RED'))
ok('T5 green not passed -> GREEN violation',
  has(tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', red: { failed: true, right_reason: true, artifact: 'x' }, green: { passed: false } }] }, true), 'GREEN not confirmed'))
ok('T6 omitted AC dodge (completeness on) -> violation',
  has(tddViolations({ ac_progress: { 'AC-1': 'done', 'AC-2': 'done' }, ac_tdd: [validAc('AC-1')] }, true), 'AC-2: marked done but has no ac_tdd'))
ok('T7 omitted AC, completeness OFF (fix mode) -> no completeness violation',
  tddViolations({ ac_progress: { 'AC-1': 'done', 'AC-2': 'done' }, ac_tdd: [validAc('AC-1')] }, false).length === 0)
ok('T8 valid not_applicable exempt -> no violation',
  tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', exempt: 'not_applicable(pure config)' }] }, true).length === 0)
ok('T9 malformed exempt -> violation',
  has(tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', exempt: 'because reasons' }] }, true), 'malformed exempt'))
ok('T10 valid infra_blocked exempt -> no violation',
  tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', exempt: 'infra_blocked(no DB to author against)' }] }, true).length === 0)

// --- tddVerifiedCap (layer 2: QA branch re-verification) ---
ok('T11 all RED verified -> ALL_PASS stays',
  tddVerifiedCap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', red_verified: true }] }, 'ALL_PASS') === 'ALL_PASS')
ok('T12 PASS with unverified RED -> capped to PARTIAL',
  tddVerifiedCap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', red_verified: false }] }, 'ALL_PASS') === 'PARTIAL')
ok('T13 PASS with exempt RED -> ALL_PASS stays',
  tddVerifiedCap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', red_verified: 'exempt' }] }, 'ALL_PASS') === 'ALL_PASS')
ok('T14 already PARTIAL -> stays PARTIAL',
  tddVerifiedCap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', red_verified: false }] }, 'PARTIAL') === 'PARTIAL')
ok('T15 FAIL AC unverified does not falsely cap when PASS ACs verified',
  tddVerifiedCap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', red_verified: true }, { ac: 'AC-2', verdict: 'FAIL', red_verified: false }] }, 'ALL_PASS') === 'ALL_PASS')
ok('T16 PASS with missing red_verified (absent) -> capped',
  tddVerifiedCap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS' }] }, 'ALL_PASS') === 'PARTIAL')

// --- edge cases added 2026-07-07: cap-boundary, multi-AC mix, malformed input (Wave 2 eval pass) ---
ok('T17 mixed valid+invalid ACs -> only the invalid one is flagged',
  tddViolations({ ac_tdd: [validAc('AC-1'), { ac: 'AC-2', kind: 'new', red: { failed: true, right_reason: true }, green: { passed: true } }] }, true).length === 1)
// --- 0.10.4: doc-shaped ACs carry a CLAIM CHECK, not a blanket not_applicable ---
// KTP-1003 AC-L2 delivered a contract page asserting every census response carries Cache-Control, under
// a `[VERIFIED against app-proximity-report@bb1b3a6]` stamp. It was RED-exempt on the author's own
// `not_applicable(...)`, nothing ever executed the claim, and the claim was false — the reviewer proved
// it with a test written by hand, which is what makes the cost of this gate provably low.
// A document that asserts something about the code is a testable artifact; `not_applicable` is a lie
// about it. `doc_claims(<why>)` is the exemption for that shape, and it is not free: each listed claim
// must name the check that was RUN against it.
const claim = (c, v) => ({ claim: c, verified_by: v })
const docAc = (claims, exempt = 'doc_claims(contract page, no runtime surface)') =>
  ({ ac_tdd: [{ ac: 'AC-L2', kind: 'new', exempt, doc_claims: claims }] })

ok('T30 doc_claims exemption with an executed check per claim -> no violation',
  tddViolations(docAc([claim('every response carries Cache-Control', 'CensusControllerTest#allBranchesCacheControl, mvn -Dtest=... , passed')]), true).length === 0)
// These assert the message is the doc_claims one and NOT 'malformed exempt' — otherwise they would
// pass vacuously while `doc_claims(...)` is simply an unrecognised exemption form.
const docViol = (...a) => { const v = tddViolations(...a); return v.length === 1 && !has(v, 'malformed exempt') ? v[0] : '' }
ok('T31 doc_claims exemption with NO claims listed -> violation (KTP-1003)',
  docViol(docAc([]), true).includes('doc_claims'))
ok('T32 doc_claims exemption with a missing doc_claims array -> violation',
  docViol({ ac_tdd: [{ ac: 'AC-L2', kind: 'new', exempt: 'doc_claims(x)' }] }, true).includes('doc_claims'))
ok('T33 a listed claim with no verified_by -> violation (a stamp with nothing behind it)',
  docViol(docAc([claim('every response carries Cache-Control', undefined)]), true).includes('AC-L2'))
ok('T34 blank/whitespace verified_by does not count as an executed check',
  docViol(docAc([claim('c', '   ')]), true).includes('AC-L2'))
ok('T35 one unverified claim among several still violates',
  docViol(docAc([claim('a', 'T#a ran, passed'), claim('b', 'T#b ran, passed'), claim('c', '')]), true).includes('AC-L2'))
ok('T36 a claim with no claim text is malformed',
  docViol(docAc([claim('', 'T#x ran')]), true).includes('AC-L2'))
ok('T37 non-array doc_claims is a violation, never a silent pass',
  docViol({ ac_tdd: [{ ac: 'AC-L2', kind: 'new', exempt: 'doc_claims(x)', doc_claims: 'yes' }] }, true).includes('doc_claims'))
ok('T38 doc_claims still has to be a well-formed exemption string',
  has(tddViolations(docAc([claim('a', 'T#a')], 'doc_claims()'), true), 'malformed exempt'))
ok('T39 doc_claims on a NON-exempt AC is ignored (the RED rules still apply)',
  tddViolations({ ac_progress: { 'AC-1': 'done' }, ac_tdd: [{ ...validAc('AC-1'), doc_claims: [] }] }, true).length === 0)
ok('T40 the other two exemptions are unaffected by the doc_claims rule',
  tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', exempt: 'not_applicable(pure config)' }] }, true).length === 0 &&
  tddViolations({ ac_tdd: [{ ac: 'AC-2', kind: 'new', exempt: 'infra_blocked(no DB)' }] }, true).length === 0)
ok('T41 the violation text says what to do, not just what is wrong',
  tddViolations(docAc([]), true)[0].includes('verified_by'))

// --- 0.10.4: doc_claims cannot be dodged by picking the gentler exemption ---
// Caught while replaying KTP-1003 against the new gate: AC-L2 as actually filed —
// `not_applicable(contract page, no runtime surface)` — still returned ZERO violations, because the
// doc_claims rule only fires on an AC that self-selects into it. That is the identical self-selection
// escape that cost 0.10.1 and 0.10.3. An exemption whose own `deliverable` is a document is a
// doc-shaped AC whatever word the implementor reached for.
const naDoc = (deliverable, exempt = 'not_applicable(contract page, no runtime surface)') =>
  ({ ac_tdd: [{ ac: 'AC-L2', kind: 'new', exempt, deliverable }] })
ok('T42 not_applicable on a .md deliverable is rejected (KTP-1003 as actually filed)',
  has(tddViolations(naDoc('docs/agent-os/architecture/census-serving-contract.md'), true), 'doc_claims'))
ok('T43 the other doc extensions are covered too',
  has(tddViolations(naDoc('spec/a.rst'), true), 'doc_claims') &&
  has(tddViolations(naDoc('spec/b.adoc'), true), 'doc_claims') &&
  has(tddViolations(naDoc('spec/c.txt'), true), 'doc_claims'))
ok('T44 case and path shape do not matter',
  has(tddViolations(naDoc('DOCS/README.MD'), true), 'doc_claims'))
ok('T45 infra_blocked on a doc deliverable is rejected the same way',
  has(tddViolations(naDoc('docs/x.md', 'infra_blocked(no stack)'), true), 'doc_claims'))
ok('T46 a CODE deliverable under not_applicable is still fine',
  tddViolations(naDoc('src/main/java/Foo.java'), true).length === 0)
ok('T47 no deliverable declared -> rule cannot fire, and must not false-positive',
  tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', exempt: 'not_applicable(pure config)' }] }, true).length === 0)
ok('T48 a doc deliverable under a PROPER doc_claims exemption passes',
  tddViolations({ ac_tdd: [{ ac: 'AC-L2', kind: 'new', exempt: 'doc_claims(contract page)',
    deliverable: 'docs/census-serving-contract.md',
    doc_claims: [claim('every response carries Cache-Control', 'CensusControllerTest#all, mvn -Dtest=..., PASSED')] }] }, true).length === 0)
ok('T49 a non-string deliverable is ignored, never a crash',
  tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', exempt: 'not_applicable(x)', deliverable: 7 }] }, true).length === 0)

ok('T18 malformed exempt boundary: empty parens -> violation',
  has(tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', exempt: 'not_applicable()' }] }, true), 'malformed exempt'))
ok('T19 malformed exempt boundary: trailing text after close-paren -> violation',
  has(tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', exempt: 'infra_blocked(no DB) extra' }] }, true), 'malformed exempt'))
ok('T20 red.artifact empty string (falsy, not missing) -> RED violation',
  has(tddViolations({ ac_tdd: [{ ac: 'AC-1', kind: 'new', red: { failed: true, right_reason: true, artifact: '' }, green: { passed: true } }] }, true), 'no valid RED'))
ok('T21 tddVerifiedCap: overall FAIL is never upgraded even with unverified RED (only ALL_PASS is capped)',
  tddVerifiedCap({ per_ac: [{ ac: 'AC-1', verdict: 'FAIL', red_verified: false }] }, 'FAIL') === 'FAIL')
ok('T22 tddVerifiedCap: one unverified PASS among many verified PASS ACs still caps (boundary = single violation)',
  tddVerifiedCap({ per_ac: [
    { ac: 'AC-1', verdict: 'PASS', red_verified: true },
    { ac: 'AC-2', verdict: 'PASS', red_verified: true },
    { ac: 'AC-3', verdict: 'PASS', red_verified: false },
  ] }, 'ALL_PASS') === 'PARTIAL')
ok('T23 tddVerifiedCap: truthy non-boolean red_verified (1) is not strictly true/"exempt" -> capped',
  tddVerifiedCap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', red_verified: 1 }] }, 'ALL_PASS') === 'PARTIAL')
ok('T24 tddVerifiedCap: malformed input (qa.per_ac absent entirely) -> no violation found, overall unchanged',
  tddVerifiedCap({}, 'ALL_PASS') === 'ALL_PASS')

console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)

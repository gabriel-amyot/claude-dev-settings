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

// Regression guard for the visual-AC readiness logic (0.9.0). Exercises the REAL classifyQaGap +
// preShipBlockers + executionOk extracted verbatim from ../dark-factory.workflow.js (not reimplemented).
// Run: `node tests/visual-readiness.test.mjs`.
import { readFileSync } from 'fs'

const src = readFileSync(new URL('../dark-factory.workflow.js', import.meta.url), 'utf8')
function extract(name) {
  const m = src.match(new RegExp('^function ' + name + '[\\s\\S]*?\\n}', 'm'))
  if (!m) throw new Error('could not extract ' + name)
  return m[0]
}
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const mod = new AsyncFunction(
  extract('executionOk') + '\n' + extract('isMetNonCodeGate') + '\n' + extract('classifyQaGap') + '\n' + extract('preShipBlockers') +
  '\nconst log = () => {};' +
  '\nreturn { classifyQaGap, preShipBlockers };'
)
const { classifyQaGap, preShipBlockers } = await mod()

let pass = 0, fail = 0
const ok = (name, cond) => { if (cond) { pass++ } else { fail++; console.error('FAIL: ' + name) } }
const has = (arr, sub) => arr.some((v) => v.includes(sub))

const passAc = (ac) => ({ ac, verdict: 'PASS', code_ref: 'f:1', test_ref: 't', red_verified: true })
const visualPendingAc = (ac) => ({ ac, verdict: 'PARTIAL', code_ref: 'f:1', test_ref: 't', red_verified: true, visual_pending: true })

// --- classifyQaGap ---
ok('G1 all PASS + ALL_PASS -> all_pass',
  classifyQaGap({ per_ac: [passAc('AC-1')] }, 'ALL_PASS') === 'all_pass')
ok('G2 visual_pending the only non-PASS -> visual_only',
  classifyQaGap({ per_ac: [passAc('AC-1'), visualPendingAc('AC-2')] }, 'PARTIAL') === 'visual_only')
ok('G3 a logic AC PARTIAL (not visual_pending) -> real_gap',
  classifyQaGap({ per_ac: [passAc('AC-1'), { ac: 'AC-2', verdict: 'PARTIAL' }] }, 'PARTIAL') === 'real_gap')
ok('G4 visual_pending present but a PASS AC lacks test_ref -> real_gap',
  classifyQaGap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', code_ref: 'f:1' /* no test_ref */, red_verified: true }, visualPendingAc('AC-2')] }, 'PARTIAL') === 'real_gap')
ok('G5 PARTIAL AC without visual_pending flag -> real_gap',
  classifyQaGap({ per_ac: [passAc('AC-1'), { ac: 'AC-2', verdict: 'PARTIAL', code_ref: 'f', test_ref: 't' }] }, 'PARTIAL') === 'real_gap')
ok('G6 mixed: one visual_pending + one real FAIL -> real_gap',
  classifyQaGap({ per_ac: [visualPendingAc('AC-1'), { ac: 'AC-2', verdict: 'FAIL' }] }, 'PARTIAL') === 'real_gap')
// Met non-code gates (sequencing / dependency / human-decision ACs with no code surface) are met
// preconditions, not logic gaps — they must not force a real_gap halt (KTP-784 regression).
const metGateAc = (ac) => ({ ac, verdict: 'PARTIAL', code_ref: 'n/a (sequencing gate — no code)', test_ref: 'dependency met', red_verified: 'exempt', visual_pending: false })
ok('G7a met non-code gate alongside a visual_pending AC -> visual_only (gate excluded)',
  classifyQaGap({ per_ac: [passAc('AC-1'), metGateAc('AC-0'), metGateAc('AC-4'), visualPendingAc('AC-3')] }, 'PARTIAL') === 'visual_only')
ok('G7b met non-code gates as the only non-PASS, all PASS otherwise -> all_pass-equivalent (no real gap)',
  classifyQaGap({ per_ac: [passAc('AC-1'), metGateAc('AC-0')] }, 'PARTIAL') !== 'real_gap')
ok('G7c a no-code AC that FAILED is still a real_gap (gate keeps teeth)',
  classifyQaGap({ per_ac: [passAc('AC-1'), { ac: 'AC-0', verdict: 'FAIL', code_ref: 'n/a', red_verified: 'exempt' }] }, 'PARTIAL') === 'real_gap')
ok('G7d an exempt AC with a REAL code_ref + PARTIAL is still a real_gap (not a no-code gate)',
  classifyQaGap({ per_ac: [passAc('AC-1'), { ac: 'AC-2', verdict: 'PARTIAL', code_ref: 'src/x.ts:10', red_verified: 'exempt' }] }, 'PARTIAL') === 'real_gap')
ok('G7 PASS AC lacking red_verified -> real_gap (TDD evidence gap, not visual)',
  classifyQaGap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', code_ref: 'f', test_ref: 't' /* no red_verified */ }, visualPendingAc('AC-2')] }, 'PARTIAL') === 'real_gap')
ok('G8 visual_pending with exempt RED on the PASS AC -> visual_only',
  classifyQaGap({ per_ac: [{ ac: 'AC-1', verdict: 'PASS', code_ref: 'f', test_ref: 't', red_verified: 'exempt' }, visualPendingAc('AC-2')] }, 'PARTIAL') === 'visual_only')

// --- preShipBlockers (visual_only must NOT block; real_gap must) ---
const cleanImpl = { execution_verified: 'true', pushed: true }
const cleanReview = { criticals_open: 0 }

ok('B1 visual_only gap does NOT block',
  preShipBlockers(cleanImpl, cleanReview, 'PARTIAL', 'visual_only').length === 0)
ok('B2 real_gap blocks',
  has(preShipBlockers(cleanImpl, cleanReview, 'PARTIAL', 'real_gap'), 'not ALL_PASS'))
ok('B3 all_pass does not block',
  preShipBlockers(cleanImpl, cleanReview, 'ALL_PASS', 'all_pass').length === 0)
ok('B4 execution not verified blocks even when visual_only',
  has(preShipBlockers({ execution_verified: 'infra_blocked(no db)', pushed: true }, cleanReview, 'PARTIAL', 'visual_only'), 'execution not verified'))
ok('B5 open CRITICAL blocks even when visual_only',
  has(preShipBlockers(cleanImpl, { criticals_open: 1 }, 'PARTIAL', 'visual_only'), 'CRITICAL'))
ok('B6 not-pushed blocks even when visual_only',
  has(preShipBlockers({ execution_verified: 'true', pushed: false }, cleanReview, 'PARTIAL', 'visual_only'), 'was not pushed'))

console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)

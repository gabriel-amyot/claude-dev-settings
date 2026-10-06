// Regression guard for the review blocking gate (0.10.0). Exercises the REAL blockingFindings /
// reviewCountMismatch / preShipBlockers source extracted verbatim from ../dark-factory.workflow.js —
// NOT a reimplementation. Run: `node tests/review-gate.test.mjs`.
//
// What this guards: nine retros between 2026-06-22 and 2026-10-02 reported the same escape — a
// reviewer demonstrated a real defect with a failing test, filed it as HIGH, criticals_open stayed 0,
// and the fix loop never ran. The gate now derives its blocking set from the findings array. These
// cases pin that behaviour so it cannot silently regress to reading the self-reported integer.
import { readFileSync } from 'fs'

const src = readFileSync(new URL('../dark-factory.workflow.js', import.meta.url), 'utf8')

function extract(name) {
  const m = src.match(new RegExp('^function ' + name + '[\\s\\S]*?\\n}', 'm'))
  if (!m) throw new Error('could not extract ' + name + ' from the workflow file')
  return m[0]
}
function extractConst(name) {
  const m = src.match(new RegExp('^const ' + name + ' = .*$', 'm'))
  if (!m) throw new Error('could not extract const ' + name + ' from the workflow file')
  return m[0]
}
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const { blockingFindings, reviewCountMismatch, preShipBlockers, handoffUncertainty } = await new AsyncFunction(
  extractConst('LOW_CONFIDENCE') + '\n' +
  extract('handoffUncertainty') + '\n' + extract('blockingFindings') + '\n' + extract('reviewCountMismatch') + '\n' +
  extract('executionOk') + '\n' + extract('preShipBlockers') +
  '\nreturn { blockingFindings, reviewCountMismatch, preShipBlockers, handoffUncertainty };'
)()

let pass = 0, fail = 0
const ok = (name, cond) => { if (cond) { pass++ } else { fail++; console.error('FAIL: ' + name) } }
const F = (severity, demonstrated, title = 't') => ({ severity, demonstrated, title })
const rev = (findings, criticals_open) => ({ findings, criticals_open })

// --- the escape this gate exists to close ---
ok('B1 demonstrated HIGH blocks even at criticals_open:0',
  blockingFindings(rev([F('HIGH', true)], 0)).length === 1)
ok('B2 undemonstrated HIGH does NOT block',
  blockingFindings(rev([F('HIGH', false)], 0)).length === 0)
ok('B3 CRITICAL blocks whether demonstrated or not',
  blockingFindings(rev([F('CRITICAL', false)], 0)).length === 1 &&
  blockingFindings(rev([F('CRITICAL', true)], 1)).length === 1)
ok('B4 MEDIUM/LOW never block even when demonstrated',
  blockingFindings(rev([F('MEDIUM', true), F('LOW', true)], 0)).length === 0)
ok('B5 mixed set returns only the blocking ones',
  blockingFindings(rev([F('CRITICAL', false), F('HIGH', true), F('HIGH', false), F('LOW', true)], 1)).length === 2)

// --- the array is the truth, not the integer ---
ok('B6 criticals_open:0 with a CRITICAL in findings still blocks',
  blockingFindings(rev([F('CRITICAL', true)], 0)).length === 1)
ok('B7 criticals_open:5 with an empty findings array blocks nothing',
  blockingFindings(rev([], 5)).length === 0)

// --- robustness: malformed input must not throw, and must not silently pass a defect ---
ok('B8 missing findings array -> no blocking, no throw', blockingFindings({ criticals_open: 3 }).length === 0)
ok('B9 null review -> no throw', blockingFindings(null).length === 0)
ok('B10 null entry inside findings is skipped',
  blockingFindings(rev([null, F('CRITICAL', true)], 1)).length === 1)
ok('B11 lowercase severity still blocks (agents are not reliable about case)',
  blockingFindings(rev([F('critical', false)], 0)).length === 1 &&
  blockingFindings(rev([F('high', true)], 0)).length === 1)
ok('B12 demonstrated must be exactly true, not truthy string',
  blockingFindings(rev([F('HIGH', 'yes')], 0)).length === 0)

// --- self-count mismatch detection ---
ok('C1 matching count -> no mismatch', reviewCountMismatch(rev([F('CRITICAL', true)], 1)) === null)
ok('C2 undercount detected', typeof reviewCountMismatch(rev([F('CRITICAL', true)], 0)) === 'string')
ok('C3 overcount detected', typeof reviewCountMismatch(rev([], 2)) === 'string')
ok('C4 HIGHs are not counted as CRITICALs', reviewCountMismatch(rev([F('HIGH', true)], 0)) === null)
ok('C5 absent criticals_open -> no mismatch claim', reviewCountMismatch({ findings: [] }) === null)

// --- preShipBlockers wires it through ---
const goodImpl = { execution_verified: 'true', pushed: true }
ok('P1 demonstrated HIGH blocks pre-ship',
  preShipBlockers(goodImpl, rev([F('HIGH', true)], 0), 'ALL_PASS', 'all_pass')
    .some((b) => b.includes('DEMONSTRATED HIGH')))
ok('P2 clean review ships',
  preShipBlockers(goodImpl, rev([F('LOW', true)], 0), 'ALL_PASS', 'all_pass').length === 0)
ok('P3 CRITICAL wording preserved',
  preShipBlockers(goodImpl, rev([F('CRITICAL', true)], 1), 'ALL_PASS', 'all_pass')
    .some((b) => b.includes('CRITICAL')))
ok('P4 count mismatch surfaces as its own blocker',
  preShipBlockers(goodImpl, rev([], 3), 'ALL_PASS', 'all_pass')
    .some((b) => b.includes('criticals_open=3')))
ok('P5 unpushed branch still blocks',
  preShipBlockers({ execution_verified: 'true', pushed: false }, rev([], 0), 'ALL_PASS', 'all_pass').length === 1)
ok('P6 visual_only gap does not block',
  preShipBlockers(goodImpl, rev([], 0), 'PARTIAL', 'visual_only').length === 0)
ok('P7 real_gap QA blocks',
  preShipBlockers(goodImpl, rev([], 0), 'PARTIAL', 'real_gap').length === 1)

// --- fail closed on a malformed review ---
// Deriving from the findings array means a MISSING array must block. Caught by the 0.9.0 harness when
// the derive landed: a review claiming criticals_open:1 with no findings array would have SHIPPED.
ok('P8 claimed criticals with no findings array blocks',
  preShipBlockers(goodImpl, { criticals_open: 1 }, 'ALL_PASS', 'all_pass')
    .some((b) => b.includes('no findings array')))
ok('P9 missing findings array blocks even at criticals_open:0',
  preShipBlockers(goodImpl, { criticals_open: 0 }, 'ALL_PASS', 'all_pass')
    .some((b) => b.includes('no findings array')))
ok('P10 empty findings array is clean and ships',
  preShipBlockers(goodImpl, rev([], 0), 'ALL_PASS', 'all_pass').length === 0)

// --- handoffUncertainty: carry a low-confidence phase's own doubt forward (0.10.1) ---
ok('U1 confident phase hands nothing forward',
  handoffUncertainty({ confidence: 90, confidence_deductions: [{ points: 10, reason: 'x' }] }, 'Design') === '')
ok('U2 exactly at the threshold is NOT low',
  handoffUncertainty({ confidence: 75 }, 'Design') === '')
ok('U3 below threshold emits a note naming the phase and score',
  handoffUncertainty({ confidence: 67, confidence_deductions: [] }, 'Implement').includes('Implement phase closed at confidence 67'))
ok('U4 deduction reasons are carried verbatim',
  handoffUncertainty({ confidence: 60, confidence_deductions: [{ points: 20, reason: 'mapbox layer order unverified' }] }, 'Grill')
    .includes('mapbox layer order unverified'))
ok('U5 missing deductions still warns rather than going silent',
  handoffUncertainty({ confidence: 40 }, 'Design').includes('no deductions recorded'))
ok('U6 absent confidence hands nothing forward (not treated as 0)',
  handoffUncertainty({ status: 'pass' }, 'Design') === '')
ok('U7 null phase is safe', handoffUncertainty(null, 'Design') === '')
ok('U8 non-numeric confidence is ignored', handoffUncertainty({ confidence: 'low' }, 'Design') === '')

console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)

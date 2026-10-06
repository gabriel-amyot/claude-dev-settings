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
const { blockingFindings, reviewCountMismatch, preShipBlockers, handoffUncertainty, describeBlocking, remoteOutageRisk, looksLikeRemoteOutage, visualReadiness } = await new AsyncFunction(
  extractConst('LOW_CONFIDENCE') + '\n' + extractConst('OUTAGE_UTC_START') + '\n' +
  extractConst('OUTAGE_UTC_END') + '\n' + extractConst('REMOTE_OUTAGE_RX') + '\n' +
  extract('handoffUncertainty') + '\n' + extract('describeBlocking') + '\n' +
  extract('visualReadiness') + '\n' + extract('remoteOutageRisk') + '\n' + extract('looksLikeRemoteOutage') + '\n' + extract('blockingFindings') + '\n' + extract('reviewCountMismatch') + '\n' +
  extract('executionOk') + '\n' + extract('preShipBlockers') +
  '\nreturn { blockingFindings, reviewCountMismatch, preShipBlockers, handoffUncertainty, describeBlocking, remoteOutageRisk, looksLikeRemoteOutage, visualReadiness };'
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

// --- 0.10.3: a DEMONSTRATED finding naming an AC blocks at ANY severity ---
// KTP-1275 shipped past a proven gap graded MEDIUM; GH-231 past one graded LOW. Severity is an
// opinion about impact; "AC-N does not hold" is a fact about the deliverable.
const FA = (severity, demonstrated, ac) => ({ severity, demonstrated, ac, title: 't' })
ok('A1 demonstrated MEDIUM naming an AC blocks (KTP-1275)',
  blockingFindings(rev([FA('MEDIUM', true, 'AC-1b')], 0)).length === 1)
ok('A2 demonstrated LOW naming an AC blocks (GH-231)',
  blockingFindings(rev([FA('LOW', true, 'AC-5')], 0)).length === 1)
ok('A3 demonstrated MEDIUM with NO ac does not block (ordinary edge case)',
  blockingFindings(rev([FA('MEDIUM', true, undefined)], 0)).length === 0)
ok('A4 UNdemonstrated finding naming an AC does not block (hunch)',
  blockingFindings(rev([FA('MEDIUM', false, 'AC-2')], 0)).length === 0)
ok('A5 empty/whitespace ac string does not count as naming an AC',
  blockingFindings(rev([FA('LOW', true, '')], 0)).length === 0 &&
  blockingFindings(rev([FA('LOW', true, '   ')], 0)).length === 0)
ok('A6 non-string ac does not count',
  blockingFindings(rev([FA('LOW', true, 7)], 0)).length === 0)
ok('A7 preShip names the AC in the blocker text',
  preShipBlockers(goodImpl, rev([FA('LOW', true, 'AC-5')], 0), 'ALL_PASS', 'all_pass')
    .some((b) => b.includes('AC-5') && b.includes('any severity')))
ok('A8 describeBlocking attributes all three rules separately',
  (() => {
    const d = describeBlocking(blockingFindings(rev([F('CRITICAL', false), F('HIGH', true), FA('LOW', true, 'AC-9')], 1)))
    return d.includes('CRITICAL') && d.includes('DEMONSTRATED HIGH') && d.includes('AC-9')
  })())

// --- 0.10.3: known nightly remote-outage window ---
ok('O1 inside the window is flagged', remoteOutageRisk('2026-10-06T04:30:00Z').inWindow === true)
ok('O2 outside the window is not', remoteOutageRisk('2026-10-06T14:30:00Z').inWindow === false)
ok('O3 window start is inclusive', remoteOutageRisk('2026-10-06T03:00:00Z').inWindow === true)
ok('O4 window end is exclusive', remoteOutageRisk('2026-10-06T10:00:00Z').inWindow === false)
ok('O5 missing now -> unknown, not false-confident',
  remoteOutageRisk(null).known === false && remoteOutageRisk(null).inWindow === false)
ok('O6 malformed timestamp -> unknown', remoteOutageRisk('not-a-date').known === false)
ok('O7 in-window result carries an explanatory note',
  typeof remoteOutageRisk('2026-10-06T05:00:00Z').note === 'string')

ok('R1 a 502 reads as a remote outage', looksLikeRemoteOutage('fatal: unable to access ... 502 Bad Gateway'))
ok('R2 503/504 too', looksLikeRemoteOutage('503 Service Unavailable') && looksLikeRemoteOutage('gateway timeout'))
ok('R3 connection failures too', looksLikeRemoteOutage('Could not read from remote repository'))
ok('R4 a REJECTED push is NOT an outage (non-fast-forward is a real failure)',
  looksLikeRemoteOutage('! [rejected] dev -> dev (non-fast-forward)') === false)
ok('R5 a permission failure is NOT an outage',
  looksLikeRemoteOutage('remote: Permission to repo denied') === false)
ok('R6 pre-receive hook rejection is NOT an outage',
  looksLikeRemoteOutage('remote: error: pre-receive hook declined') === false)
ok('R7 null/undefined is not an outage',
  looksLikeRemoteOutage(null) === false && looksLikeRemoteOutage(undefined) === false)
// A non-string must not be COERCED into a match: ['502 Bad Gateway'] stringifies to '502 Bad Gateway'
// and would read as an outage without the typeof guard. Caught by mutation N7 surviving.
ok('R8 a non-string is never coerced into an outage',
  looksLikeRemoteOutage(['502 Bad Gateway']) === false &&
  looksLikeRemoteOutage({ toString: () => '503' }) === false &&
  looksLikeRemoteOutage(502) === false)

// --- 0.10.3: visual-AC shape known at the FRONT gate ---
const AC = (id, kind, fixture) => ({ id, ac_kind: kind, fixture })
ok('V1 every AC visual -> all_visual',
  visualReadiness([AC('AC-1','visual'),AC('AC-2','visual')]).shape === 'all_visual')
ok('V2 mix -> mixed', visualReadiness([AC('AC-1','visual'),AC('AC-2','logic')]).shape === 'mixed')
ok('V3 no visual -> logic_only', visualReadiness([AC('AC-1','logic')]).shape === 'logic_only')
ok('V4 empty -> unknown, never a false all_visual', visualReadiness([]).shape === 'unknown')
ok('V5 null/undefined acs is safe',
  visualReadiness(null).shape === 'unknown' && visualReadiness(undefined).shape === 'unknown')
ok('V6 unrecognised ac_kind does not count as either',
  visualReadiness([AC('AC-1','weird')]).shape === 'unknown')
ok('V7 case-insensitive on ac_kind',
  visualReadiness([AC('AC-1','VISUAL'),AC('AC-2','Logic')]).shape === 'mixed')
ok('V8 missing fixtures are listed by AC id',
  visualReadiness([AC('AC-1','visual','missing'),AC('AC-2','visual','available')]).missing_fixture.join() === 'AC-1')
ok('V9 counts are reported',
  (() => { const r = visualReadiness([AC('A','visual'),AC('B','logic'),AC('C','logic')])
           return r.visual === 1 && r.logic === 2 && r.total === 3 })())
ok('V10 null entries inside acs are skipped',
  visualReadiness([null, AC('AC-1','logic')]).shape === 'logic_only')

console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)

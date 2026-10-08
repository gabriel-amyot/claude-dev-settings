// Regression guard for the three KTP-1003 surfacing gates (0.10.4). Exercises the REAL
// harnessReadiness / toolchainMismatch / firstOfKindNotes source extracted verbatim from
// ../dark-factory.workflow.js — NOT a reimplementation. Run: `node tests/design-qa-gates.test.mjs`.
//
// All three close a "nobody was told" failure from run-2026-10-07-KTP-1003 (fitness 80):
//   5. Design handed grill a @SpringBootTest harness that could not start. Grill caught three defects
//      in it; design had never run it once.
//   6. QA ran JDK 21 against a pom targeting release 17, in a repo whose CLAUDE.md records a JDK 21
//      Lombok break. No harm landed, but the measured toolchain was not the declared one.
//   7. The repo had ZERO @SpringBootTest classes. Grill read that absence as a past decision. The
//      factory added the first one without surfacing it to a human.
import { readFileSync } from 'fs'

const src = readFileSync(new URL('../dark-factory.workflow.js', import.meta.url), 'utf8')
function extract(name) {
  const m = src.match(new RegExp('^function ' + name + '[\\s\\S]*?\\n}', 'm'))
  if (!m) throw new Error('could not extract ' + name + ' from the workflow file')
  return m[0]
}
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const { harnessReadiness, toolchainMismatch, firstOfKindNotes } = await new AsyncFunction(
  extract('harnessReadiness') + '\n' + extract('toolchainMismatch') + '\n' + extract('firstOfKindNotes') +
  '\nreturn { harnessReadiness, toolchainMismatch, firstOfKindNotes };'
)()

let pass = 0, fail = 0
const ok = (name, cond) => { if (cond) { pass++ } else { fail++; console.error('FAIL: ' + name) } }

// --- Item 5: a NEW test harness is boot-checked during design, before grill ---
const H = (h) => ({ status: 'pass', summary: 's', new_harness: h })
ok('H1 no new harness -> nothing to say',
  harnessReadiness({ status: 'pass', summary: 's' }) === '')
ok('H2 a boot-checked harness with its beans enumerated is clean',
  harnessReadiness(H({ kind: '@SpringBootTest', boot_checked: true, beans_enumerated: true })) === '')
ok('H3 a declared harness that was never booted is surfaced (KTP-1003)',
  harnessReadiness(H({ kind: '@SpringBootTest', boot_checked: false })).includes('@SpringBootTest'))
ok('H4 absent boot_checked is treated as NOT booted, never as clean',
  harnessReadiness(H({ kind: '@SpringBootTest' })) !== '')
ok('H5 booted but beans not enumerated is still surfaced',
  // KTP-1003's bean list missed 2 of the controller's 5 constructor args — booting is not enough.
  harnessReadiness(H({ kind: '@SpringBootTest', boot_checked: true, beans_enumerated: false })).includes('bean'))
ok('H6 the note tells grill what to check, not just that something is wrong',
  harnessReadiness(H({ kind: '@SpringBootTest', boot_checked: false })).toLowerCase().includes('grill'))
ok('H7 truthy-but-not-true boot_checked does not pass',
  harnessReadiness(H({ kind: '@SpringBootTest', boot_checked: 'yes' })) !== '')
ok('H8 a harness with no kind named is still surfaced',
  harnessReadiness(H({ boot_checked: false })) !== '')
ok('H9 null/malformed design is safe',
  harnessReadiness(null) === '' && harnessReadiness({}) === '' && harnessReadiness({ new_harness: 'x' }) === '')

// --- Item 6: QA's measured toolchain must be the one the build declares ---
const T = (declared, actual) => ({ raw_overall: 'ALL_PASS', per_ac: [], toolchain: { declared, actual } })
ok('M1 matching toolchain -> no mismatch',
  toolchainMismatch(T('17', '17')) === null)
ok('M2 JDK 21 against release 17 is reported (KTP-1003)',
  toolchainMismatch(T('17', '21')).includes('21'))
ok('M3 the report names BOTH the declared and the measured value',
  (() => { const m = toolchainMismatch(T('17', '21')); return m.includes('17') && m.includes('21') })())
ok('M4 cosmetic formatting is not a mismatch',
  toolchainMismatch(T('17', ' 17 ')) === null && toolchainMismatch(T('1.8', '1.8')) === null)
ok('M5 a missing toolchain block is reported as unmeasured, not as clean',
  typeof toolchainMismatch({ raw_overall: 'ALL_PASS', per_ac: [] }) === 'string')
ok('M6 a half-filled toolchain block is reported',
  typeof toolchainMismatch(T('17', undefined)) === 'string' &&
  typeof toolchainMismatch(T(undefined, '21')) === 'string')
ok('M7 numbers and strings compare equal (agents are not reliable about type)',
  toolchainMismatch(T(17, '17')) === null)
ok('M8 null qa is safe', toolchainMismatch(null) === null)

// --- Item 7: a pattern the repo has ZERO of is a human decision, not a default ---
const FK = (list) => ({ status: 'pass', summary: 's', first_of_kind: list })
ok('F1 nothing first-of-its-kind -> nothing to say',
  firstOfKindNotes({ status: 'pass', summary: 's' }) === '' && firstOfKindNotes(FK([])) === '')
ok('F2 a first-of-its-kind pattern is named (KTP-1003 @SpringBootTest)',
  firstOfKindNotes(FK([{ pattern: '@SpringBootTest', repo_count: 0 }])).includes('@SpringBootTest'))
ok('F3 the note says WHY it matters — absence at that scale is usually a decision',
  firstOfKindNotes(FK([{ pattern: '@SpringBootTest', repo_count: 0 }])).toLowerCase().includes('decision'))
ok('F4 a pattern the repo already has is NOT first-of-its-kind',
  firstOfKindNotes(FK([{ pattern: '@MockBean', repo_count: 12 }])) === '')
ok('F5 mixed list reports only the genuinely-zero ones',
  (() => {
    const n = firstOfKindNotes(FK([{ pattern: '@MockBean', repo_count: 12 }, { pattern: '@SpringBootTest', repo_count: 0 }]))
    return n.includes('@SpringBootTest') && !n.includes('@MockBean')
  })())
ok('F6 several first-of-kind patterns are all named',
  (() => {
    const n = firstOfKindNotes(FK([{ pattern: 'A', repo_count: 0 }, { pattern: 'B', repo_count: 0 }]))
    return n.includes('A') && n.includes('B')
  })())
ok('F7 a missing repo_count is treated as zero (claimed first-of-kind), not skipped',
  firstOfKindNotes(FK([{ pattern: '@SpringBootTest' }])).includes('@SpringBootTest'))
ok('F8 an unnamed pattern is skipped rather than emitting a blank line',
  firstOfKindNotes(FK([{ pattern: '', repo_count: 0 }])) === '')
ok('F9 null/malformed is safe',
  firstOfKindNotes(null) === '' && firstOfKindNotes({ first_of_kind: 'x' }) === '' &&
  firstOfKindNotes(FK([null])) === '')

console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)

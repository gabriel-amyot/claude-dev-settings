// Regression guard for the ticket-source resolver (0.10.0). Exercises the REAL resolveTicketSource
// source extracted verbatim from ../dark-factory.workflow.js — NOT a reimplementation (that would be
// a tautology the TDD discipline warns against). Run: `node tests/ticket-source.test.mjs`.
//
// What this guards: the resolver decides whether a run talks to Jira or to the wayfinder tracker, and
// it is the only thing standing between a mistyped repo and a factory run posting into the wrong
// issue tracker. A silent default there is worse than a crash, so the unsupported-repo case is a
// first-class assertion, not an afterthought.
import { readFileSync } from 'fs'

const src = readFileSync(new URL('../dark-factory.workflow.js', import.meta.url), 'utf8')

function extract(name) {
  const m = src.match(new RegExp('^function ' + name + '[\\s\\S]*?\\n}', 'm'))
  if (!m) throw new Error('could not extract ' + name + ' from the workflow file')
  return m[0]
}
const repoM = src.match(/^const WAYFINDER_REPO = .*$/m)
if (!repoM) throw new Error('could not extract WAYFINDER_REPO from the workflow file')

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const { resolveTicketSource, WAYFINDER_REPO } = await new AsyncFunction(
  repoM[0] + '\n' + extract('resolveTicketSource') +
  '\nreturn { resolveTicketSource, WAYFINDER_REPO };'
)()

let pass = 0, fail = 0
const ok = (name, cond) => { if (cond) { pass++ } else { fail++; console.error('FAIL: ' + name) } }
const threw = (input) => {
  try { resolveTicketSource(input); return false } catch { return true }
}

// --- Jira keys stay Jira ---
for (const key of ['KTP-1234', 'INS-7', 'SPV-69', 'KTT-1']) {
  const r = resolveTicketSource(key)
  ok('jira ' + key, r.source === 'jira' && r.ticket === key && r.issue_repo === null && r.issue_number === null)
}

// --- wayfinder issue forms all land on the same ticket ---
const forms = [
  '#123',
  'gh#123',
  '123',
  WAYFINDER_REPO + '#123',
  'https://github.com/' + WAYFINDER_REPO + '/issues/123',
  'https://github.com/' + WAYFINDER_REPO + '/issues/123/',
]
for (const f of forms) {
  const r = resolveTicketSource(f)
  ok('github form ' + f,
    r.source === 'github' && r.ticket === 'GH-123' && r.issue_number === 123 && r.issue_repo === WAYFINDER_REPO)
}

// --- the guard that matters: a non-wayfinder repo must CRASH, never silently retarget ---
ok('other-repo qualified ref throws', threw('someone/other-repo#123'))
ok('other-repo issue URL throws', threw('https://github.com/someone/other-repo/issues/123'))
ok('klever code repo issue throws', threw('gabriel-amyot/compostelaguide#5'))

// --- unparseable input crashes rather than guessing ---
ok('empty string -> null (caller raises the arg error)', resolveTicketSource('') === null)
ok('undefined -> null', resolveTicketSource(undefined) === null)
ok('prose throws', threw('the map ticket'))
ok('lowercase jira-ish throws', threw('ktp-1234'))
ok('PR url throws', threw('https://github.com/' + WAYFINDER_REPO + '/pull/123'))
ok('bare hash with no number throws', threw('#'))
ok('trailing text throws', threw('KTP-1234 and also #5'))

// --- whitespace is trimmed, not treated as unparseable ---
ok('whitespace trimmed (jira)', resolveTicketSource('  KTP-1234 ').ticket === 'KTP-1234')
ok('whitespace trimmed (github)', resolveTicketSource(' #123 ').ticket === 'GH-123')

console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)

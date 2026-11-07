// Regression guard for the substrate preflight and the AC-preservation rule (0.10.6). Exercises the
// REAL runtimeIsolation / substratePreflight / scopeCutFindings / scopeCutNote source extracted verbatim
// from ../dark-factory.workflow.js, NOT a reimplementation. Run: `node tests/substrate-scope.test.mjs`.
// Set DF_WORKFLOW_SRC=<path> to run the same cases against another revision of the workflow file
// (that is how the "fails on the old code" proof was made).
//
// What this guards:
//  - 2026-06-16 and 2026-08-20: `isolation: 'worktree'` on six agent() calls created worktrees in
//    project-management (the workflow cwd), and a full disk killed a run mid `git worktree add`.
//  - KTP-779: an undemonstrated "redundant" review finding was acted on and half the ticket shipped.
import { readFileSync } from 'fs'

const srcPath = process.env.DF_WORKFLOW_SRC || new URL('../dark-factory.workflow.js', import.meta.url)
const src = readFileSync(srcPath, 'utf8')

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
const { runtimeIsolation, substratePreflight, scopeCutFindings, scopeCutNote, isScopeCutClaim } = await new AsyncFunction(
  extractConst('PM_PATH_RX') + '\n' + extractConst('DEFAULT_MIN_FREE_GB') + '\n' + extractConst('SCOPE_CUT_RX') + '\n' +
  extract('runtimeIsolation') + '\n' + extract('substratePreflight') + '\n' +
  extract('isScopeCutClaim') + '\n' + extract('scopeCutFindings') + '\n' + extract('scopeCutNote') +
  '\nreturn { runtimeIsolation, substratePreflight, scopeCutFindings, scopeCutNote, isScopeCutClaim };'
)()

let pass = 0, fail = 0
const ok = (name, cond) => { if (cond) { pass++ } else { fail++; console.error('FAIL: ' + name) } }

// --- S0: the whole workflow script still parses (top-level return + await are legal in a Workflow body) ---
{
  let parsed = true
  try { new AsyncFunction('args', 'agent', 'phase', 'log', src.replace(/^export const meta/m, 'const meta')) } catch (e) { parsed = false; console.error(e.message) }
  ok('S0 workflow script parses', parsed)
}

// --- runtime isolation: only when the caller says the cwd is NOT project-management ---
const PM = '/Users/gamyot/Developer/grp-beklever-com/project-management'
ok('S1 cwd = project-management -> no runtime isolation', runtimeIsolation(PM) === false)
ok('S2 cwd inside project-management -> no runtime isolation', runtimeIsolation(PM + '/tickets/KTP') === false)
ok('S3 cwd = a code repo -> runtime isolation', runtimeIsolation('/Users/gamyot/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal') === true)
ok('S4 a repo merely NAMED like project-management is not a false positive',
  runtimeIsolation('/Users/gamyot/Developer/gabriel-amyot/klever-project-management') === true)
ok('S5 cwd not supplied -> fail safe, no runtime isolation', runtimeIsolation(undefined) === false && runtimeIsolation('') === false && runtimeIsolation(null) === false)

// --- disk floor: halt before any agent, with the number in the message ---
{
  const r = substratePreflight({ cwd: '/repo/app', free_disk_gb: 10 })
  ok('S6 10 GB < 15 GB floor -> not ok', r.ok === false)
  ok('S6b the problem names the measured GB and the floor', r.problems.length === 1 && r.problems[0].includes('10 GB') && r.problems[0].includes('15 GB'))
}
ok('S7 40 GB -> ok', substratePreflight({ cwd: '/repo/app', free_disk_gb: 40 }).ok === true)
{
  const r = substratePreflight({ cwd: '/repo/app' })
  ok('S8 no free_disk_gb -> ok, but a note says disk was NOT checked', r.ok === true && r.notes.some((n) => n.includes('NOT checked')))
}
ok('S9 min_free_gb override is honoured', substratePreflight({ free_disk_gb: 20, min_free_gb: 30 }).ok === false &&
  substratePreflight({ free_disk_gb: 20, min_free_gb: 5 }).ok === true)
ok('S10 a non-numeric free_disk_gb does not throw and does not pass silently',
  substratePreflight({ free_disk_gb: 'lots' }).notes.some((n) => n.includes('NOT checked')))
ok('S11 bad min_free_gb falls back to the default floor', substratePreflight({ free_disk_gb: 12, min_free_gb: -1 }).ok === false)
ok('S12 stray pm worktrees are reported, never cleaned (read-only)',
  substratePreflight({ cwd: PM, free_disk_gb: 50, pm_worktrees: 3 }).notes.some((n) => n.includes('3 stray worktree') && n.includes('manual')))
ok('S13 null args -> no throw, default floor', substratePreflight(null).min_free_gb === 15)

// --- static wiring: no agent() call carries a hard-coded isolation, and the halt precedes every agent ---
{
  const agentCalls = src.split('\n').filter((l) => /\blabel: /.test(l) && /phase: /.test(l))
  const hardCoded = agentCalls.filter((l) => /isolation:\s*'worktree'/.test(l))
  ok('W1 no agent() options line hard-codes isolation: \'worktree\' (was 6)', agentCalls.length > 0 && hardCoded.length === 0)
  ok('W2 six code agents spread the computed ISO options', agentCalls.filter((l) => l.includes('...ISO')).length === 6)
  const haltAt = src.indexOf("status: 'HALT_SUBSTRATE'")
  const pipelineAt = src.indexOf('await runPipeline()')
  ok('W3 HALT_SUBSTRATE returns before runPipeline (so before any agent())', haltAt > 0 && pipelineAt > 0 && haltAt < pipelineAt)
  ok('W4 the old "runtime gave you your own worktree" prompt text is gone from the spine',
    !/The runtime gave you your own worktree/.test(src))
}

// --- AC preservation: a redundancy claim is never a cut ---
const F = (title, extra) => Object.assign({ severity: 'LOW', demonstrated: false, title }, extra || {})
{
  const ktp779 = F('NAME added to state_boundaries is redundant (consumer reads centers, not boundaries)')
  const r = scopeCutFindings({ findings: [ktp779] })
  ok('D1 KTP-779 shape: undemonstrated "redundant" -> needs_proof', r.needs_proof.length === 1 && r.proposed.length === 0)
}
{
  const r = scopeCutFindings({ findings: [F('boundary tileset is unnecessary', { redundancy_trace: 'demographics header reads centers only: Header.tsx:42; ui-probe click on boundary shows no NAME read' })] })
  ok('D2 a traced redundancy claim is a PROPOSAL for a human, not needs_proof', r.proposed.length === 1 && r.needs_proof.length === 0)
}
ok('D3 scope_cut:true is caught even without a keyword in the title',
  scopeCutFindings({ findings: [F('drop the second upload', { scope_cut: true })] }).needs_proof.length === 1)
ok('D4 an ordinary defect is not a scope-cut claim',
  scopeCutFindings({ findings: [F('null province name crashes the header', { severity: 'HIGH', demonstrated: true })] }).needs_proof.length === 0)
ok('D5 a demonstrated:true flag does NOT turn a redundancy claim into a proof (only a trace does)',
  scopeCutFindings({ findings: [F('centers upload is redundant', { demonstrated: true })] }).needs_proof.length === 1)
ok('D6 null review / missing findings / null entry -> empty, no throw',
  scopeCutFindings(null).needs_proof.length === 0 && scopeCutFindings({}).proposed.length === 0 &&
  scopeCutFindings({ findings: [null] }).needs_proof.length === 0)
ok('D7 whitespace-only trace counts as no trace', scopeCutFindings({ findings: [F('x is redundant', { redundancy_trace: '   ' })] }).needs_proof.length === 1)
ok('D8 the note says the factory did not cut scope', scopeCutNote(scopeCutFindings({ findings: [F('y is redundant')] })).includes('did not cut scope'))
ok('D9 no claims -> empty note', scopeCutNote({ needs_proof: [], proposed: [] }) === '' && scopeCutNote(null) === '')
ok('D10 the fix and QA prompts carry the AC-preservation rule',
  (src.match(/\$\{AC_PRESERVATION_RULE\}/g) || []).length >= 2)
ok('D11 "redundant" inside a longer word does not match', isScopeCutClaim(F('nonredundantly cached')) === false)

console.log(`substrate-scope: ${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)

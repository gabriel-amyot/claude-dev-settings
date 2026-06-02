export const meta = {
  name: 'dark-factory-v2',
  description: 'Ticket-to-dev factory v2 (seed). Deterministic Workflow orchestration of the backend/Java floor. Gates are JS code, not prose, so no phase can be skipped or self-certified past. Human concierge gate at the front. Every phase returns a soft confidence (0-100). A final Retro phase scores the run, captures red flags, and writes telemetry + a next-run improvement handoff. Terminal state READY_TO_SHIP: the workflow does code work + pushes the branch; the main loop runs the MR + Jira + post-merge validate.',
  phases: [
    { title: 'Concierge', detail: 'analyze + context + prereqs; surface decisions for the human' },
    { title: 'Design',    detail: 'tactical impl plan + test specs' },
    { title: 'Grill',     detail: 'interrogate the plan against the codebase' },
    { title: 'Implement', detail: 'TDD per AC in a worktree; attempt execution; push branch' },
    { title: 'Review',    detail: 'fresh adversarial agent in its own worktree on the pushed branch' },
    { title: 'QA',        detail: 'fresh agent proves each AC; verdict capped by execution_verified + evidence' },
    { title: 'ShipPrep',  detail: 'version bump + CHANGELOG + commit + push (no MR/Jira)' },
    { title: 'Retro',     detail: 'score the run, capture red flags, write telemetry + improvement handoff' },
  ],
}

// ---------------------------------------------------------------------------
// Seed scope: ONE floor (backend/Java), single-pass review + QA, like-for-like.
// Built BLIND to any specific ticket: the ticket is a black-box arg.
// Verified Workflow-API constraints: skills unsafe in-agent (Ship = code-prep
// only; main loop does MR+Jira+validate); sibling agents can't see each other's
// worktree (Implement pushes the branch; Review/QA/Ship fetch+checkout it); no
// loop guard (explicit resume guard); no wait primitive (Validate is post-merge).
//
// INSTRUMENTATION (migrated from v1): every phase returns a soft `confidence`
// (0-100) + `confidence_deductions` (signal, not a gate). A final Retro phase
// scores the whole run, lists red flags, and writes telemetry + a next-run
// improvement handoff so each run makes the next one better.
// ---------------------------------------------------------------------------

const CONTRACTS = '/Users/gabrielamyot/.claude/skills/dark-factory-v2/contracts'
const RUNS = '/Users/gabrielamyot/.claude/skills/dark-factory-v2/runs'

const ticket = (args && args.ticket) || null
const org = (args && args.org) || 'klever'
const humanDecisions = (args && args.humanDecisions) || null
if (!ticket) throw new Error('dark-factory-v2 requires args.ticket (e.g. "KTP-728")')

// ---- Schemas (handoffs are validated objects, not parsed text) ----

const CONCIERGE_SCHEMA = {
  type: 'object',
  required: ['spec_quality', 'needs_human', 'ac_count', 'repos', 'prereqs_ok', 'open_questions', 'ticket_folder', 'summary'],
  properties: {
    spec_quality: { type: 'string', enum: ['PASS', 'FAIL'] },
    needs_human: { type: 'boolean' },
    ac_count: { type: 'integer', minimum: 0 },
    repos: { type: 'array', items: { type: 'string' } },
    prereqs_ok: { type: 'boolean' },
    ticket_folder: { type: 'string', minLength: 1 },
    open_questions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'question', 'why_blocking'],
        properties: {
          id: { type: 'string' }, question: { type: 'string' }, why_blocking: { type: 'string' },
          options: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    summary: { type: 'string' },
    confidence: { type: 'integer', minimum: 0, maximum: 100 },
    confidence_deductions: { type: 'array', items: { type: 'object', properties: { points: { type: 'integer' }, reason: { type: 'string' } } } },
  },
}

const PHASE_SCHEMA = {
  type: 'object',
  required: ['status', 'summary'],
  properties: {
    status: { type: 'string', enum: ['pass', 'partial', 'stuck'] },
    summary: { type: 'string' },
    artifacts: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
    confidence: { type: 'integer', minimum: 0, maximum: 100 },
    confidence_deductions: { type: 'array', items: { type: 'object', properties: { points: { type: 'integer' }, reason: { type: 'string' } } } },
  },
}

const IMPLEMENT_SCHEMA = {
  type: 'object',
  required: ['status', 'execution_verified', 'ac_progress', 'branch', 'pushed', 'diff_artifact'],
  properties: {
    status: { type: 'string', enum: ['pass', 'partial', 'stuck'] },
    execution_verified: { type: 'string', pattern: '^(true|false|infra_blocked\\(.*\\)|not_applicable\\(.*\\))$' },
    ac_progress: { type: 'object' },
    branch: { type: 'string', minLength: 1 },
    pushed: { type: 'boolean' },
    diff_artifact: { type: 'string' },
    summary: { type: 'string' },
    confidence: { type: 'integer', minimum: 0, maximum: 100 },
    confidence_deductions: { type: 'array', items: { type: 'object', properties: { points: { type: 'integer' }, reason: { type: 'string' } } } },
  },
}

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['criticals_open', 'findings'],
  properties: {
    criticals_open: { type: 'integer', minimum: 0 },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'title', 'demonstrated'],
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] },
          title: { type: 'string' }, file: { type: 'string' }, demonstrated: { type: 'boolean' },
        },
      },
    },
    summary: { type: 'string' },
    confidence: { type: 'integer', minimum: 0, maximum: 100 },
    confidence_deductions: { type: 'array', items: { type: 'object', properties: { points: { type: 'integer' }, reason: { type: 'string' } } } },
  },
}

const QA_SCHEMA = {
  type: 'object',
  required: ['raw_overall', 'per_ac'],
  properties: {
    raw_overall: { type: 'string', enum: ['ALL_PASS', 'PARTIAL', 'FAIL'] },
    per_ac: {
      type: 'array',
      items: {
        type: 'object',
        required: ['ac', 'verdict'],
        properties: {
          ac: { type: 'string' }, verdict: { type: 'string', enum: ['PASS', 'PARTIAL', 'FAIL'] },
          code_ref: { type: 'string' }, test_ref: { type: 'string' },
        },
      },
    },
    summary: { type: 'string' },
    confidence: { type: 'integer', minimum: 0, maximum: 100 },
    confidence_deductions: { type: 'array', items: { type: 'object', properties: { points: { type: 'integer' }, reason: { type: 'string' } } } },
  },
}

const SHIPPREP_SCHEMA = {
  type: 'object',
  required: ['status', 'branch', 'pushed'],
  properties: {
    status: { type: 'string', enum: ['pass', 'partial', 'stuck'] },
    branch: { type: 'string', minLength: 1 },
    version: { type: 'string' },
    pushed: { type: 'boolean' },
    summary: { type: 'string' },
    confidence: { type: 'integer', minimum: 0, maximum: 100 },
    confidence_deductions: { type: 'array', items: { type: 'object', properties: { points: { type: 'integer' }, reason: { type: 'string' } } } },
  },
}

const RETRO_SCHEMA = {
  type: 'object',
  required: ['task_confidence', 'factory_fitness', 'red_flags', 'improvements'],
  properties: {
    task_confidence: { type: 'integer', minimum: 0, maximum: 100 }, // is the TASK done?
    factory_fitness: { type: 'integer', minimum: 0, maximum: 100 }, // did the FACTORY perform well?
    deductions: { type: 'array', items: { type: 'object', properties: { points: { type: 'integer' }, reason: { type: 'string' } } } },
    red_flags: { type: 'array', items: { type: 'string' } },
    improvements: { type: 'array', items: { type: 'object', required: ['title', 'detail'], properties: { title: { type: 'string' }, detail: { type: 'string' } } } },
    telemetry_written: { type: 'string' },
    handoff_written: { type: 'string' },
    summary: { type: 'string' },
  },
}

// ---- Gates: deterministic JS ----

function capQaVerdict(execVerified, rawOverall) {
  const v = String(execVerified)
  if (v === 'true') return rawOverall
  if (v.indexOf('not_applicable') === 0) return rawOverall
  if (v.indexOf('infra_blocked') === 0) return 'PARTIAL'
  if (v !== 'false') log(`WARN: unrecognised execution_verified="${v}" -> capping QA to INCOMPLETE`)
  return 'INCOMPLETE'
}

function evidenceCappedOverall(qa) {
  const unsupported = (qa.per_ac || []).some((a) => a.verdict === 'PASS' && (!a.code_ref || !a.test_ref))
  if (qa.raw_overall === 'ALL_PASS' && unsupported) {
    log('WARN: a PASS AC lacks code_ref/test_ref -> capping QA to PARTIAL')
    return 'PARTIAL'
  }
  return qa.raw_overall
}

function executionOk(ev) {
  const v = String(ev)
  return v === 'true' || v.indexOf('not_applicable') === 0
}

function preShipBlockers(impl, review, qaCapped) {
  const b = []
  if (!impl || !executionOk(impl.execution_verified)) b.push(`execution not verified (${impl ? impl.execution_verified : 'no impl'})`)
  if (!impl || impl.pushed !== true) b.push('feature branch was not pushed (review/QA could not see the code)')
  if (!review) b.push('no review artifact')
  else if (review.criticals_open > 0) b.push(`${review.criticals_open} open CRITICAL finding(s)`)
  if (qaCapped !== 'ALL_PASS') b.push(`QA verdict is ${qaCapped}, not ALL_PASS`)
  return b
}

// Soft-signal instruction appended to every phase prompt.
const CONFIDENCE_BLURB = `
Also return two SOFT signal fields (not a gate): "confidence" (integer 0-100 = how confident you are this phase is correct and complete) and "confidence_deductions" (array of { points, reason } accounting for EVERY point below 100). Be honest — this feeds the run eval.`

let _tf = null
const readContract = (name) =>
  `Read ${CONTRACTS}/${name}.md and execute it exactly for ticket ${ticket} (org: ${org}). Ticket folder (absolute): ${_tf || '(resolved by concierge)'}.${CONFIDENCE_BLURB}`

// Trace of phase outcomes for the Retro phase.
const trace = []
const rec = (name, r, extra) => { trace.push({ phase: name, status: (r && (r.status || r.spec_quality)) || extra || '?', confidence: r ? r.confidence : null }); return r }

// =================== PIPELINE ===================

async function runPipeline() {
  phase('Concierge')
  log(`Dark Factory v2 (seed) — ${ticket}`)
  const concierge = await agent(
    `Read ${CONTRACTS}/1-concierge.md and execute it for ticket ${ticket} (org: ${org}).
You are the concierge: validate spec quality, gather context, extract ACs, check prerequisites, and
RESOLVE the absolute ticket-folder path (return it as ticket_folder). This is the front gate. If
anything needs a human decision (ambiguous spec, missing/unknown repo or stack, a greenfield infra
choice, an unmet prerequisite), set needs_human=true and list each as a specific open_question.
Do NOT guess past these.${CONFIDENCE_BLURB}`,
    { schema: CONCIERGE_SCHEMA, label: 'concierge', phase: 'Concierge' }
  )
  if (!concierge) return { status: 'HALT_AGENT_SKIPPED', phase: 'Concierge', ticket }
  rec('concierge', concierge, concierge.spec_quality)
  if (concierge.spec_quality === 'FAIL') return { status: 'BLOCKED_SPEC_QUALITY', ticket, concierge }
  if (concierge.needs_human && !humanDecisions) {
    return { status: 'AWAITING_HUMAN', ticket, decision_packet: concierge.open_questions, concierge,
      resume_hint: 'Re-invoke Workflow with resumeFromRunId and args.humanDecisions = {<id>: <answer>}' }
  }
  if (concierge.needs_human && humanDecisions) {
    return { status: 'BLOCKED_NEEDS_HUMAN_AGAIN', ticket, decision_packet: concierge.open_questions, concierge,
      note: 'Answers supplied but concierge still needs_human. Not re-looping automatically.' }
  }

  _tf = concierge.ticket_folder
  const decisions = humanDecisions || {}
  const decisionsNote = Object.keys(decisions).length
    ? `Human decisions to honor (apply these): ${JSON.stringify(decisions)}`
    : 'No human decisions were required.'

  phase('Design')
  const design = await agent(`${readContract('2-design')}\n${decisionsNote}`, { schema: PHASE_SCHEMA, label: 'design', phase: 'Design' })
  if (!design) return { status: 'HALT_AGENT_SKIPPED', phase: 'Design', ticket }
  rec('design', design)
  if (design.status === 'stuck') return { status: 'HALT_DESIGN_STUCK', ticket, design }

  phase('Grill')
  const grill = await agent(`${readContract('3-grill')}\nInterrogate the design plan against the actual codebase (use git, not just local files). ${decisionsNote}`, { schema: PHASE_SCHEMA, label: 'grill', phase: 'Grill' })
  if (!grill) return { status: 'HALT_AGENT_SKIPPED', phase: 'Grill', ticket }
  rec('grill', grill)
  if (grill.status === 'stuck') return { status: 'HALT_GRILL_UNWORKABLE', ticket, design, grill }

  phase('Implement')
  const impl = await agent(`${readContract('4-implement')}
The Workflow runtime gave you your OWN git worktree — do NOT run 'git worktree add'. TDD per AC. After
all ACs are green, ATTEMPT to run the artifact and record execution_verified honestly (never skip).
Then PUSH the feature branch to origin and write 'git diff origin/dev..HEAD' to a file in the ticket
folder; return its path as diff_artifact and set pushed=true. ${decisionsNote}`,
    { schema: IMPLEMENT_SCHEMA, label: 'implement', phase: 'Implement', isolation: 'worktree' })
  if (!impl) return { status: 'HALT_AGENT_SKIPPED', phase: 'Implement', ticket }
  rec('implement', impl)
  if (impl.status === 'stuck') return { status: 'HALT_IMPLEMENT_STUCK', ticket, branch: impl.branch, impl }

  phase('Review')
  const review = await agent(`${readContract('5-review')}
You did NOT write this code and have no design context. The runtime gave you your own worktree: run
'git fetch origin ${impl.branch}' then 'git checkout ${impl.branch}'. Review only 'git diff
origin/dev..HEAD' against the ACs and the repo CLAUDE.md. Find bugs that reach users; for each, write a
test and run it; retract if it passes. Diff artifact (backup): ${impl.diff_artifact}.`,
    { schema: REVIEW_SCHEMA, label: 'review', phase: 'Review', isolation: 'worktree' })
  if (!review) return { status: 'HALT_AGENT_SKIPPED', phase: 'Review', ticket, branch: impl.branch }
  rec('review', review, 'criticals:' + review.criticals_open)
  if (review.criticals_open > 0) return { status: 'BLOCKED_REVIEW_CRITICAL', ticket, branch: impl.branch, review, impl }

  phase('QA')
  const qa = await agent(`${readContract('6-qa')}
You did NOT write this code or its plan. The runtime gave you your own worktree: run 'git fetch origin
${impl.branch}' then 'git checkout ${impl.branch}'. Prove each AC with concrete evidence (code_ref + a
passing test_ref; for runnable behaviour, run it). Return raw verdicts; do NOT self-assign the level.`,
    { schema: QA_SCHEMA, label: 'qa', phase: 'QA', isolation: 'worktree' })
  if (!qa) return { status: 'HALT_AGENT_SKIPPED', phase: 'QA', ticket, branch: impl.branch }
  rec('qa', qa, qa.raw_overall)

  const qaCapped = capQaVerdict(impl.execution_verified, evidenceCappedOverall(qa))
  const blockers = preShipBlockers(impl, review, qaCapped)
  if (blockers.length) return { status: 'HALT_PRESHIP', ticket, branch: impl.branch, blockers, qa_capped: qaCapped, impl, review, qa }

  phase('ShipPrep')
  const shipPrep = await agent(`${readContract('7-ship')}
The runtime gave you your own worktree: 'git fetch origin ${impl.branch}' then 'git checkout
${impl.branch}'. Version bump + CHANGELOG, commit, push the branch with git. Do NOT invoke /klever-mr,
/post-comment, or any Jira transition — the main loop does those. Return branch, version, pushed=true.`,
    { schema: SHIPPREP_SCHEMA, label: 'ship-prep', phase: 'ShipPrep', isolation: 'worktree' })
  if (!shipPrep) return { status: 'HALT_AGENT_SKIPPED', phase: 'ShipPrep', ticket, branch: impl.branch }
  rec('ship-prep', shipPrep)
  if (shipPrep.status === 'stuck' || shipPrep.pushed !== true) {
    return { status: 'HALT_SHIPPREP_FAILED', ticket, branch: impl.branch, shipPrep, impl, review, qa }
  }

  return {
    status: 'READY_TO_SHIP', ticket, branch: shipPrep.branch, version: shipPrep.version,
    execution_verified: impl.execution_verified, qa_capped: qaCapped, ticket_folder: _tf,
    next_steps_for_main_loop: [
      'Invoke /klever-mr (no auto-merge) for branch ' + shipPrep.branch,
      'Invoke /post-comment for the Jira comment (MR link + AC summary + QA evidence)',
      'Transition the ticket to In Review/Testing (ceiling)',
      'After the human merges: run contract 8 (validate) as a post-merge step',
    ],
    phases: { concierge, design, grill, impl, review, qa, shipPrep },
  }
}

// =================== RUN + RETRO ===================

const result = await runPipeline()

// AWAITING_HUMAN is a pause (will resume), not an end — no retro yet.
if (result.status === 'AWAITING_HUMAN') return result

// Every other terminal state (success OR halt/block) gets instrumented.
phase('Retro')
const runEval = await agent(
  `Read ${CONTRACTS}/9-retro.md and execute it for ticket ${ticket}.
Terminal status: ${result.status}. Ticket folder: ${_tf || '(unresolved)'}.
Per-phase trace (JSON, includes each phase's soft confidence): ${JSON.stringify(trace)}.
Score the run, list red flags, propose concrete next-run improvements, and WRITE both the telemetry
YAML (to ${RUNS}/) and the next-run improvement handoff exactly as the contract specifies. Return the
paths you wrote as telemetry_written and handoff_written.`,
  { schema: RETRO_SCHEMA, label: 'retro', phase: 'Retro' }
)

return { ...result, eval: runEval || null, trace }

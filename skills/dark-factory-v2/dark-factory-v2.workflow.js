export const meta = {
  name: 'dark-factory-v2',
  description: 'Ticket-to-dev factory v2 (seed). Deterministic Workflow orchestration, work-type-agnostic: the concierge proposes a tool belt from the crib and the build + tester sockets equip it. Gates are JS code, not prose, so no phase can be skipped or self-certified past. Human concierge gate at the front. Every phase returns a soft confidence (0-100). A final Retro phase scores the run, captures red flags, and writes telemetry + a next-run improvement handoff. Terminal state READY_TO_SHIP: the workflow does code work + pushes the branch; the main loop runs the MR + Jira + post-merge validate.',
  phases: [
    { title: 'Concierge', detail: 'analyze + context + prereqs; surface decisions for the human' },
    { title: 'Design',    detail: 'tactical impl plan + test specs' },
    { title: 'Grill',     detail: 'interrogate the plan against the codebase' },
    { title: 'Implement', detail: 'TDD per AC in a worktree; attempt execution; push branch' },
    { title: 'Review',    detail: 'fresh adversarial agent in its own worktree on the pushed branch' },
    { title: 'Fix',       detail: 'bounded loop: on a CRITICAL, targeted fix + re-review (max 2 rounds) before halting' },
    { title: 'QA',        detail: 'fresh agent proves each AC; verdict capped by execution_verified + evidence' },
    { title: 'ShipPrep',  detail: 'version bump + CHANGELOG + commit + push (no MR/Jira)' },
    { title: 'Retro',     detail: 'score the run, capture red flags, write telemetry + improvement handoff' },
  ],
}

// ---------------------------------------------------------------------------
// Seed scope: single-pass review + QA, like-for-like with v1. Work-type tooling comes from a tool
// belt the concierge selects from the crib (no stack baked into the spine or shared contracts).
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
const TOOLCRIB = '/Users/gabrielamyot/.claude/skills/dark-factory-v2/toolcrib'
const SUPPORTED_BELTS = ['java', 'scripting'] // tool belts racked in the crib; concierge proposes one

const ticket = (args && args.ticket) || null
const org = (args && args.org) || 'klever'
const humanDecisions = (args && args.humanDecisions) || null
if (!ticket) throw new Error('dark-factory-v2 requires args.ticket (e.g. "ABC-123")')

// ---- Schemas (handoffs are validated objects, not parsed text) ----

const CONCIERGE_SCHEMA = {
  type: 'object',
  required: ['spec_quality', 'needs_human', 'ac_count', 'repos', 'prereqs_ok', 'open_questions', 'ticket_folder', 'tool_belt', 'summary'],
  properties: {
    spec_quality: { type: 'string', enum: ['PASS', 'FAIL'] },
    needs_human: { type: 'boolean' },
    ac_count: { type: 'integer', minimum: 0 },
    repos: { type: 'array', items: { type: 'string' } },
    prereqs_ok: { type: 'boolean' },
    ticket_folder: { type: 'string', minLength: 1 },
    tool_belt: { type: 'string' }, // proposed belt id from the crib; unknown id => unsupported halt
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
let _belt = null
const readContract = (name) =>
  `Read ${CONTRACTS}/${name}.md and execute it exactly for ticket ${ticket} (org: ${org}). Ticket folder (absolute): ${_tf || '(resolved by concierge)'}. Tool belt for this run: ${_belt || '(proposed by concierge)'} — equip it from ${TOOLCRIB}/${_belt || '<belt>'}.md (read it for the build / execute-verify / proof tooling; do NOT assume a stack).${CONFIDENCE_BLURB}`

// Trace of phase outcomes for the Retro phase.
const trace = []
const rec = (name, r, extra) => { trace.push({ phase: name, status: (r && (r.status || r.spec_quality)) || extra || '?', confidence: r ? r.confidence : null }); return r }

// =================== PIPELINE ===================

async function runPipeline() {
  phase('Concierge')
  log(`Dark Factory v2 (seed) — ${ticket}`)
  // Resume path (ADR-003 / 0.5.0 #6): when a human supplied decisions, fold them into the concierge
  // prompt. This (a) busts the resume cache so the concierge RE-RUNS instead of replaying its stale
  // needs_human verdict, and (b) forces a LIVE re-read of the ticket where the human may have resolved
  // an open_question. Without this, resumeFromRunId replays the byte-identical prompt -> cached verdict
  // -> BLOCKED_NEEDS_HUMAN_AGAIN even though the blocker was answered.
  const resumeNote = humanDecisions
    ? `\n\nRESUME CONTEXT: a human supplied decisions/answers since the prior run: ${JSON.stringify(humanDecisions)}. Re-read the ticket LIVE now (the human may also have resolved an open_question in the ticket itself) and incorporate these answers. Only set needs_human=true if a NEW, still-unresolved blocker remains — do NOT re-raise a question these answers resolve.`
    : ''
  const concierge = await agent(
    `Read ${CONTRACTS}/1-concierge.md and execute it for ticket ${ticket} (org: ${org}).
You are the concierge: validate spec quality, gather context, extract ACs, check prerequisites, and
RESOLVE the absolute ticket-folder path (return it as ticket_folder). This is the front gate. If
anything needs a human decision (ambiguous spec, missing/unknown repo or stack, a greenfield infra
choice, an unmet prerequisite), set needs_human=true and list each as a specific open_question.
Do NOT guess past these.
Also CLASSIFY the work-type and PROPOSE a tool_belt: read the tool crib at ${TOOLCRIB}/ (start with its
INDEX.md, then each belt file's "detect" rule) and return the id of the belt whose detect rule matches
this ticket's deliverable. If none match, return your best-guess label (the run halts as unsupported
rather than fake a proof — that means a new belt must be racked first).${resumeNote}${CONFIDENCE_BLURB}`,
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
      note: 'Answers were supplied AND the concierge re-ran live, yet a still-unresolved blocker remains (see decision_packet). This is a genuinely NEW/unanswered question, not a replayed verdict. Resolve it in the ticket and re-invoke with the additional answer, or run fresh.' }
  }

  _tf = concierge.ticket_folder
  _belt = concierge.tool_belt
  // Honest halt: no tool belt racked for this work-type. Rack one in toolcrib/ before running.
  if (!SUPPORTED_BELTS.includes(_belt)) {
    return { status: 'BLOCKED_UNSUPPORTED_FLOOR', ticket, tool_belt: _belt, ticket_folder: _tf, concierge,
      note: `No tool belt for work-type "${_belt}". Supported: ${SUPPORTED_BELTS.join(', ')}. Rack a belt in toolcrib/ (and confirm with the human) before running this ticket.` }
  }
  log(`Tool belt: ${_belt}`)
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

  // Review prompt reused across the bounded fix loop (each round is a fresh, segregated reviewer).
  const reviewPrompt = `${readContract('5-review')}
You did NOT write this code and have no design context. The runtime gave you your own worktree: run
'git fetch origin ${impl.branch}' then 'git checkout ${impl.branch}'. Review only 'git diff
origin/dev..HEAD' against the ACs and the repo CLAUDE.md. Find bugs that reach users; for each, write a
test and run it; retract if it passes. Diff artifact (backup): ${impl.diff_artifact}.`

  phase('Review')
  let review = await agent(reviewPrompt, { schema: REVIEW_SCHEMA, label: 'review', phase: 'Review', isolation: 'worktree' })
  if (!review) return { status: 'HALT_AGENT_SKIPPED', phase: 'Review', ticket, branch: impl.branch }
  rec('review', review, 'criticals:' + review.criticals_open)

  // Bounded fix loop (0.6.0): on a CRITICAL, bounce back to a targeted fix + re-review instead of
  // halting on the first pass. Harvested from v1's Quinn-attacks/Amelia-fixes loop and sprint-crawl's
  // review->implement revert. Bounded so a persistent critical still HALTs rather than looping forever.
  const MAX_FIX_ROUNDS = 2
  let fixRounds = 0
  while (review.criticals_open > 0 && fixRounds < MAX_FIX_ROUNDS) {
    fixRounds++
    const criticals = (review.findings || []).filter((f) => f.severity === 'CRITICAL')
    phase('Fix')
    const fix = await agent(`${readContract('4-implement')}
FIX MODE (round ${fixRounds}/${MAX_FIX_ROUNDS}). You are addressing ONLY the open CRITICAL review findings
below — do NOT add scope, refactor unrelated code, or touch ACs that already pass. The runtime gave you
your own worktree: 'git fetch origin ${impl.branch}' then 'git checkout ${impl.branch}'. For each finding:
write/keep a test that demonstrates the bug, fix the code minimally, re-run the affected tests, then PUSH
the branch. Return execution_verified honestly and pushed=true.
OPEN CRITICAL FINDINGS: ${JSON.stringify(criticals)}`,
      { schema: IMPLEMENT_SCHEMA, label: `fix-round-${fixRounds}`, phase: 'Fix', isolation: 'worktree' })
    if (!fix) return { status: 'HALT_AGENT_SKIPPED', phase: 'Fix', ticket, branch: impl.branch }
    rec(`fix-${fixRounds}`, fix)
    if (fix.pushed !== true) return { status: 'HALT_FIX_NOT_PUSHED', ticket, branch: impl.branch, fix, review }

    phase('Review')
    review = await agent(reviewPrompt, { schema: REVIEW_SCHEMA, label: `review-r${fixRounds + 1}`, phase: 'Review', isolation: 'worktree' })
    if (!review) return { status: 'HALT_AGENT_SKIPPED', phase: 'Review', ticket, branch: impl.branch }
    rec(`review-${fixRounds + 1}`, review, 'criticals:' + review.criticals_open)
  }
  if (review.criticals_open > 0) return { status: 'BLOCKED_REVIEW_CRITICAL', ticket, branch: impl.branch, review, impl, fix_rounds: fixRounds }

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

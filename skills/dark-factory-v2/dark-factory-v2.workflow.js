export const meta = {
  name: 'dark-factory-v2',
  description: 'Ticket-to-dev factory v2 (seed). Deterministic Workflow orchestration of the backend/Java floor. Gates are JS code, not prose, so no phase can be skipped or self-certified past. Human concierge gate at the front via two-stage split. Terminal state READY_TO_SHIP: the workflow does code work + pushes the branch; the main loop runs the MR + Jira (skills) and post-merge validate. Ticket-agnostic.',
  phases: [
    { title: 'Concierge', detail: 'analyze + context + prereqs; surface decisions for the human' },
    { title: 'Design',    detail: 'tactical impl plan + test specs' },
    { title: 'Grill',     detail: 'interrogate the plan against the codebase' },
    { title: 'Implement', detail: 'TDD per AC in a worktree; attempt execution; push branch' },
    { title: 'Review',    detail: 'fresh adversarial agent in its own worktree on the pushed branch' },
    { title: 'QA',        detail: 'fresh agent proves each AC; verdict capped by execution_verified + evidence' },
    { title: 'ShipPrep',  detail: 'version bump + CHANGELOG + commit + push (no MR/Jira — main loop does those)' },
  ],
}

// ---------------------------------------------------------------------------
// Seed scope: ONE floor (backend/Java), single-pass review + QA, like-for-like
// with v1. Built BLIND to any specific ticket: the ticket is a black-box arg.
//
// Verified Workflow-API constraints driving this design (claude-code-guide, 2026-06-02):
//  - Skills (/klever-mr, /post-comment) are NOT safely callable inside a workflow
//    agent -> Ship here is code-prep only; the MAIN LOOP runs MR + Jira + validate.
//  - A later agent cannot see an earlier agent's worktree unless the branch is pushed
//    -> Implement PUSHES the feature branch; Review/QA/ShipPrep run with
//    isolation:'worktree' and fetch+checkout that branch.
//  - No built-in loop guard -> explicit resume guard on the human gate.
//  - No native wait primitive -> Validate is NOT in this workflow; the main loop
//    runs it post-merge.
//
// The MUSCLE (per-phase reasoning) lives in contracts/*.md. Each phase agent reads
// its contract and executes it. This file is only the SKELETON: order + gates.
// ---------------------------------------------------------------------------

const CONTRACTS = '/Users/gabrielamyot/.claude/skills/dark-factory-v2/contracts' // absolute: '~' may not expand inside an agent prompt

// args: { ticket: 'KTP-XXX', org: 'klever', humanDecisions?: {<id>: <answer>} }
const ticket = (args && args.ticket) || null
const org = (args && args.org) || 'klever'
const humanDecisions = (args && args.humanDecisions) || null
if (!ticket) throw new Error('dark-factory-v2 requires args.ticket (e.g. "KTP-728")')

// ---- Schemas: phase handoffs are validated objects, not parsed free text ----

const CONCIERGE_SCHEMA = {
  type: 'object',
  required: ['spec_quality', 'needs_human', 'ac_count', 'repos', 'prereqs_ok', 'open_questions', 'ticket_folder', 'summary'],
  properties: {
    spec_quality: { type: 'string', enum: ['PASS', 'FAIL'] },
    needs_human: { type: 'boolean' },
    ac_count: { type: 'integer', minimum: 0 },
    repos: { type: 'array', items: { type: 'string' } },
    prereqs_ok: { type: 'boolean' },
    ticket_folder: { type: 'string', minLength: 1 }, // absolute path; downstream agents read/write artifacts here
    open_questions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'question', 'why_blocking'],
        properties: {
          id: { type: 'string' },
          question: { type: 'string' },
          why_blocking: { type: 'string' },
          options: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    summary: { type: 'string' },
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
  },
}

const IMPLEMENT_SCHEMA = {
  type: 'object',
  required: ['status', 'execution_verified', 'ac_progress', 'branch', 'pushed', 'diff_artifact'],
  properties: {
    status: { type: 'string', enum: ['pass', 'partial', 'stuck'] },
    // "true" | "infra_blocked(reason)" | "not_applicable(reason)" | "false"
    execution_verified: { type: 'string', pattern: '^(true|false|infra_blocked\\(.*\\)|not_applicable\\(.*\\))$' },
    ac_progress: { type: 'object' },
    branch: { type: 'string', minLength: 1 },
    pushed: { type: 'boolean' }, // did the feature branch get pushed to origin?
    diff_artifact: { type: 'string' }, // absolute path to the written diff (backup channel for review/qa)
    summary: { type: 'string' },
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
          title: { type: 'string' },
          file: { type: 'string' },
          demonstrated: { type: 'boolean' }, // true iff a test was written, run, and FAILED
        },
      },
    },
    summary: { type: 'string' },
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
          ac: { type: 'string' },
          verdict: { type: 'string', enum: ['PASS', 'PARTIAL', 'FAIL'] },
          code_ref: { type: 'string' },
          test_ref: { type: 'string' },
        },
      },
    },
    summary: { type: 'string' },
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
  },
}

// ---- Gates: deterministic JS. The agent cannot reason past these. ----

function capQaVerdict(execVerified, rawOverall) {
  const v = String(execVerified)
  if (v === 'true') return rawOverall
  if (v.indexOf('not_applicable') === 0) return rawOverall
  if (v.indexOf('infra_blocked') === 0) return 'PARTIAL' // cannot exceed PARTIAL
  if (v !== 'false') log(`WARN: unrecognised execution_verified="${v}" -> capping QA to INCOMPLETE`)
  return 'INCOMPLETE' // false or unrecognised: cannot exceed INCOMPLETE
}

// "Code review alone is NEVER a PASS": a PASS AC with no code_ref+test_ref is unsupported.
function evidenceCappedOverall(qa) {
  const unsupported = (qa.per_ac || []).some((a) => a.verdict === 'PASS' && (!a.code_ref || !a.test_ref))
  if (qa.raw_overall === 'ALL_PASS' && unsupported) {
    log('WARN: a PASS AC lacks code_ref/test_ref -> capping QA to PARTIAL (code review is not evidence of function)')
    return 'PARTIAL'
  }
  return qa.raw_overall
}

function executionOk(ev) {
  const v = String(ev)
  return v === 'true' || v.indexOf('not_applicable') === 0
}

function preShipBlockers(impl, review, qaCapped) {
  const blockers = []
  if (!impl || !executionOk(impl.execution_verified))
    blockers.push(`execution not verified (${impl ? impl.execution_verified : 'no impl'})`)
  if (!impl || impl.pushed !== true) blockers.push('feature branch was not pushed (review/QA could not see the code)')
  if (!review) blockers.push('no review artifact')
  else if (review.criticals_open > 0) blockers.push(`${review.criticals_open} open CRITICAL finding(s)`)
  if (qaCapped !== 'ALL_PASS') blockers.push(`QA verdict is ${qaCapped}, not ALL_PASS`)
  return blockers
}

const readContract = (name) =>
  `Read ${CONTRACTS}/${name}.md and execute it exactly for ticket ${ticket} (org: ${org}). Ticket folder (absolute): ${ticketFolderRef()}.`

let _tf = null
function ticketFolderRef() {
  return _tf || '(resolved by concierge — see concierge.ticket_folder)'
}

// =================== ORCHESTRATION ===================

phase('Concierge')
log(`Dark Factory v2 (seed) — ${ticket}`)
const concierge = await agent(
  `Read ${CONTRACTS}/1-concierge.md and execute it for ticket ${ticket} (org: ${org}).
You are the concierge: validate spec quality, gather context, extract ACs, check prerequisites, and
RESOLVE the absolute ticket-folder path (return it as ticket_folder). This is the front gate. If
anything needs a human decision (ambiguous spec, missing/unknown repo or stack, a greenfield infra
choice, an unmet prerequisite), set needs_human=true and list each as a specific open_question with
why it blocks. Do NOT guess past these.`,
  { schema: CONCIERGE_SCHEMA, label: 'concierge', phase: 'Concierge' }
)
if (!concierge) return { status: 'HALT_AGENT_SKIPPED', phase: 'Concierge', ticket }

// Gate: spec quality (un-skippable)
if (concierge.spec_quality === 'FAIL') {
  return { status: 'BLOCKED_SPEC_QUALITY', ticket, concierge }
}

// Front human gate (two-stage split) + resume loop guard.
if (concierge.needs_human && !humanDecisions) {
  log(`Concierge needs ${concierge.open_questions.length} human decision(s) before Design.`)
  return {
    status: 'AWAITING_HUMAN',
    ticket,
    decision_packet: concierge.open_questions,
    concierge,
    resume_hint: 'Re-invoke Workflow with resumeFromRunId and args.humanDecisions = {<id>: <answer>}',
  }
}
if (concierge.needs_human && humanDecisions) {
  // Decisions were provided but the concierge still reports it needs a human. Do NOT loop.
  return {
    status: 'BLOCKED_NEEDS_HUMAN_AGAIN',
    ticket,
    decision_packet: concierge.open_questions,
    concierge,
    note: 'Human decisions were supplied but concierge still needs_human. Refine the answers or the spec; not re-looping automatically.',
  }
}

_tf = concierge.ticket_folder
const decisions = humanDecisions || {}
const decisionsNote = Object.keys(decisions).length
  ? `Human decisions to honor (apply these in your work): ${JSON.stringify(decisions)}`
  : 'No human decisions were required.'

phase('Design')
const design = await agent(`${readContract('2-design')}\n${decisionsNote}`,
  { schema: PHASE_SCHEMA, label: 'design', phase: 'Design' })
if (!design) return { status: 'HALT_AGENT_SKIPPED', phase: 'Design', ticket }
if (design.status === 'stuck') return { status: 'HALT_DESIGN_STUCK', ticket, design }

phase('Grill')
const grill = await agent(`${readContract('3-grill')}\nInterrogate the design plan against the actual codebase (use git, not just local files). ${decisionsNote}`,
  { schema: PHASE_SCHEMA, label: 'grill', phase: 'Grill' })
if (!grill) return { status: 'HALT_AGENT_SKIPPED', phase: 'Grill', ticket }
if (grill.status === 'stuck') return { status: 'HALT_GRILL_UNWORKABLE', ticket, design, grill }

phase('Implement')
const impl = await agent(`${readContract('4-implement')}
The Workflow runtime has given you your OWN git worktree — do NOT run 'git worktree add'. TDD per AC.
After all ACs are green, ATTEMPT to run the artifact and record execution_verified honestly
(true | infra_blocked(reason) | not_applicable(reason) | false) — never skip the attempt. Then PUSH
the feature branch to origin (so Review/QA can see it) and write 'git diff origin/dev..HEAD' to a
file in the ticket folder; return its path as diff_artifact and set pushed=true. ${decisionsNote}`,
  { schema: IMPLEMENT_SCHEMA, label: 'implement', phase: 'Implement', isolation: 'worktree' })
if (!impl) return { status: 'HALT_AGENT_SKIPPED', phase: 'Implement', ticket }
if (impl.status === 'stuck') return { status: 'HALT_IMPLEMENT_STUCK', ticket, branch: impl.branch, impl }

phase('Review')
// Fresh agent, own worktree, no implementation context (segregation).
const review = await agent(`${readContract('5-review')}
You did NOT write this code and have no design context. The Workflow runtime gave you your own
worktree: run 'git fetch origin ${impl.branch}' then 'git checkout ${impl.branch}'. Review only the
diff 'git diff origin/dev..HEAD' against the acceptance criteria and the repo CLAUDE.md. Find bugs
that reach users; for each, write a test and run it; retract if it passes. Diff artifact (backup):
${impl.diff_artifact}.`,
  { schema: REVIEW_SCHEMA, label: 'review', phase: 'Review', isolation: 'worktree' })
if (!review) return { status: 'HALT_AGENT_SKIPPED', phase: 'Review', ticket, branch: impl.branch }

// Gate: zero open CRITICALs before QA
if (review.criticals_open > 0) {
  return { status: 'BLOCKED_REVIEW_CRITICAL', ticket, branch: impl.branch, review, impl }
}

phase('QA')
const qa = await agent(`${readContract('6-qa')}
You did NOT write this code or its plan. The Workflow runtime gave you your own worktree: run
'git fetch origin ${impl.branch}' then 'git checkout ${impl.branch}'. Prove each AC with concrete
evidence (code_ref + a passing test_ref; for runnable behaviour, run it). Return raw verdicts; do
NOT self-assign the verification level.`,
  { schema: QA_SCHEMA, label: 'qa', phase: 'QA', isolation: 'worktree' })
if (!qa) return { status: 'HALT_AGENT_SKIPPED', phase: 'QA', ticket, branch: impl.branch }

// Gate: evidence cap, then execution-verified cap (JS clamps; agent cannot override)
const qaEvidence = evidenceCappedOverall(qa)
const qaCapped = capQaVerdict(impl.execution_verified, qaEvidence)

// Gate: pre-ship blockers (JS). Halts before any ship action.
const blockers = preShipBlockers(impl, review, qaCapped)
if (blockers.length) {
  return { status: 'HALT_PRESHIP', ticket, branch: impl.branch, blockers, qa_capped: qaCapped, impl, review, qa }
}

phase('ShipPrep')
// Code-prep only: version bump + CHANGELOG + commit + push. NO MR, NO Jira (skills unsafe in-agent).
const shipPrep = await agent(`${readContract('7-ship')}
The Workflow runtime gave you your own worktree: 'git fetch origin ${impl.branch}' then
'git checkout ${impl.branch}'. Do version bump + CHANGELOG, commit, and push the branch with git.
Do NOT invoke /klever-mr, /post-comment, or any Jira transition — the main loop does those. Return
the branch, the new version, and pushed=true.`,
  { schema: SHIPPREP_SCHEMA, label: 'ship-prep', phase: 'ShipPrep', isolation: 'worktree' })
if (!shipPrep) return { status: 'HALT_AGENT_SKIPPED', phase: 'ShipPrep', ticket, branch: impl.branch }
if (shipPrep.status === 'stuck' || shipPrep.pushed !== true) {
  return { status: 'HALT_SHIPPREP_FAILED', ticket, branch: impl.branch, shipPrep, impl, review, qa }
}

// Terminal: code is done, reviewed, QA'd, version-bumped, pushed. Main loop creates the MR + Jira,
// then runs post-merge validate (contract 8) once the human merges.
return {
  status: 'READY_TO_SHIP',
  ticket,
  branch: shipPrep.branch,
  version: shipPrep.version,
  execution_verified: impl.execution_verified,
  qa_capped: qaCapped,
  ticket_folder: _tf,
  next_steps_for_main_loop: [
    'Invoke /klever-mr (no auto-merge) to create the MR for branch ' + shipPrep.branch,
    'Invoke /post-comment to post the Jira comment (MR link + AC summary + QA evidence)',
    'Transition the ticket to In Review/Testing (ceiling)',
    'After the human merges: run contract 8 (validate) as a post-merge step',
  ],
  phases: { concierge, design, grill, impl, review, qa, shipPrep },
}

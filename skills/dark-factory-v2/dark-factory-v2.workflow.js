export const meta = {
  name: 'dark-factory-v2',
  description: 'Ticket-to-dev factory v2 (seed). Deterministic Workflow orchestration of the backend/Java floor. Gates are JS code, not prose, so no phase can be skipped or self-certified past. Human concierge gate at the front via two-stage split. Ticket-agnostic: any backend/Java ticket in, mergeable MR out.',
  phases: [
    { title: 'Concierge', detail: 'analyze + context + prereqs; surface decisions for the human' },
    { title: 'Design',    detail: 'tactical impl plan + test specs' },
    { title: 'Grill',     detail: 'interrogate the plan against the codebase' },
    { title: 'Implement', detail: 'TDD per AC, in a worktree; attempt execution' },
    { title: 'Review',    detail: 'fresh adversarial agent, diff + ACs only' },
    { title: 'QA',        detail: 'fresh agent proves each AC; verdict capped by execution_verified' },
    { title: 'Ship',      detail: 'pre-ship gate, then MR + Jira (human merges)' },
    { title: 'Validate',  detail: 'post-merge dev check / human gate for frontend' },
  ],
}

// ---------------------------------------------------------------------------
// Seed scope: ONE floor (backend/Java), single-pass review + QA, like-for-like
// with v1. No rigor (blind-impl, deliberation, multi-gate, model diversity) —
// those are roadmap R1-R3. Built BLIND to any specific ticket: the ticket is a
// black-box arg. If a conditional ever names a ticket, that is overfitting.
//
// The MUSCLE (per-phase reasoning) lives in contracts/*.md, harvested from v1's
// proven backend phases. Each phase agent reads its contract and executes it.
// This file is only the SKELETON: order, gates, the human-gate split.
// ---------------------------------------------------------------------------

const CONTRACTS = '~/.claude/skills/dark-factory-v2/contracts'

// args: { ticket: 'KTP-XXX', org: 'klever', humanDecisions?: {...}, ticketFolder?: '...' }
const ticket = (args && args.ticket) || null
const org = (args && args.org) || 'klever'
const humanDecisions = (args && args.humanDecisions) || null
if (!ticket) throw new Error('dark-factory-v2 requires args.ticket (e.g. "KTP-728")')

// ---- Schemas: phase handoffs are validated objects, not parsed free text ----

const CONCIERGE_SCHEMA = {
  type: 'object',
  required: ['spec_quality', 'needs_human', 'ac_count', 'prereqs_ok', 'open_questions', 'summary'],
  properties: {
    spec_quality: { type: 'string', enum: ['PASS', 'FAIL'] },
    needs_human: { type: 'boolean' },
    ac_count: { type: 'integer' },
    repos: { type: 'array', items: { type: 'string' } },
    prereqs_ok: { type: 'boolean' },
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
  required: ['status', 'execution_verified', 'ac_progress', 'branch'],
  properties: {
    status: { type: 'string', enum: ['pass', 'partial', 'stuck'] },
    // true | "infra_blocked(reason)" | "not_applicable(reason)" | "false"
    execution_verified: { type: 'string' },
    ac_progress: { type: 'object' },
    branch: { type: 'string' },
    summary: { type: 'string' },
  },
}

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['criticals_open', 'findings'],
  properties: {
    criticals_open: { type: 'integer' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'title', 'demonstrated'],
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] },
          title: { type: 'string' },
          file: { type: 'string' },
          demonstrated: { type: 'boolean' }, // a test was written and it failed
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

// ---- Gates: deterministic JS. The agent cannot reason past these. ----

function capQaVerdict(execVerified, rawOverall) {
  const v = String(execVerified)
  if (execVerified === true || v === 'true') return rawOverall
  if (v.indexOf('not_applicable') === 0) return rawOverall
  if (v.indexOf('infra_blocked') === 0) return 'PARTIAL' // cannot exceed PARTIAL
  return 'INCOMPLETE' // false or missing: cannot exceed INCOMPLETE
}

function preShipBlockers(impl, review, qaCapped) {
  const blockers = []
  if (!impl || !impl.execution_verified || String(impl.execution_verified) === 'false')
    blockers.push('execution not verified (Phase 4 step 5)')
  if (!review) blockers.push('no review artifact')
  else if (review.criticals_open > 0) blockers.push(`${review.criticals_open} open CRITICAL finding(s)`)
  if (qaCapped !== 'ALL_PASS') blockers.push(`QA verdict is ${qaCapped}, not ALL_PASS`)
  return blockers
}

// ---- Per-phase prompts: each agent reads its contract and executes it. ----

const readContract = (name) => `Read ${CONTRACTS}/${name}.md and execute it exactly for ticket ${ticket} (org: ${org}).`

// =================== ORCHESTRATION ===================

phase('Concierge')
log(`Dark Factory v2 (seed) — ${ticket}`)
const concierge = await agent(
  `${readContract('1-concierge')}
You are the concierge: validate spec quality, gather context, extract ACs, and check prerequisites.
This is the front gate. If anything requires a human decision (ambiguous spec, missing/unknown repo
or stack, a greenfield infra choice, an unmet prerequisite), set needs_human=true and list each as a
specific open_question with why it blocks. Do NOT guess past these.`,
  { schema: CONCIERGE_SCHEMA, label: 'concierge', phase: 'Concierge' }
)

// Gate: spec quality (JS, un-skippable)
if (concierge.spec_quality === 'FAIL') {
  return { status: 'BLOCKED_SPEC_QUALITY', ticket, concierge }
}

// Front human gate (two-stage split): if a human decision is needed and we don't
// yet have answers, STOP and hand the decision packet back to the main loop.
// The main loop asks the user, then re-invokes with resumeFromRunId + args.humanDecisions
// (the concierge agent() above returns cached on resume, so this is cheap).
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
const decisions = humanDecisions || {}
const decisionsNote = Object.keys(decisions).length
  ? `Human decisions to honor: ${JSON.stringify(decisions)}`
  : 'No human decisions were required.'

const design = await agent(`${readContract('2-design')}\n${decisionsNote}`,
  { schema: PHASE_SCHEMA, label: 'design', phase: 'Design' })

phase('Grill')
const grill = await agent(`${readContract('3-grill')}\nInterrogate the design plan against the actual codebase (use git, not just local files). ${decisionsNote}`,
  { schema: PHASE_SCHEMA, label: 'grill', phase: 'Grill' })

phase('Implement')
const impl = await agent(`${readContract('4-implement')}\nTDD per AC in a worktree. After all ACs are green, ATTEMPT to run the artifact and record execution_verified honestly (true | infra_blocked(reason) | not_applicable(reason) | false). Never skip the attempt.`,
  { schema: IMPLEMENT_SCHEMA, label: 'implement', phase: 'Implement', isolation: 'worktree' })

phase('Review')
// Fresh agent, no implementation context (segregation): diff + ACs + repo conventions only.
const review = await agent(`${readContract('5-review')}\nYou did NOT write this code and have no design context. You receive only the diff (git diff origin/dev..HEAD in the worktree), the acceptance criteria, and the repo CLAUDE.md. Find bugs that reach users. For each finding, write a test and run it; retract if it passes. Branch: ${impl.branch}.`,
  { schema: REVIEW_SCHEMA, label: 'review', phase: 'Review' })

// Gate: zero open CRITICALs before QA
if (review.criticals_open > 0) {
  return { status: 'BLOCKED_REVIEW_CRITICAL', ticket, branch: impl.branch, review, impl }
}

phase('QA')
// Fresh agent, separate from implementor: AC list + file paths + tech table only.
const qa = await agent(`${readContract('6-qa')}\nYou did NOT write this code or its plan. Prove each AC with concrete evidence (code ref + passing test ref; for any runnable behavior, run it). Return raw verdicts; do not self-assign the verification level.`,
  { schema: QA_SCHEMA, label: 'qa', phase: 'QA' })

// Gate: verdict cap from execution_verified (JS clamps; agent cannot override)
const qaCapped = capQaVerdict(impl.execution_verified, qa.raw_overall)

// Gate: pre-ship artifact + quality gate (JS). Halts before any ship action.
const blockers = preShipBlockers(impl, review, qaCapped)
if (blockers.length) {
  return { status: 'HALT_PRESHIP', ticket, branch: impl.branch, blockers, qa_capped: qaCapped, impl, review, qa }
}

phase('Ship')
const ship = await agent(`${readContract('7-ship')}\nVersion bump + CHANGELOG, push branch ${impl.branch}, create the MR via /klever-mr (NO auto-merge), post the Jira comment via /post-comment, transition the ticket no higher than In Review/Testing.`,
  { schema: PHASE_SCHEMA, label: 'ship', phase: 'Ship' })

phase('Validate')
const validate = await agent(`${readContract('8-validate')}\nPost-merge dev verification. For backend: smoke the key endpoints once merged. If frontend or no automated check exists, return status:partial and flag a human gate.`,
  { schema: PHASE_SCHEMA, label: 'validate', phase: 'Validate' })

return {
  status: 'COMPLETE',
  ticket,
  branch: impl.branch,
  execution_verified: impl.execution_verified,
  qa_capped: qaCapped,
  phases: { concierge, design, grill, impl, review, qa, ship, validate },
}

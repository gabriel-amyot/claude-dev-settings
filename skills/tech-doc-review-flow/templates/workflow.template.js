// TEMPLATE — tech-doc-review-flow deterministic workflow.
// Fill the <FILL:...> constants for the target repo, then launch with the
// Workflow tool ({scriptPath}). Run-specific state (CACHED_ROUNDS, EXTRA_ROUNDS,
// VERIFY_RETRY, DIRECTIVES) starts empty; populate only when resuming a
// stranded run (see SKILL.md "Resume discipline").
export const meta = {
  name: 'tech-doc-review-flow',
  description: 'Three-pass editor + Codex-adversarial review of app-ttd-trading-mcp agent-os docs (KTP-1182)',
  phases: [
    { title: 'Setup', detail: 'gate on !18 merged, worktree from origin/dev, baseline suite' },
    { title: 'Pass 1 — Technical accuracy', detail: 'Winston+Amelia editor vs Codex counterpart, max 5 rounds' },
    { title: 'Pass 2 — Usability & clarity', detail: 'John (PM) + Leo lens vs Codex counterpart, max 5 rounds' },
    { title: 'Pass 3 — Editorial & style', detail: 'Paige editor vs Codex counterpart, max 5 rounds' },
    { title: 'Ship', detail: 'version bump, CHANGELOG, docs lint, freshness check, push' },
  ],
}

const REVIEW_FLOW = '<FILL: absolute path to the ticket review-flow folder holding charter, manifest, prompts, ledger, ast-guard>'
const REPO = '<FILL: absolute path to the target repo main checkout>'
const WORKTREE = REPO + '/.worktrees/KTP-1182-doc-review-flow'
const BRANCH = '<FILL: TICKET-doc-review-flow>'
const PREREQ_BRANCH = '<FILL: branch that must be merged into the base before this flow runs, or empty to skip the gate>'
const PREREQ_TIP = '<FILL: that branch tip sha, fallback for a deleted remote branch>'
const MAX_ROUNDS = 5

// Model tiering (Gabriel, 2026-09-11): workflow agents run on Opus, never the
// session-default model; the reviewer of record stays the Codex CLI inside the
// verifier agent. Rounds already completed by run wf_0307e084-fee keep their
// exact original opts so a resume replays them from cache instead of re-spending.
const CACHED_ROUNDS = {}  // rounds already completed by a prior run, per its journal
// Round-6 override (Gabriel, 2026-09-11): pass 1 exhausted its 5-round budget
// with 3 small Majors left; one extra round was authorized. Prompt text keeps
// "of max 5" for rounds 1-5 so the cache replays them byte-identically.
// Standing auth (Gabriel, 2026-09-11): after the round-6 exhaustion he
// authorized a directed round 7 AND continuation without asking while blocking
// findings keep SHRINKING round-over-round; a stall (count not smaller than the
// previous round) or the hard cap stops the pass for a human. Rounds 1-6 keep
// byte-identical prompts for the cache.
const EXTRA_ROUNDS = {}   // human-authorized rounds beyond MAX_ROUNDS, per pass
// Verify-retry markers: bump a pass-round key to cache-bust exactly that
// verifier call on resume. p1-6's first attempt could not run Codex (workspace
// out of credits, refilled 2026-09-11); the retry line below changes only that
// call's prompt so everything before it replays from cache.
const VERIFY_RETRY = {}   // bump 'pX-N': n to cache-bust exactly that verifier call
// Per-round editor directives, injected into that round's editor dispatch only.
const DIRECTIVES = {}     // per-round editor directives, 'pX-N': 'text'
function maxFor(passId) { return MAX_ROUNDS + (EXTRA_ROUNDS[passId] || 0) }
function maxShown(passId, round) { return round <= MAX_ROUNDS ? MAX_ROUNDS : maxFor(passId) }
// Editors do the substantive work: opus. Verifier wrappers only conduct the
// Codex CLI run and execute refutation commands: sonnet. Cached rounds keep
// empty opts so the resume replays them.
// Anti-bullshit auto-directive: when the same file carries blocking findings
// in two consecutive verdicts, the next editor is told to DEMOTE the refuted
// claim per charter rule 12 instead of rewording it. p1 starts at round 8 so
// rounds 1-7 replay from cache; fresh passes start at round 2. Skipped when a
// manual DIRECTIVES entry exists for the round.
function autoChurnFrom(passId) { return 2 }
function findingFiles(verdict) {
  const out = new Set()
  for (const f of (verdict && verdict.blockingFindings) || []) {
    for (const part of String(f.file || '').split(',')) {
      const s = part.trim()
      if (s) out.add(s)
    }
  }
  return out
}
function churnDirective(passId, round, prevVerdict, prevPrevVerdict) {
  if (round < autoChurnFrom(passId)) return ''
  if (!prevVerdict || !prevPrevVerdict) return ''
  const prev = findingFiles(prevVerdict)
  const repeats = [...findingFiles(prevPrevVerdict)].filter(f => prev.has(f))
  if (!repeats.length) return ''
  return `\n\nANTI-BULLSHIT DIRECTIVE (auto, charter rule 12): ${repeats.join(' and ')} carried blocking findings in the last two rounds. The claim, not the wording, is the defect. Do not reformulate: remove or demote each refuted absolute claim — name the enforcing mechanism by symbol, or state the best-effort truth and enumerate the exceptions by symbol.`
}

function tierOpts(passId, round, role) {
  if ((CACHED_ROUNDS[passId] || 0) >= round) return {}
  return { model: role === 'verifier' ? 'sonnet' : 'opus' }
}

const SETUP_SCHEMA = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    reason: { type: 'string' },
    reused: { type: 'boolean' },
    baseSha: { type: 'string' },
    passed: { type: 'integer' },
    skipped: { type: 'integer' },
  },
  required: ['ok'],
}

const EDITOR_SCHEMA = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    commits: { type: 'array', items: { type: 'string' } },
    gates: {
      type: 'object',
      properties: {
        astGuardOk: { type: 'boolean' },
        suiteOk: { type: 'boolean' },
        passed: { type: 'integer' },
        skipped: { type: 'integer' },
      },
      required: ['astGuardOk', 'suiteOk'],
    },
    changedThisRound: { type: 'string' },
    reportPath: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['ok', 'gates', 'changedThisRound'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    reviewer: { type: 'string', enum: ['codex', 'fallback-fable'] },
    critical: { type: 'integer' },
    major: { type: 'integer' },
    medium: { type: 'integer' },
    minor: { type: 'integer' },
    blockingFindings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string' },
          title: { type: 'string' },
          file: { type: 'string' },
        },
        required: ['severity', 'title'],
      },
    },
    readTest: {
      type: 'object',
      properties: { contractOk: { type: 'boolean' }, indexOk: { type: 'boolean' } },
    },
    verdictPath: { type: 'string' },
    summary: { type: 'string' },
  },
  required: ['reviewer', 'critical', 'major', 'medium', 'minor', 'blockingFindings'],
}

const SHIP_SCHEMA = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    reason: { type: 'string' },
    version: { type: 'string' },
    pushed: { type: 'boolean' },
    freshness: { type: 'integer' },
    brokenLinks: { type: 'integer' },
    commits: { type: 'array', items: { type: 'string' } },
  },
  required: ['ok'],
}

const SETUP_PROMPT = `You are the Setup agent of the tech-doc-review-flow workflow (<FILL: TICKET>, Klever org only).
Repo: ${REPO}. Run every git mutation unpiped so a failure is visible.

1. Run: git -C ${REPO} fetch origin  (must succeed).
2. MERGE GATE — the prerequisite MR must already be merged into origin/dev. Determine it:
   a. If origin/${PREREQ_BRANCH} exists: git -C ${REPO} merge-base --is-ancestor origin/${PREREQ_BRANCH} origin/dev
   b. If the remote branch is gone: git -C ${REPO} merge-base --is-ancestor ${PREREQ_TIP} origin/dev
   c. If that object is unknown: git -C ${REPO} log origin/dev --grep "${PREREQ_BRANCH}" --oneline -1 (non-empty means merged)
   Merged if ANY signal passes. If NOT merged: return ok=false with reason "the prerequisite MR (branch ${PREREQ_BRANCH}) is not merged into origin/dev yet. Gabriel merges !18 first; rerun this workflow afterwards." and do NOTHING else — no worktree, no edits.
3. WORKTREE at ${WORKTREE} on branch ${BRANCH}:
   - If it already exists: it must be on branch ${BRANCH} with clean status. Reuse it (reused=true). Never hard-reset, never delete. Any other state: return ok=false with a precise reason.
   - If absent and branch ${BRANCH} does not exist: git -C ${REPO} worktree add .worktrees/${BRANCH} -b ${BRANCH} origin/dev
   - If absent but branch ${BRANCH} exists from a prior run: add the worktree on the existing branch (no -b), reused=true.
4. baseSha: fresh branch = git -C ${REPO} rev-parse origin/dev. Reused branch = git -C ${REPO} merge-base ${BRANCH} origin/dev.
5. BASELINE: in ${WORKTREE} run: uv run pytest -q . Parse the final counts ("N passed", "M skipped"). Expected near 613 passed / 21 skipped; record the ACTUAL numbers. A failing suite at baseline is ok=false (reason includes the failure names).
6. LEDGER: in ${REVIEW_FLOW}/review-ledger.md replace the two "filled by Setup" placeholders with the base SHA and the actual baseline counts. Do not commit anything in project-management.
7. Return the structured result: ok, reused, baseSha, passed, skipped.`

function editorPrompt(p, round, setup, prevVerdict, churnNote) {
  const roundCtx = round === 1
    ? 'This is round 1: execute the full round-1 mission from the prompt file.'
    : `This is round ${round}. Blocking findings from the previous verdict (fix or reject-with-evidence each one):\n${JSON.stringify(prevVerdict.blockingFindings, null, 2)}\nFull verdict file: ${REVIEW_FLOW}/rounds/${p.id}-r${round - 1}-verdict.md`
  return `You are dispatched by the tech-doc-review-flow workflow (<FILL: TICKET>, Klever org only).
Read and follow EXACTLY the prompt file: ${REVIEW_FLOW}/${p.editorFile}

Dispatch values:
- REVIEW_FLOW = ${REVIEW_FLOW}
- WORKTREE = ${WORKTREE} (branch ${BRANCH})
- BASE_SHA = ${setup.baseSha}
- Setup baseline: ${setup.passed} passed / ${setup.skipped} skipped (uv run pytest -q)
- Pass: ${p.id}. Round: ${round} of max ${maxShown(p.id, round)}.
- Your round report file: ${REVIEW_FLOW}/rounds/${p.id}-r${round}-editor.md

${roundCtx}${DIRECTIVES[`${p.id}-${round}`] ? `\n\n${DIRECTIVES[`${p.id}-${round}`]}` : (churnNote || '')}

Return the structured result. gates.astGuardOk and gates.suiteOk must reflect gate runs you actually executed this round; report red honestly.`
}

function verifierPrompt(p, round, setup, editor) {
  return `You are dispatched by the tech-doc-review-flow workflow (<FILL: TICKET>, Klever org only).
Read and follow EXACTLY the prompt file: ${REVIEW_FLOW}/${p.verifierFile}

Dispatch values:
- REVIEW_FLOW = ${REVIEW_FLOW}
- WORKTREE = ${WORKTREE} (branch ${BRANCH})
- BASE_SHA = ${setup.baseSha}
- Setup baseline: ${setup.passed} passed / ${setup.skipped} skipped (uv run pytest -q)
- Pass: ${p.id}. Round: ${round} of max ${maxShown(p.id, round)}.
- What the editor changed this round: ${editor.changedThisRound}
- Editor commits this round: ${(editor.commits || []).join(', ') || 'see git log'}
- Editor round report: ${editor.reportPath || REVIEW_FLOW + '/rounds/' + p.id + '-r' + round + '-editor.md'}
- Your verdict file: ${REVIEW_FLOW}/rounds/${p.id}-r${round}-verdict.md${VERIFY_RETRY[`${p.id}-${round}`] ? `\n- Retry attempt ${VERIFY_RETRY[`${p.id}-${round}`] + 1}: the prior attempt could not run Codex (workspace out of credits, since refilled). Run it now per the SOP.` : ''}

Return the structured verdict. Counts must match your verdict file. blockingFindings lists every Critical and Major (empty array if none).`
}

function shipPrompt(setup) {
  return `You are the Ship agent of the tech-doc-review-flow workflow (<FILL: TICKET>, Klever org only).
Worktree: ${WORKTREE} on branch ${BRANCH}. Base: ${setup.baseSha}. Baseline: ${setup.passed} passed / ${setup.skipped} skipped.

1. FINAL GATES: python3 ${REVIEW_FLOW}/ast-guard.py --repo ${WORKTREE} --base ${setup.baseSha} ; then in the worktree: uv run pytest -q (counts must equal baseline). Any red: return ok=false with the output.
2. DOCS LINK LINT: verify every repo-relative markdown link in files under ${WORKTREE}/agent-os/ resolves to an existing file (throwaway checker in /tmp, never committed). Fix broken links (doc edits only), rerun until 0. Report brokenLinks as the final count.
3. VERSION: read [project] version in pyproject.toml on the branch; bump the patch. Follow the repo's own convention for packaging/manifest.json (it may single-source from pyproject — check before editing). Add a CHANGELOG.md entry: docs rewritten to contract/index standard plus comment/docstring sweep, zero behavior change. Dates are legal in CHANGELOG.
4. COMMIT: "<FILL: TICKET>: bump version to <v> and record the doc overhaul in the changelog" with a why-body.
5. FRESHNESS: git -C ${WORKTREE} fetch origin (unpiped). Then: git -C ${WORKTREE} rev-list --count HEAD..origin/dev — must be 0. If not 0: return ok=false, reason "origin/dev moved; do not rebase" (never rebase or merge).
6. PUSH (unpiped, mutation): git -C ${WORKTREE} push -u origin ${BRANCH} . Judge success from this command's own exit status only.
7. Do NOT create the MR (the main loop does). Never touch .gitlab-ci.yml. Never push any other branch. Never run GitLab pipelines.

Return: ok, version, pushed, freshness, brokenLinks, commits.`
}

phase('Setup')
const setup = await agent(SETUP_PROMPT, { schema: SETUP_SCHEMA, label: 'setup', phase: 'Setup' })
if (!setup) return { status: 'AGENT_DIED', at: 'setup' }
if (!setup.ok) return { status: 'BLOCKED_AT_SETUP', reason: setup.reason }
log(`Setup ok: base ${setup.baseSha ? setup.baseSha.slice(0, 8) : '?'}, baseline ${setup.passed}/${setup.skipped}, reused=${!!setup.reused}`)

const passes = [
  { id: 'p1', phase: 'Pass 1 — Technical accuracy', editorFile: 'p1-editor.md', verifierFile: 'p1-verifier.md' },
  { id: 'p2', phase: 'Pass 2 — Usability & clarity', editorFile: 'p2-editor.md', verifierFile: 'p2-verifier.md' },
  { id: 'p3', phase: 'Pass 3 — Editorial & style', editorFile: 'p3-editor.md', verifierFile: 'p3-verifier.md' },
]

const summary = []
for (const p of passes) {
  phase(p.phase)
  let clean = false
  let stalled = false
  let prevVerdict = null
  let prevPrevVerdict = null
  let roundsRun = 0
  for (let r = 1; r <= maxFor(p.id); r++) {
    roundsRun = r
    const editor = await agent(editorPrompt(p, r, setup, prevVerdict, churnDirective(p.id, r, prevVerdict, prevPrevVerdict)), { schema: EDITOR_SCHEMA, label: `${p.id}-r${r}-editor`, phase: p.phase, ...tierOpts(p.id, r, 'editor') })
    if (!editor) return { status: 'AGENT_DIED', at: `${p.id}-r${r}-editor`, summary }
    if (!editor.ok || !editor.gates.astGuardOk || !editor.gates.suiteOk) {
      return { status: 'GATES_RED', at: `${p.id}-r${r}-editor`, detail: editor, summary }
    }
    const verdict = await agent(verifierPrompt(p, r, setup, editor), { schema: VERDICT_SCHEMA, label: `${p.id}-r${r}-verifier`, phase: p.phase, ...tierOpts(p.id, r, 'verifier') })
    if (!verdict) return { status: 'AGENT_DIED', at: `${p.id}-r${r}-verifier`, summary }
    log(`${p.id} round ${r}: ${verdict.critical} critical, ${verdict.major} major, ${verdict.medium} medium, ${verdict.minor} minor (${verdict.reviewer})`)
    if (verdict.critical === 0 && verdict.major === 0) { prevPrevVerdict = prevVerdict; prevVerdict = verdict; clean = true; break }
    if (r > MAX_ROUNDS && prevVerdict && (verdict.critical + verdict.major) >= (prevVerdict.critical + prevVerdict.major)) {
      prevPrevVerdict = prevVerdict
      prevVerdict = verdict
      stalled = true
      break
    }
    prevPrevVerdict = prevVerdict
    prevVerdict = verdict
  }
  summary.push({ pass: p.id, clean, rounds: roundsRun })
  if (!clean) {
    return { status: stalled ? 'PASS_STALLED' : 'PASS_EXHAUSTED', at: p.id, blocking: prevVerdict ? prevVerdict.blockingFindings : [], summary }
  }
}

phase('Ship')
const ship = await agent(shipPrompt(setup), { schema: SHIP_SCHEMA, label: 'ship', phase: 'Ship', model: 'opus' })
if (!ship) return { status: 'AGENT_DIED', at: 'ship', summary }
if (!ship.ok) return { status: 'SHIP_BLOCKED', detail: ship, summary }
return {
  status: 'READY_FOR_MR',
  branch: BRANCH,
  baseSha: setup.baseSha,
  baseline: `${setup.passed} passed / ${setup.skipped} skipped`,
  ship,
  summary,
}
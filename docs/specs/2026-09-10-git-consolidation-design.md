# Git consolidation — one point of contact, behind a regression net

Status: DESIGN, not approved. Awaiting `/crit` review.
Author: session `warm-finch` (reopened 2026-09-10)
Origin: an IAP clone gotcha documented seven times and rediscovered an eighth.

## Goal

One place that owns every git rule in this harness, so a rule is stated once and
found once. Today the rules live on five surfaces and no surface owns them.

Gabriel's constraint, verbatim in intent: *"let's make sure we have evals to catch any
regression that we might be introducing right now into the harness."* The evals are the
gate, not the paperwork. Nothing gets consolidated until the current behaviour is pinned
and a Codex pass has tried to break the pins.

## What gets consolidated, and how

| Surface | Consolidate? | Why |
|---|---|---|
| Global `CLAUDE.md` git rules (8 rules, lines 45-99) | **Yes, by reference** | Keep a one-line trigger, move the body to `/git`. Always-loaded bytes are the scarce resource. |
| Project `CLAUDE.md` (single-trunk, commit/MR conventions) | **Yes, by reference** | Same. |
| `library/context/git-history-verification.md`, `worktree-fleet-ops.md` | **Yes, absorb or link** | Already on-demand; make `/git` the entry point. |
| 9 skills embedding git steps | **Yes, cite instead of restate** | `autonomous-ticket-ship`, `bmad-repo-onboarding`, `batch-pr-consolidation`, `crawl-adversarial-review-cascade`, `pr-review`, `klever-mr`, `sprint-factory`, `status-index`, `writing-claude-code-hooks` |
| 4 hooks | **No, keep as-is** | They are the enforcement layer and already have fixtures. `/git` documents them; they do not call it. |
| `superpowers:using-git-worktrees` | **Yes — migrate and own** | See below. Corrected 2026-09-10 after review: this was originally scoped as immovable, which mistook a policy choice for a technical limit. |

### Owning the worktree skill

The first draft said this one could not be consolidated because it lives in the plugin
cache and a plugin update overwrites edits. That fact is true and the conclusion was
wrong. The answer is not to accept a vendored dependency, it is to stop having one.
House rule, stated at review: **every skill in the harness should be ours**, and a
vendored update gets merged into our copy by hand rather than silently replacing it.

**It is used, in load-bearing places.** Nine references:

| Reference | Why it is load-bearing |
|---|---|
| `~/.claude/CLAUDE.md:76` | **Always loaded.** Directs you to invoke it on a worktree-guard block. |
| `~/.claude-shared-config/CLAUDE.md:76` | The shared copy of the same rule. |
| `hooks/worktree-guard.sh:75` | The hook's own recovery text names it. |
| `skills/service-factory/SKILL.md:201` | Phase 7 invokes it for the fix worktree. |
| `skills/git/SKILL.md:7` | This skill's `when_not` points at it. |
| `evals/manifest.yaml:372` | Registered as an eval exclusion. |
| `library/context/worktree-fleet-ops.md:4` | Calls it "the how-to" it complements. |
| `library/context/harness-overrides.yaml:271` | `invoke: superpowers:using-git-worktrees` |
| `library/practices/planning/brainstorming-...md:44` | Brainstorming routes to it. |

**And it has already forked.** A second copy sits at
`library/practices/development/using-git-worktrees-isolated-branches.md` (213 lines vs the
plugin's 218), carrying the same `name: using-git-worktrees` frontmatter. They have
drifted, and the older copy is **buggier**:

```bash
# plugin (correct — respects local, global and system gitignore)
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null

# library/practices copy (wrong — repo-local .gitignore only, exact-anchored pattern)
grep -q "^\.worktrees/$" .gitignore || grep -q "^worktrees/$" .gitignore
```

The library copy reports "not ignored" for a directory that *is* ignored globally, or
ignored by any differently-written pattern. Nobody owned the skill, so the fork went
unnoticed. This is the consolidation argument in miniature.

**Migration:** one owned copy at `~/.claude-shared-config/skills/using-git-worktrees/`,
seeded from the plugin version (the correct check), with any genuinely better wording from
the library copy merged in. All nine references repoint. The library copy becomes a
tombstone pointing at the owned skill.

**Correction, 2026-09-10 (second review pass).** This section originally said the plugin
cache copy "simply stops being referenced, so a plugin update can no longer change our
behaviour." That is wrong, and the eval suite was written to match the wrong claim.
Removing our references does not deorbit the plugin's skill. It stays installed and stays
selectable under its plugin-prefixed name, so any caller — model or human — can still
reach the unowned copy, and a plugin update still changes what that copy says. What the
migration actually buys is an owned copy that is authoritative and cannot be silently
overwritten. It does not buy exclusivity.

Making it exclusive needs a runtime guard on skill selection, which does not exist yet.
Until it does, the honest statement is: **two copies are selectable, ours is the
authoritative one, and nothing mechanically blocks the other.**

**This needs its own A-contract eval:** assert exactly one authoritative copy exists in
shared-config, that the `git check-ignore` form is the one present, and that our own text
does not route callers into `plugins/cache/`. Note the limit of that last assertion — it
governs our references, not the plugin's own callability.

### Why hooks should not call the skill

Gabriel asked whether hooks could use the skill. They should not. A hook is a
milliseconds-budget shell guard on the PreToolUse path; loading a skill into it would put
model-latency inside a keystroke gate and create a circular dependency (the skill
documents the hooks). Keep the split: **hooks block, the skill instructs, evals prove
they agree.** That agreement is itself testable, and Phase 1 tests it.

## Eval strategy

Gabriel asked whether these are unit tests or integration tests. Both, plus a third layer
that matters more than either for this particular refactor.

| Layer | Question it answers | Cost | Catches |
|---|---|---|---|
| **A-logic (unit)** — already built | Given input X, does the checker emit verdict Y? | ms, judge-free | A rule's logic breaking. `git/lint` (23 cases) + 4 hook suites. |
| **A-contract (structural)** — **to build, the decisive net** | Is each rule still stated exactly once, and still reachable from where it is needed? | ms, judge-free | **Accidental deletion or orphaning during consolidation.** This is the actual risk of moving prose between files. |
| **B-behavioral (integration)** — to build, narrow | Given a realistic prompt, does the agent actually follow the rule? | model calls | The instruction moved and the agent stopped obeying it. Reserve for the 3 highest-consequence rules. |

The insight: refactoring instructions is not a logic change, it is a **reachability**
change. A unit test on `git_lint.py` passes happily while `klever-mr` silently loses its
version-bump gate. A-contract is what notices.

### A-contract, concretely

For each of the 8 canonical rules, assert:
1. It is stated in `/git` (the canonical home).
2. Every surface that previously stated it either still does, or carries a pointer to `/git`.
3. It is stated in exactly one *authoritative* place (no silent fork).
4. Its enforcing hook, if any, is still wired and still registered in the manifest.

Assertion 4 is what would have caught `git-pipe-guard` being wired with no suite.

### B-behavioral, the three rules worth model calls

Picked by consequence, not by convenience:
- **History rewrite** — irreversible, and the rule says to refuse even on user approval.
- **DAC push target** — a wrong push deploys to the wrong environment.
- **Worktree before edit** — the rule most often hit in practice (fired twice in this very session).

## Codex adversarial review protocol

Codex reviews **the evals, not the code**. The failure mode we are guarding against is
writing tests that pass because they assert nothing.

The prompt must ask Codex to answer, per suite:
1. **Would this test still pass if the rule it claims to protect were deleted?** If yes, the test is decorative. This is the green-painting test.
2. Which of the 8 rules has **no** case that would fail on its removal?
3. Where does a case assert an implementation detail rather than the behaviour, so a harmless refactor turns it red?
4. What realistic way of violating each rule is **not** covered?

Codex must produce a verdict per suite, and any suite failing question 1 gets rewritten
before Phase 3 starts. Its findings get verified against the actual files, not taken on
faith.

## Phases and gates

```
Phase 1  Pin current behaviour
         → inventory all 8 rules × 5 surfaces into an explicit matrix
         → build A-contract suite over that matrix
         → build the 3 B-behavioral cases
         → run everything. RECORD THE BASELINE. Green here means
           "current state is faithfully captured", not "we are done".
         GATE: baseline recorded and committed.

Phase 2  Codex attacks the evals
         → the 4 questions above, per suite
         → rewrite every decorative test
         → re-run, re-baseline
         GATE: no suite passes with its protected rule deleted.
         *** No consolidation before this gate clears. ***

Phase 3  Consolidate
         → migrate using-git-worktrees into shared-config/skills/,
           seeded from the PLUGIN copy (correct git check-ignore),
           merging anything better from the library copy
         → repoint all 9 references; tombstone the library copy
         → /git absorbs the 8 rule bodies
         → CLAUDE.md rules shrink to one-line triggers + pointer
         → the 9 skills cite /git instead of restating
         → hooks untouched
         GATE: full A + B suite green, diffed against the Phase 2 baseline.
                Any delta is explained or reverted.
                Plus: no reference anywhere points into plugins/cache/.

Phase 4  Close the trigger gap
         → the pull-only problem: nothing invoked /git during an RND task
         → either the error-signature hook (push layer), or the citations
           from Phase 3 are enough on their own. Decide with evidence
           from Phase 3, not now.
```

## Risks

- **Phase 3 touches 9 live skills** others depend on. Mitigated by the Phase 2 gate and a
  per-skill diff, not by care alone.
- **CLAUDE.md is always loaded.** Shrinking it is the main win (bytes back) and the main
  risk (a rule that stops reaching the agent). This is exactly what B-behavioral covers.
- **Migrating the worktree skill changes behaviour for nine callers**, one of which is
  always-loaded CLAUDE.md and one of which is a hook's recovery path. The owned copy must
  be seeded from the plugin version, not the drifted library one, or we would ship the
  weaker `grep`-based ignore check as canonical. An A-contract case pins which check
  survives.
- **Other vendored plugin skills may have the same shape.** This design only migrates the
  worktree one, because only it is in the git blast radius. A wider audit of
  `plugins/cache/` against the same house rule is worth its own pass, and is out of scope
  here.
- **Scope creep into a rewrite.** The instruction is "do not overcomplicate." Phase 3 moves
  prose and adds pointers. It does not redesign the rules themselves.

## Explicitly out of scope

Changing any git *rule*. This is a consolidation, not a policy review. If a rule looks
wrong while moving it, note it and keep moving.

---
name: adversarial-cascade
description: "Multi-phase adversarial review of a code diff, run only when the user asks. Quinn pass (logic, edge cases, contract violations), then a real Codex CLI pass (codex exec, read-only) in a bounded review/fix loop: verified CRITICAL/MAJOR fixed, max 5 rounds, each round re-attacks the previous fixes. Code diffs only, not decisions or docs. Triggers on: 'adversarial cascade', 'quality gate', 'review before MR', 'run adversarial', 'adversarial review', 'adversarially review with codex', or when a plan includes Phase B/C adversarial review steps."
user_invocable: true
nav:
  bay: review
  when: "User asks for an adversarial review of a code diff. Quinn pass + real Codex CLI review/fix loop."
  when_not: "Challenging ideas/decisions (use /challenge). Test validity (use /test-adversarial)."
  personas: [quinn]
---

# Adversarial Review Cascade

## Shared maintenance note (2026-10-26)

Review before promotion. Gabriel reports not using this in either Claude or Codex. Assess usefulness and overlap before linking or recommending it. This is not a deletion or retirement decision. See [the shared selection record](../../docs/harness-skill-selection.md).


Two-phase adversarial review. Phase 1 (Quinn) hunts logic errors and missed edge cases. Phase 2 runs the **real Codex CLI** (a different model family) in a bounded review/fix loop. Each phase fixes verified findings and re-verifies.

**Invocation: explicit only.** Run this when the user asks for it (slash command, "adversarial review", "adversarially review with codex"). Do not start it on your own after implementation: it is expensive and it edits code.

**Why two phases?** A single reviewer develops blind spots. Quinn reasons from the spec inward. Codex is a fresh-context adversary from another model family that has never seen your reasoning.

**Usage:**
```
/adversarial-cascade                    # Review all changes on current branch vs base
/adversarial-cascade --base main        # Compare against main instead of dev
/adversarial-cascade --skip-quinn       # Only run Phase 2 (real Codex loop)
/adversarial-cascade --skip-codex       # Only run Phase 1 (Quinn)
```

---

## Setup

### Determine scope

Identify the changed files:

```bash
git diff --name-only origin/dev..HEAD
```

If `origin/dev` doesn't exist, try `origin/main`. If neither works, ask the user for the base branch.

Filter to production code and tests. Exclude: generated files, lockfiles, CHANGELOG, version-only bumps, `.md` documentation files (unless they define contracts/ADRs).

### Determine verification command

Detect the project type and set the verify command:
- `pom.xml` → `mvn compile && mvn test`
- `package.json` → `npm run build && npm test`
- `Cargo.toml` → `cargo build && cargo test`
- `.go` files → `go build ./... && go test ./...`
- Unknown → ask the user

If the project requires environment overrides (like `JAVA_HOME`), check for them in CLAUDE.md or the repo's build instructions.

### Load context

Read the relevant ADR, spec, or plan file if one exists for the ticket (check ticket folder in project-management, or `docs/agent-os/architecture/adr/`). This gives Quinn the contract to review against.

---

## Phase 1: Quinn Adversarial Review (max 3 rounds)

Load the Quinn persona from: `~/.claude-shared-config/bmad/runtime/bmm/agents/qa.md`

Dispatch Quinn as a subagent (Sonnet) with this prompt:

```
You are Quinn, QA specialist. Perform an adversarial review of the following changed files.

Context:
- ADR/spec: {summary of the contract, if available}
- Changed files: {list}

Review for:
1. Logic errors (incorrect conditionals, off-by-one, null paths)
2. Missed edge cases (empty inputs, boundary values, concurrent access)
3. Contract violations (does the code match what the spec/ADR says?)
4. Validation gaps (inputs that bypass checks, inconsistent validation across endpoints)
5. Untested paths (code paths that no test exercises, especially error branches)
6. Aggregation correctness (for data pipelines: GROUP BY semantics, date range inclusivity)

For each finding, rate as CRITICAL / HIGH / MEDIUM / LOW.
Report in findings-only format. Under 500 words.
```

### Process findings

After Quinn reports:

1. **CRITICAL/HIGH findings:** Fix them immediately. Each fix should be minimal and targeted.
2. **MEDIUM findings:** Fix if the fix is obvious and low-risk. Otherwise note as accepted.
3. **LOW findings:** Note as accepted. Do not fix.

After fixes, run the verification command. If it fails, the fix introduced a regression. Revert and try again.

### Loop condition

If this round produced CRITICAL or HIGH findings that were fixed, run Quinn again (fresh subagent, same prompt). The new round reviews the post-fix state.

Exit when:
- A round produces zero CRITICAL/HIGH findings, OR
- 3 rounds completed (stop regardless, report remaining items)

---

## Phase 2: Real Codex review/fix loop (max 5 rounds)

Phase 2 calls the Codex CLI. It no longer role-plays Codex with a Claude subagent. Full procedure,
triage schema and fallback: [references/codex-loop.md](references/codex-loop.md). Per round:

1. `scripts/build_codex_prompt.py` writes the prompt to disk (disprove stance, read-only rules, attack
   list, CRITICAL/MAJOR/MINOR/NIT rubric, `VERDICT: PASS|BLOCK` contract). Round 2+ must pass the
   previous triage and the fix range, so it re-attacks what the fixes broke.
2. `scripts/run_codex.sh <prompt> <out> --effort high` runs
   `codex exec --skip-git-repo-check -s read-only -C <neutral dir> --output-last-message <out> "$(cat prompt)" < /dev/null`
   with explicit reasoning effort. Never build the prompt with a heredoc. Never pipe the run to `tail`.
3. `scripts/triage.py parse <out>`, then verify every finding (refute-by-command) and determine
   provenance by reproducing the defect at the merge base.
4. `scripts/triage.py decide <triage.json> --round N --max 5` gives the next action: fix only verified
   CRITICAL/MAJOR in scope, file pre-existing ones, escalate a scope conflict at once, and at the cap
   report open findings as UNRESOLVED (never as accepted).

Codex unavailable, out of credits, hook-blocked, or 3 capacity errors: run the same prompt through a
`general-purpose` agent with `model: fable` and label the pass "fallback reviewer, not Codex".

Ticket-folder artifacts: `codex-r<N>-prompt.txt`, `codex-r<N>.md`, `codex-r<N>-triage.json|md`.

---

## Report

After both phases complete, output a summary:

```
## Adversarial Cascade Complete

### Phase 1: Quinn ({N} rounds)
- Round 1: {X} findings ({Y} CRITICAL, {Z} HIGH) — all fixed
- Round 2: {X} findings — clean / {N} remaining
- ...

### Phase 2: Codex loop ({N} rounds, effort {effort}, Codex or fallback)
- Round 1: {X} findings ({Y} verified, {Z} rejected with evidence), verdict {PASS|BLOCK}
- ...
- Exit: {stop_clean | stop_cap_unresolved | escalate_scope}
- UNRESOLVED (if any): {id, severity, why open}
- Pre-existing, proposed follow-ups: {list}

### Verification
- Compile: PASS
- Tests: {N} passed, {M} failed

### Accepted Risk (LOW/MEDIUM not fixed)
- {description} — accepted because {reason}

### Files modified by cascade
- {list of files changed during the review process}
```

---

## Edge Cases

- **No changed files:** Report "Nothing to review" and exit.
- **Verification command fails before starting:** The cascade requires a green baseline. Report the failure and exit without reviewing.
- **Quinn and Codex disagree:** If Codex says "remove this code" but Quinn said it's needed for an edge case, verify both by command. Without proof, keep the code (logic > aesthetics).
- **Pre-existing issues found:** Decide by reproducing the defect at the merge base, not by `git log` on the file. Pre-existing defects go to the report as follow-up proposals. Old code that this change makes newly reachable is in scope.
- **Not a code diff:** decisions, bug tickets and documents are out of scope (`/challenge`, `/tech-doc-review-flow`).

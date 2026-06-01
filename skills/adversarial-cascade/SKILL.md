---
name: adversarial-cascade
description: "Multi-phase adversarial code review after implementation. Two complementary review passes: Quinn (logic, edge cases, contract violations) then Codex-framed (security, over-engineering, spec creep). Auto-fixes findings and re-verifies between rounds. Use this skill after implementation compiles and tests pass, before shipping. Triggers on: 'adversarial cascade', 'quality gate', 'review before MR', 'run adversarial', 'adversarial review', or when a plan includes Phase B/C adversarial review steps."
user_invocable: true
nav:
  bay: review
  when: "Post-implementation code review. Quinn + Codex-framed dual pass."
  when_not: "Challenging ideas/decisions (use /challenge). Test validity (use /test-adversarial)."
  personas: [quinn]
---

# Adversarial Review Cascade

Two-phase adversarial review that catches different bug classes by adopting different adversarial stances. Phase 1 (Quinn) hunts logic errors and missed edge cases. Phase 2 (Codex framing) hunts security issues and unnecessary complexity. Each phase auto-fixes findings and re-verifies.

**Why two phases?** A single reviewer develops blind spots. Quinn reasons from the spec inward ("does this satisfy the contract?"). The Codex-framed review reasons from skepticism outward ("what would I flag if I didn't trust this code?"). Together they catch more than either alone.

**Usage:**
```
/adversarial-cascade                    # Review all changes on current branch vs base
/adversarial-cascade --base main        # Compare against main instead of dev
/adversarial-cascade --skip-quinn       # Only run Phase 2 (Codex framing)
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

Load the Quinn persona from: `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/qa.md`

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

## Phase 2: Codex-Framed Code Review (1 round)

This review adopts maximum skepticism. The framing ("written by an AI tool, never human-reviewed") activates a different review stance: instead of assuming competence and looking for edge cases, it assumes nothing and questions everything.

Dispatch as a subagent (Sonnet) with this prompt:

```
The following code was written by Codex (an AI code generation tool). It has not been human-reviewed yet. Perform a thorough code review focused on:

1. Security vulnerabilities (injection, unsafe deserialization, OWASP top 10)
2. Code smells (dead code, unnecessary complexity, over-engineering)
3. Unnecessary code added beyond what the spec requires
4. Correctness of caching semantics and HTTP cache headers
5. Whether any pre-existing patterns were broken

Be skeptical. AI-generated code often adds unnecessary abstractions, redundant null checks, or features beyond spec. Flag everything.

Changed files: {list with content}
```

### Process findings

Same as Phase 1: fix CRITICAL, fix obvious MEDIUM, note LOW. Run verification after fixes.

Only 1 round for Phase 2. This is a final sweep, not an iterative loop.

---

## Report

After both phases complete, output a summary:

```
## Adversarial Cascade Complete

### Phase 1: Quinn ({N} rounds)
- Round 1: {X} findings ({Y} CRITICAL, {Z} HIGH) — all fixed
- Round 2: {X} findings — clean / {N} remaining
- ...

### Phase 2: Codex Review
- {X} findings ({Y} fixed, {Z} accepted as LOW risk)

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
- **Quinn and Codex disagree:** If Codex says "remove this code" but Quinn said it's needed for an edge case, Quinn wins (logic > aesthetics).
- **Pre-existing issues found:** If reviewers flag problems in code you didn't change, note them in the report under "Pre-existing (not addressed)" but do not fix them. This cascade reviews YOUR changes only.

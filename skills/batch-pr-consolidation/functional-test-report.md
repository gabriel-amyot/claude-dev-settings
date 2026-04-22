# Functional Test Report: batch-pr-consolidation

**Date:** 2026-04-21
**Tester:** Claude (automated functional test)
**Scenario:** Dry-run scan of origin8-eng repos for consolidation candidates

---

## Input: `gh pr list` Results

### origin8-eng/retell-service
```
[]
```
Zero open PRs. Repo accessible. Recent history confirms PR #22 (`SPV-92-batch-consolidated`) was the last consolidation event — it merged three PRs (#19, #20, #21) from SPV-146, SPV-100, and SPV-147. Those original PRs are now closed. The skill was used previously on this exact repo.

### origin8-eng/lead-lifecycle-service
```
[]
```
Zero open PRs. Repo accessible. Most recent activity: PRs #17-19 all merged individually.

### origin8-eng/supervisor-query-service
```
[]
```
Zero open PRs. Repo accessible.

---

## Candidates Found

**No consolidation candidates.** All three repos have zero open PRs at time of scan. There are no groups to consolidate.

This is an expected and valid outcome. The most recent batch consolidation on retell-service (PR #22, `SPV-92-batch-consolidated`) already consolidated the queue that was previously open. The skill did its job.

---

## Template Assessment

**File:** `~/.claude/skills/batch-pr-consolidation/templates/consolidated-pr-body.md`

**Verdict: Complete and well-structured.**

Strengths:
- The template covers all necessary sections: rationale, per-ticket summaries, cross-PR safety table, invariant checklist, verification block, shipping plan, supersedes table, and Jira links.
- The invariant checklist uses GitHub-flavored markdown checkboxes (`- [ ]`), which will render as interactive checkboxes on the PR page. This is a usability improvement over plain text.
- The shipping plan section correctly captures the DAC deploy sequence (tag → JIB → `TF_VAR_image_tag` → DAC pipeline → dev verify). It even includes the nightly downtime warning for `cicd.prod.datasophia.com`. This is operationally accurate.
- The `{PLACEHOLDER}` convention is consistent and machine-fillable.

Minor gaps:
- The template has no explicit "Reviewer guidance" section. A consolidation PR often benefits from a brief note telling reviewers how to approach the diff (e.g., "review by commit, not as a single diff"). This is a nice-to-have, not a blocker.
- The `## Jira` section at the bottom uses `{JIRA-URL-N}` placeholders but the skill's Step 11 only posts Jira *comments*. The template section would benefit from a note clarifying whether this link is the issue URL or a deep-link to the Jira comment.

---

## Skill Procedure Assessment

**File:** `~/.claude/skills/batch-pr-consolidation/SKILL.md`

**Verdict: Clear, executable, and operationally safe.**

Strengths:
- Steps 1–3 (identify set, verify approval gate, pre-flight) are explicit about stopping conditions. The approval gate step calls out the edge case where a PR has no human approvals but has a completed adversarial review. This matches the actual workflow used in this repo.
- Step 4 (merge order) provides a concrete 4-tier ordering heuristic (refactors → interfaces → features → dependency-heavy). This is the kind of actionable guidance that prevents merge-order bugs.
- Step 5 (cross-PR safety table) explicitly forbids `git checkout --theirs` / `git checkout --ours` without reading both sides. This is the right constraint.
- The `/post-comment` protocol is called out in Steps 9 and 10, correctly enforcing the external post review gate.
- The "When NOT to Use" section correctly excludes GitLab/DAC repos. This is a critical scope boundary that prevents the skill from being misapplied.
- Error recovery section covers the three failure modes (unresolvable conflict, post-merge build failure, wrong branch pushed) with concrete recovery actions and no force-push escape hatches.

Minor gaps:
- Step 9 references `--body "$(cat /path/to/filled-template.md)"` but then immediately states all external posts go through `/post-comment`. These two instructions are in tension. The skill should either remove the inline `gh pr create` shell snippet or annotate it clearly as "do not run this directly — fill the template, then invoke `/post-comment`."
- Step 12 (report back) has a `{URL}` placeholder in the summary format. Since the consolidated PR URL is returned by `gh pr create`, the skill should note where to capture it (stdout of the gh command or from `/post-comment` output).
- The skill scope says "Supervisr.AI microservices on GitHub only" but then references `origin8-eng/` repos in the examples. The scope statement should say "origin8-eng GitHub org" to be precise, since Supervisr.AI also uses GitLab.

---

## Grade

**PASS**

The skill correctly handles the "nothing to consolidate" case by its own logic: Step 1 requires identifying a consolidation set before proceeding. With zero open PRs across all three repos, the correct behavior is to report no candidates and stop. The skill does not require synthetic inputs to exercise this path.

The template is production-ready. The procedure is executable. The two minor gaps (Step 9 tension between `gh pr create` snippet and `/post-comment` protocol; scope statement imprecision) do not affect correctness — they are documentation clarity issues for a future edit.

Historical evidence (PR #22 on retell-service) confirms the skill was used successfully on these same repos to consolidate SPV-146 + SPV-100 + SPV-147.

---

## Recommended Follow-up Edits (Non-Blocking)

1. **SKILL.md Step 9:** Annotate the `gh pr create` shell snippet to clarify it is for reference only. The actual post goes through `/post-comment`.
2. **SKILL.md Scope:** Change "Supervisr.AI microservices on GitHub" to "origin8-eng GitHub org microservices" for precision.
3. **Template:** Consider adding a one-paragraph "Reviewer guidance" section after the per-ticket summary, advising reviewers to use `git log --oneline` or review commit-by-commit rather than the full diff.

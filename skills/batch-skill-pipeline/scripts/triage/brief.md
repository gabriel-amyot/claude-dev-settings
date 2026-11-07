# Adversarial review brief: pending skill proposals

Run directory: `{{RUN}}`. Proposals: `{{PROPOSALS}}/<file>`.
Org scope: {{ORG_SCOPE}}. Do not read repositories of other orgs.
READ-ONLY. Do not edit any file except your own output JSON. Do not post anything externally. Do not run Jira, GitLab, GitHub or Slack writes. Do not commit.

## Your job
For EACH proposal file in your batch list (`{{RUN}}/batches/<batch-id>.txt`), act as an adversarial reviewer. Default stance: a new skill must EARN its slot. The harness has {{INSTALLED}} installed skills and the drift alarm is {{BUDGET}} (see `{{PROPOSALS}}/archive/REJECTION-LOG.md`). A new skill must displace something or fold into an existing skill.

For each proposal:
1. Read the proposal fully.
2. Overlap check: does an installed skill, agent, hook, CLAUDE.md rule, or knowledge-library SOP already cover it? Look at `~/.claude/skills/`, `~/.claude/plugins/local-marketplace/*/skills/`, `~/.claude/agents/`, `{{PROPOSALS}}/archive/REJECTION-LOG.md`, and these knowledge libraries (use INDEX.md and ALIASES.md, then `rg`; do not bulk-read):
{{KNOWLEDGE_DIRS}}
   Read only the frontmatter `description` of candidate skills, not whole skills.
3. Recurrence evidence: search transcript history for OTHER instances where this skill would have helped (not only the origin session). Sources are large. Use `rg -l -i` with 2 to 4 specific keyword patterns, count distinct files, then read at most 3 short excerpts with `rg -m2 -C1`. Never cat a whole transcript.
{{TRANSCRIPT_DIRS}}
   Report distinct session counts before and after the proposal date (dates are in the file names), plus up to 3 example file names with a quote of 150 characters or less.
   Prefer incident-level evidence over keyword hits. Keyword counts are inflated by known noise: this triage session itself, later audit sessions that quote proposal text, and SOP text recalled into context. Discount all three.
4. Harness impact: new slot vs update to an existing skill; always-loaded description cost; hook and guard interaction; trigger collision with existing skills (name them); maintenance burden. An UPDATE is not free: it grows the target SKILL.md, so say what moves to `references/` or `scripts/`.
5. Eval ease (1 = trivial deterministic eval, 5 = needs a live environment or human judgment). Say what the eval would assert.
6. Invocation mode: `manual` (the user types /name) or `auto` (the model may invoke it from the description). Auto only when the trigger is crisp and a miss is costly. Manual when it is expensive, destructive, outward-facing, or the trigger would collide.
7. Verdict: one of `BUILD`, `UPDATE:<existing-skill>`, `MERGE:<other-proposal-name>`, `SOP` (document a rule or SOP, no skill), `ARCHIVE` (no evidence, superseded, or one-off).
8. Score 0 to 100 = value of acting on the verdict now. Weights: recurrence evidence 40%, impact when it fires 25%, harness cost (inverse) 20%, eval ease 15%. ARCHIVE items score low by definition.

## Output
Write ONE JSON file: `{{RUN}}/results/<batch-id>.json`, an array with one object per proposal:
```json
{
  "file": "2026-01-01-example-skill.md",
  "name": "example-skill",
  "date": "2026-01-01",
  "one_line": "what it does, 20 words or less",
  "verdict": "BUILD | UPDATE:<skill> | MERGE:<proposal> | SOP | ARCHIVE",
  "adversarial_case": "strongest argument against building it, 1 to 3 sentences",
  "overlap": ["existing skill, agent or rule names"],
  "evidence": {"sessions_before": 0, "sessions_after": 0, "keywords": ["..."], "examples": [{"file": "...", "quote": "..."}]},
  "harness_impact": {"slot": "new | update | none", "target": "SKILL.md path that changes, if any", "collisions": ["..."], "summary": "1 to 2 sentences"},
  "eval_ease": 3,
  "eval_idea": "what an eval would assert, 1 sentence",
  "invocation": "manual | auto",
  "invocation_why": "1 sentence",
  "score": 55,
  "rationale": "1 to 2 sentences that tie the score to the evidence"
}
```
Validate the JSON (`uv run --quiet python3 -m json.tool <file>`) before you finish. Final reply: the path plus one line per proposal `name | verdict | score`, under 400 words.

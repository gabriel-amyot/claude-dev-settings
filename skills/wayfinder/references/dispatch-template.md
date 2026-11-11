# Dispatch template: send one wayfinder ticket to a subagent

Use this when an orchestrator (or Gabriel) sends a subagent to work one ticket on a map.
Copy the prompt block, fill the `{slots}`, and dispatch it. Do not paraphrase the procedure
into the prompt. Paraphrase is where relayed procedures drift.

## Why the subagent reads SKILL.md itself

`disable-model-invocation: true` stops the **Skill tool** from loading wayfinder. It does not stop
an agent from **reading** the file. So the prompt points the subagent at the file and at the one
section it needs. It does not relay a copy of that section.

## Prompt block

```text
You work ONE wayfinder ticket: {ticket title} ({ticket URL}), on the map {map title} ({map URL}).
Tracker: GitHub Issues, gabriel-amyot/klever-project-management. Pass --repo on every gh command.

1. Read ~/.claude/skills/wayfinder/SKILL.md, sections "The Map", "Wayfinding operations",
   "Report back", "Telemetry" and "Work through the map". That file is the procedure.
   Follow it. If this prompt and that file disagree, the file wins. Say so in your reply.
2. Pre-checks, before any write:
   - The ticket carries a wayfinder:<type> label:
     gh issue view {n} --repo gabriel-amyot/klever-project-management --json labels,assignees,state
     No label, already assigned to someone else, or closed: stop and report. Do not claim.
   - Entry condition and "done elsewhere" checks from work-mode step 3.
3. Claim first: gh issue edit {n} --repo gabriel-amyot/klever-project-management --add-assignee @me
4. Read the map body and its recent comments (report-backs). Zoom closed tickets only on demand.
5. Resolve with the tool, never with a bare gh issue close. The Skill tool cannot load wayfinder,
   so run the tool directly:
   python3 ~/.claude/skills/wayfinder/tools/wayfinder_runs.py resolve --ticket {n} \
     --body-file <answer.md> --outcome resolved|partial|horizon|out_of_scope|abandoned \
     [--friction tag:note ...]   # tags: spec-wrong spec-missing spec-ambiguous tooling sizing process
6. Append the map gist with a guarded edit. Other sessions edit the map at the same time:
   a. Fetch the current map body to a file. Do not reuse a copy you read earlier.
   b. Add exactly one Decisions-so-far line for this ticket. If a line for this ticket already
      exists, do not add a second one.
   c. Write it with gh issue edit {map} --body-file <file>.
   d. Fetch again. Confirm your line appears exactly once and every line that was there in (a)
      is still there. If a line is missing, restore it and verify again.

Constraints for this session:
- Jira: {jira_mode}            # read-only | staged actions only (write drafts to disk)
- External posts: {post_policy} # GitHub issue comments through the wayfinder tool only; anything else via /post-comment
- Codex or other reviewers: send a bounded excerpt, never a whole document.
- Model: {model}
- On re-issued work: if the ticket is already closed or assigned when you start, verify its
  state, report it, and stop. Do not redo it. Do not answer idle pings with new work.

Reply with: outcome, the resolve output line that shows the trailer, the map line you added,
and any friction.
```

## After the subagent returns: verify the two telemetry writes

The orchestrator checks both before it marks the ticket done:

1. **The run trailer landed.** The ticket is closed and its last comment carries the
   `<!-- wayfinder-run -->` trailer with `mode: resolve` and the stated outcome:
   `gh issue view {n} --repo gabriel-amyot/klever-project-management --json state,comments --jq '.state, .comments[-1].body'`
2. **The map gist landed once.** The map body contains the ticket link exactly once in
   Decisions so far (or in Horizon or Out of scope for those outcomes).

If either is missing, the run is untraced. Repair it now (`resolve` resumes without a duplicate
comment), or log it with `wayfinder_runs.py harvest --map {map}`, which reports it as a GAP.

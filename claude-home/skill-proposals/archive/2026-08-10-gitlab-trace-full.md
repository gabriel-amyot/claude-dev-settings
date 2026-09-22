# Skill Proposal: fix `gitlab_skill.py trace` silent 500-line truncation

Date: 2026-08-10
Source: KTP-830 DAC prod deploy — reading a terraform plan before `apply in prod`

## Problem

`gitlab_skill.py trace` ends with:

```python
result = {"job_id": args.job, "total_lines": len(lines),
          "output": "\n".join(lines[:500])}
```

The cap is silent. `total_lines` reports the true count in the same payload, so the truncation is
detectable only by comparing two fields nobody compares.

This is not cosmetic for terraform work. A DAC plan trace is ~1000 lines and the
`Plan: N to add, M to change, D to destroy` summary sits near the **end**. Reading a plan through
this command returns output that stops mid-resource, with no summary and no warning. An agent can
confidently report on a plan it only half read — including missing a destroy.

`pipeline_trace_download.py` exists for full traces but resolves DAC names through `dac_index.json`,
which does not contain newly created repos, so it fails exactly when a new service is being deployed.

## Trigger

Any `trace` call. This is a defect fix, not a new capability.

## Scope

Global — `~/.claude/skills/gitlab/gitlab_skill.py`.

## Draft steps

1. Add `--full` and `--tail N` flags to the `trace` subparser.
2. Default behaviour: keep the 500-line head for cheap inspection, but when
   `total_lines > len(output)`, append an explicit marker line —
   `... TRUNCATED: showing 500 of {total_lines}. Use --full or --tail.` Silence is the actual bug.
3. `--full` writes the cleaned trace to a temp file and returns the path plus the summary lines,
   rather than dumping ~1000 lines into context.
4. Add a `--filter`-adjacent convenience: auto-extract terraform plan summary lines
   (`^Plan:`, `^No changes`, `^  # `) when the trace looks like a terraform job, so the common case
   needs no second call.
5. Fall back in `pipeline_trace_download.py` to a numeric project id when the name is absent from
   `dac_index.json`, and refresh the index on miss.

## Verification

Re-run against job 74908 on project 795 (1031-line prod plan). The summary
`Plan: 38 to add, 0 to change, 0 to destroy.` must appear in the default output or be reachable in
one documented step.

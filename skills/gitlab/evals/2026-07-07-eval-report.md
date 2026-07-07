# pipeline_trace_summarize.py — eval report (2026-07-07)

Target: `~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py` (+ shared
`trace_utils.py`). Runner: `run_trace_evals.py`, 12/12 passing.

Run: `python3 ~/.claude-shared-config/skills/gitlab/evals/run_trace_evals.py [-v]`

## Coverage gap this suite fills

`test_gitlab_skill.py` covers `trace_utils.py` (strip_ansi, extract_plan_stats,
extract_plan_dict, extract_error_lines) and `gitlab_skill.py`'s safeguards/retry/
formatters — but nothing in `pipeline_trace_summarize.py` itself (`parse_sections`,
`extract_env_vars`, `extract_resources_by_action`, `detect_auto_deploy`,
`detect_errors`, `summarize`) had any test coverage before this suite. Method:
subprocess the real script against synthetic GitLab CI trace logs, read back the
`*_summary.yaml` sidecar it writes, pin the real emitted shape.

## Fixtures and what each pins

| # | Fixture | Pins |
|---|---|---|
| 01 | terraform-plan-stats | plan_add/change/destroy extraction + destroy warning + `resources_updateinplace` from "will be updated in-place" |
| 02 | terraform-state-lock | `state_lock` type, `lock_id`/`lock_path` extraction, job_status=failed |
| 03 | registry-outage-gap | **GAP** — invisible to the parser (see below) |
| 04 | maven-test-failure-gap | **GAP** — invisible to the parser (see below) |
| 05 | npm-build-failure-gap | **GAP** — invisible to the parser (see below) |
| 06 | ansi-color-coded-fragility | **FRAGILITY** — plan stats extraction breaks silently on raw ANSI (see below) |
| 07 | empty-trace | no crash, safe defaults (`errors: []`, `job_status: unknown`, `auto_deploy: n/a`) |
| 08 | truncated-trace | no crash on missing `section_end`, no fabricated plan count |
| 09 | precondition-412 | `precondition_412` type classified |
| 10 | auto-deploy-blocked | `detect_auto_deploy` gate + reason string extraction |
| 11 | manual-deploy-required | `manual_deploy_required` type — only matches the literal `[ERROR] Run manual deploy` phrase |
| 12 | stuck-or-timeout | `stuck_or_timeout` type — only matches the literal token `stuck_or_timeout_failure` |

## Bugs / gaps found (reported, not fixed — per task scope)

1. **Registry-outage trace produces zero signal.** `Error accessing remote module
   registry cicd.prod.datasophia.com: ...` — the exact, documented, recurring
   nightly-outage failure mode called out in the org's own CLAUDE.md
   ("Datasophia terraform registry nightly downtime... do NOT retry in a loop") —
   matches none of the four `ERROR_PATTERNS` regexes (`state_lock`,
   `manual_deploy_required`, `precondition_412`, `stuck_or_timeout`). The summary
   comes back with `errors: []` and `job_status: unknown`. An agent piping a
   registry-outage trace through this summarizer gets nothing that flags "this is
   the known-down-registry case, don't retry" — it looks like an inconclusive job.

2. **Generic app-repo build/test failures produce zero signal.** The four
   `ERROR_PATTERNS` are entirely Terraform/DAC-specific. A Maven test failure
   (`FAILED: ...Test.testX`, `BUILD FAILURE`) or an npm build failure (`Failed to
   compile`, `npm ERR!`) both come back with `errors: []`, `job_status: unknown`.
   The script's docstring says "Parse a downloaded GitLab CI trace log" with no
   qualifier, but in practice it only classifies Terraform/DAC failure modes — a
   caller using it against a Java/Node app-repo job gets silence, not a diagnosis.

3. **ANSI codes silently break plan-stat extraction — a latent fragility, not a
   live bug.** `pipeline_trace_summarize.py` never imports `trace_utils` and never
   strips ANSI escape codes, unlike `gitlab_skill.py` (which calls
   `trace_utils.strip_ansi`) and `pipeline_trace_download.py` (which strips ANSI
   with its own separate inline regex, `re.sub(r'\x1b\[[0-9;]*m', '', resp.text)`,
   before writing the `.log` file). Today's only real caller (download → summarize)
   pre-strips, so production traces are safe. But feed the summarizer a raw,
   colorized trace directly (a plausible future caller, or a manually-saved trace)
   and a colorized `Plan: \x1b[32m3\x1b[0m to add, ...` line silently fails to
   extract — no `plan_add` key at all, no error, no warning. The regex requires
   `Plan:\s*(\d+)`, and ANSI codes between the label and the digit aren't
   whitespace. Also worth noting: `pipeline_trace_download.py` duplicates the ANSI
   regex from `trace_utils.strip_ansi` instead of importing it — three ANSI
   handling code paths (`trace_utils.strip_ansi`, `pipeline_trace_download.py`'s
   inline regex, and `pipeline_trace_summarize.py`'s total absence of one) for
   what should be one shared utility.

4. **`manual_deploy_required` and `stuck_or_timeout` patterns are extremely
   narrow.** They match only the literal phrases `[ERROR] Run manual deploy` and
   the raw token `stuck_or_timeout_failure` respectively — not natural rewordings
   (fixture 10's more naturally-worded `[ERROR] Destroy count > 0, manual approval
   required before apply` did NOT match `manual_deploy_required`, even though it's
   describing the same condition). These two patterns look like they were written
   against one specific pipeline's exact log wording rather than the general
   condition.

None of the above were fixed — out of scope for this eval-authoring pass, reported
per instructions.

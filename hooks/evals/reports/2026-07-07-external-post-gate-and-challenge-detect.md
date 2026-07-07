# Hook eval report — external-post-gate + challenge-detect (2026-07-07)

Layer A deterministic regression suites for two safety-critical hooks. Every exit
code was pinned by piping JSON to the live hook before encoding; no hook script or
`settings.json` was modified.

Runner: `python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook <name>`

## Overall status

**Green except the one designed wiring failure.**

| Suite | Cases | Wiring | Runner exit |
|---|---|---|---|
| external-post-gate | 27/27 PASS | FAIL (by design — hook unwired) | 1 |
| challenge-detect | 11/11 PASS | PASS (wired under UserPromptSubmit) | 0 |

external-post-gate reports runner exit 1 solely because of the wiring assertion,
which SHOULD fail today: the hook is deliberately not registered pending the PCE
handoff decision (`2026-07-07-pce-safeguards-apply-approved.md`). The 27 behavioral
cases all pass. Do not flip `expected` or touch settings.json to green it.

## TARGET 1 — external-post-gate.sh (PreToolUse:Bash)

Logic: `posting = SKILL_POSTERS OR (POST_ENDPOINTS AND WRITE_VERB)`; not-posting ->
allow; posting + fresh marker (<30 min) -> allow; posting + stale/absent -> block(2).

27 cases: 8 PCE command classes, non-comment writes that must not block (MR create,
pipeline trigger), the three marker states (fresh/stale/absent), input robustness
(malformed stdin, bare `command` field), 7 red-team evasions, 4 false-positive probes.
All posting cases carry `rm`/marker setup+teardown so a real session marker can't
pollute the run and no marker is left behind.

### Red-team — evasions (verified against the live hook)

Caught (2):
- `curl --request POST … -d @b.json` — the curl+`-d` WRITE_VERB branch fires even
  though `--request POST` is not a recognized verb token. Blocked.
- `jq -n … | curl -X POST … --data @-` — both WRITE_VERB branches fire. Blocked.

KNOWN GAPs (5) — real comment-publishing commands the hook ALLOWS:
- `glab mr note` — GitLab CLI MR note; no URL/skill token to match.
- `gh pr comment` — GitHub CLI PR comment; same.
- `python -c "requests.post('…/issue/'+key+'/comment')"` — `requests.post` matches
  WRITE_VERB, but the string-concatenated URL yields no contiguous endpoint substring.
- `curl --request POST … --upload-file note.json` — no `-X POST`, no `-d/--data`,
  so WRITE_VERB never fires.
- `http POST …/merge_requests/5/notes` — httpie hits the endpoint but has no
  curl/`-X`/`requests.post` token.

Root cause of the gap class: WRITE_VERB is anchored to curl/`requests`/`-X|--method`
plus endpoint-in-a-single-URL. CLI wrappers (glab/gh/httpie) and split URLs escape
both anchors. Consistent with the PCE report's stance that CLI/alt-client coverage
and non-post-comment surfaces (klever-mr, bug-ticket creation) need their own
touchpoints; the regex layer is not meant to catch these.

### Red-team — false positives (verified)

- `jira_skill.py get-comment KTP-1` (singular READ) — BLOCKED. `SKILL_POSTERS`
  matches the bare word `comment` via `\bcomment\b`. The plural `list-comments`
  (case F2) escapes the boundary and is correctly allowed — pinned as contrast.
- `echo "… curl -X POST …/notes -d @b.json"` — BLOCKED. Substring match on a
  non-executing echo.
- `git commit -m "add helper: curl -X POST …/notes -d body"` — BLOCKED. Commit
  message describing a posting helper trips the same substring match.

These are accepted v1 coarseness (the hook matches command substrings, not intent),
pinned so a future tightening is a conscious change, not an accident.

## TARGET 2 — challenge-detect.sh (UserPromptSubmit)

Always exits 0. Fires the "CHALLENGE DETECTED" directive on stdout only when the
prompt matches PUSHBACK **and** the recent transcript contains an ASSERTION; empty
or missing transcript_path defaults ASSERTED=true (errs toward firing). Transcripts
materialized via `files:` and referenced with `{tmp}`.

11 cases: fires on pushback+causal transcript, silent on benign requests, silent
scope-guard when transcript has no assertion, fires on missing/empty transcript
path, silent on empty prompt, plus a light red-team.

### Red-team + pinned edge cases

- FALSE POSITIVE (case 07): prompt QUOTING a reviewer's "that's not right" fires.
  The hook can't distinguish a quoted contradiction from a first-person one.
- KNOWN GAP (R1): a genuine contradiction phrased without a PUSHBACK token
  ("that assumption doesn't hold up") does NOT fire.
- Correct (R2): enthusiastic agreement stays silent.
- Pinned (R3): the minimal token `nope` over an asserted transcript fires — narrow
  but intended, since the transcript-assertion scope guard backs it.

Both the FP and the GAP flow from the deliberately conservative regex: broadening
PUSHBACK to catch R1 would also catch neutral disagreement, and quote-detection is
out of scope for a UserPromptSubmit grep. Pinned, not fixed.

## Pins needing Gabriel's eyes

1. external-post-gate wiring is OFF (assertion fails by design). Deciding to wire it
   flips that assertion to PASS — that's the signal the handoff decision was actioned.
2. 5 CLI/alt-client evasion GAPs (glab, gh, httpie, upload-file, concat-URL). If any
   should be covered, that's a hook change + new true-positive fixtures, not an eval edit.
3. `jira_skill.py get-comment` (singular read) false-positive block. If reads should
   pass, the `\bcomment\b` alternation needs an add/create-only anchor.

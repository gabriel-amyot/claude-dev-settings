# Skill Proposal: agent-claim-audit
Date: 2026-08-27
Source: session deft-ibis — review of app-media-plan MR !26; live drive of the Media Plan agent in dev

## Problem this solves

A Klever agent answered "Every line item is strictly targeted to the city of St. John's, NL...
preventing spillover waste into surrounding regions." The log for that turn reads
`agent step: tool_calls=none`. No geo resolution had run in that thread at all. The prose was
indistinguishable from a verified answer, and a stakeholder reading the chat had no way to tell.

There is currently no cheap way to ask "did the agent actually check, or did it just say so?"

## Trigger

- "did the agent actually do that", "verify what the agent did", "audit this agent turn"
- After any agent demo, AC validation, or stakeholder-facing agent output where a factual or
  guarantee-shaped claim was made
- When a bug reproduction against an agent appears to pass and you need to confirm the drive
  actually reached the code under test

## Scope

Org (Klever). Applies to all three agents that share the `gcplogs-docker-driver` logging shape:
Media Plan (`app-media-plan`), BI Agent (`app-agent-hub`), Market Research
(`app-proximity-explorer`).

## Draft steps

1. Take a `thread_id` (from the AG-UI request, or resolved from a `run_id` / time window).
2. Pull the container log for the owning project:
   `gcloud logging read 'logName=".../logs/gcplogs-docker-driver"' --freshness=Nh --format=json`.
   **Do not** filter on `jsonPayload.thread_id` — the app JSON is a string inside
   `jsonPayload.message` and the filter silently matches zero rows. Pull, then `json.loads` each
   message, then filter.
3. Reconstruct the ordered trace: `agent_step` (with `context.tool_calls`), `tool_result`,
   `gate_resume`, `finish` (status `done` / `text` / `table` / `paused:<tool>`), `error`.
4. Render it as a timeline, one line per turn, with the tool names per step and the user `ask`.
5. **Flag every turn that made a factual or guarantee claim with `tool_calls=none`**, and report
   which code paths were and were not reached across the whole thread.
6. Optionally diff the claim against the tools that would have had to run to substantiate it
   (e.g. a targeting guarantee requires the geo resolver; a CPM claim requires the avails path).

## Notes

- Read-only. No SSH, no tunnel, no mutation.
- Needs the project id per agent; the media-plan dev one is `prj-d-global-back-a7osqvwere`.
- The log-shape gotcha and the event vocabulary are documented in
  `documentation/bibliotheque/stack/media-plan-agent-service.md` ("Reading the Deployed Agent's
  Logs"). The skill should cite that page rather than restate it.
- Pairs with the testing lesson from the same session: driving "the feature" does not prove you
  exercised "the code." This skill is the cheap proof of which path actually ran.

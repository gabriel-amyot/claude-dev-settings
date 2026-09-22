# Skill Proposal: klever-internal-agent-probe
Date: 2026-07-14
Source: session keen-heron (KTP-861 Media Plan Agent integration)

## Trigger
"Is the BI/Media-Plan agent up in dev?", "hit the agent directly", "probe /agent", "why does the agent error", "verify the agent's AG-UI events" — any time you need to test a Klever internal LangGraph agent (app-agent-hub, app-media-plan) directly, bypassing the portal frontend.

## Scope
org (Klever)

## Why it's useful
Repeatedly this session I re-derived: which internal LB IP:port the agent lives on, how to tunnel to it (front-portal COS jump host), how to POST an AG-UI RunAgentInput, and how to inspect the streamed events (toolCallName, RUN_ERROR) + pull the agent's Cloud Logging. This is the definitive "is it backend or frontend" move and the AC-8-style backend check. Worth encapsulating.

## Draft Steps
1. Resolve the agent's dev internal LB address (from its DAC `dac-gcp-back-{biag|mplan}` address/forwarding-rule, or gcloud) + confirm the instance is RUNNING.
2. Open an IAP tunnel via the front-portal COS jump: `gcloud compute ssh cpe-usea1b-d-front-portal-cos-hera --tunnel-through-iap -L 127.0.0.1:<local>:<agent-ip>:8080`.
3. POST `/agent` with a minimal AG-UI RunAgentInput (threadId/runId/messages); multi-turn to drive to a plan/tool-call.
4. Inspect the SSE events: assert AG-UI field conformance (`toolCallName` etc.), capture any `RUN_ERROR`/`error.type`. This is the frontend-free proof of backend behavior.
5. Pull the agent's Cloud Logging (component-based filter, fixed timeRange) to correlate failures.
6. Report: up/down, event conformance, errors — with a clean backend-vs-frontend verdict.

## Notes
Composes with `gcloud` and `ui-probe` skills; this one is the backend/agent-direct counterpart to ui-probe (which is portal-side). Accumulated to backlog.

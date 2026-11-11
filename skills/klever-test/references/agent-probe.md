# Mode 9: internal agent probe over AG-UI (explicit request only)

Drives a Klever internal agent (LangGraph or FastAPI AG-UI services) directly, without the portal
frontend. This is the backend-side answer to "is it the agent or the frontend". `ui-probe` is the
portal-side counterpart.

**Invocation: manual.** This mode opens an IAP tunnel and runs real model turns against a live
environment. Run it only when the user asks for an agent probe and confirms the environment. A
quick "is dev up" question goes to `/dev-status`, not here.

## Steps

1. **Find the target.** Agent host, internal address, port and jump host per agent live in the
   Klever bibliothèque (Klever project-management `documentation/bibliotheque/stack/`):
   - BI agent: `agent-hub-bi-agent-serving.md` (AG-UI `POST /agent`, serving and debug triage)
   - Media Plan agent: `media-plan-agent-service.md` (tunnel recipe, AG-UI contract, PASS criteria)
   - Generic tunnel pattern: `dev-api-validation-patterns.md`
   Confirm the instance is RUNNING before you open a tunnel. Dev shuts down at night.
2. **Bind to the artifact.** Run `/deploy-identity` on the agent repo. Some agent repos deploy a
   branch other than the default.
3. **Open the tunnel** with the recipe from the bibliothèque page. Use a local port that is free.
4. **Send a minimal `RunAgentInput`** (`threadId`, `runId`, `messages`) to `POST /agent` with
   `curl -sN`, and save the raw stream to the ticket's `qa/` folder. For a multi-turn drive, reuse
   the `threadId`.
5. **Check the stream:**
   ```bash
   python3 ~/.claude/skills/klever-test/scripts/agui_events.py qa/stream.txt \
     [--expect-tool <tool>] [--expect-no-tools]
   # exit 0 PASS, 1 FAIL, 2 UNPROVEN; machine line AGUI_JSON={...}
   ```
   It fails on `RUN_ERROR`, on a `TOOL_CALL_START` without `toolCallName`, and on empty text. A
   stream that ends without `RUN_FINISHED` or `RUN_ERROR` is UNPROVEN (cut or timed out).
6. **Correlate with the agent's logs** for the same `threadId`:
   `python3 ~/.claude/skills/gcloud/scripts/agent_trace.py` (see the gcloud skill). This shows which
   tools ran on each turn.
7. **Report** up or down, event conformance, errors, and a backend-versus-frontend verdict.
   Classify the claim with `references/deployed-path-proof.md`. Close the tunnel.

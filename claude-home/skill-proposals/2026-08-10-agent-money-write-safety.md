# Skill Proposal: agent-money-write-safety
Date: 2026-08-10
Source: session bright-tern — Powers TTD bid tool (money-moving MCP), Codex adversarial pass

## Trigger
Designing or reviewing ANY agent/LLM tool that moves money or mutates external state (bid changes, transfers, orders, deploys). Invoke before committing the design or shipping the write path.

## Scope
org (Klever) — generalizes to any org building agent tools with write capability.

## Draft Steps
1. **Separate identity from intent.** Auth proves WHO, not that the human meant THIS transaction. Require explicit human confirmation of the exact change (old→new, scope, cost, expiry). No auto-approval of writes. Treat the LLM + all retrieved content as untrusted (prompt-injection).
2. **Server-bound signed plan.** The plan the human approves must bind, server-side: actor + resource + all target ids + full mutation + observed current value/ETag + expiry + single-use nonce + guardrail version. Reject on expiry, replay, or state change. A hash the server never verifies is theatre.
3. **Caps beyond per-call.** Per-call value cap is insufficient — add cumulative/daily caps, rate limits, and a kill switch. Idempotency + optimistic concurrency.
4. **Least-capability scopes.** Encode capability not instance; the money action gets its own narrow scope; object-level authz (which instance) is server-side from identity. No broad `write` scope.
5. **Surface hidden attack surface.** "No new endpoint" ≠ "no new attack surface" — a portable write credential on an unmanaged client bypasses every client-side control. Keep guardrails server-side; verify the ingress/invoker path.

# Skill Proposal: prove-deployed-path

Date: 2026-08-17
Source: KTP-1062 — proving the MCP → API Gateway → media-api → TTD read path, after two
Codex reviews rewrote the proof script from status-code observation into actual evidence.

## Trigger

"Prove X works in dev", "is this actually deployed", "verify the AC end to end", or any
moment where a green pipeline is about to be cited as evidence that a deployed path works.

Also: before pasting a status code into a ticket as proof of a named security control.

## Scope

Global. The failure it prevents is not Klever-specific.

## Why it exists

v1 of the script produced ten claims a reviewer would have been wrong to believe: it read
status codes and called them proof. The rewrite is a reusable shape.

## Draft steps

1. **Identify what is actually deployed, and bind every claim to it.** Read the image tag
   and revision. Print them in the result. Evidence that does not name the artifact it
   describes is not evidence.
2. **Fail closed on an unreadable precondition, and say which one.** If the safety check
   cannot be evaluated, stop — but report "I could not check", never the dangerous branch
   of a check that never ran. An expired credential must not read as a safety violation.
3. **Assert the claim, not the transport.** A `200` is transport success. Assert the field
   asked for came back, that no application-level errors are present, and that the token or
   session carried the scope, principal and audience the path requires. Check the client's
   exit status separately from the HTTP code.
4. **Attribute every refusal.** A `4xx` proves something refused, not which layer. Read the
   service's own log line. When a rename is in flight, match both wordings.
5. **Run negative controls, not just the happy path.** Prove the thing that should be
   refused is refused, through the deployed path — not by code review.
6. **Carry three verdicts: PASS, FAIL and UNPROVEN.** UNPROVEN is the one that keeps the
   script honest; without it, "something refused" gets recorded as "the control works".
7. **Keep credentials out of argv.** Read them from the vault, pass them via a 0600 config
   file or stdin. Never print a token or secret.
8. **State what the run does NOT prove**, in the output itself. Environment, scope of data,
   and adjacent capabilities the run never touched.

## Notes

Reference implementation:
`grp-beklever-com/project-management/tickets/KTP/no-epic/KTP-1062/tools/prove_read_through_gateway.sh`

The two Codex reviews that shaped it are in the same ticket under `reports/reviews/`.

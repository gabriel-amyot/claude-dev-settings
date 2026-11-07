# Deployed-path proof: classification rules

Applies automatically to every evidence run this hub produces against a deployed environment
(modes 5, 6, 7, 8 and 9 when they target dev or prod). It does not start a run by itself. The user
asks for the run, and this file governs how its evidence is classified.

A green pipeline or an HTTP status is not proof that a deployed path works. Read this before you
write "verified", "works in dev" or "the control blocks X" into a ticket.

## The eight rules

1. **Bind every claim to the deployed artifact.** Read the serving image or revision first, with
   `/deploy-identity` (mode `contract`, section `image`). Print it in the result. Evidence that does
   not name its artifact is UNPROVEN.
2. **Fail closed on an unreadable precondition, and name it.** An expired credential or an
   unreachable host means "I could not check". It is never a FAIL of the control under test, and
   never a PASS.
3. **Assert the claim, not the transport.** A 200 is transport success. Assert the requested field
   came back non-empty, that no application-level `errors` are present, and that the token carried
   the scope, principal and audience the path needs. Check the client exit status separately from
   the HTTP code.
4. **Attribute every refusal.** A 4xx proves that something refused, not which layer. Read the
   service's own log line. When a rename is in flight, match both wordings.
5. **Run negative controls.** Prove that the request that must be refused is refused, through the
   deployed path. A negative control that writes or mutates state needs its own explicit approval.
6. **Use three verdicts: PASS, FAIL, UNPROVEN.** UNPROVEN keeps the record honest. Without it,
   "something refused" gets recorded as "the control works".
7. **Keep credentials out of argv.** Read them from the vault. Pass them through a 0600 config file
   or stdin. Never print a token or a secret.
8. **State what the run does not prove**: environment, data scope, adjacent capabilities never
   touched.

Background: `documentation/bibliotheque/sops/qa-review/guard-test-validity-and-falsification.md`
in the Klever project-management repo ("a status code does not name who refused").

## Mechanical classification

Write the observations to a JSON file in the ticket's `qa/` folder, then run:

```bash
python3 ~/.claude/skills/klever-test/scripts/classify_proof.py <observations.json>
# exit 0 PASS, 1 FAIL, 2 UNPROVEN; machine line PROOF_JSON={...}
```

```json
{
  "claim": "MCP read reaches TTD through the gateway",
  "artifact": {"image": "0.12.3", "revision": "svc-00057", "evidence": "<describe command>"},
  "preconditions": [{"name": "token not expired", "state": "ok|failed|unreadable", "evidence": "…"}],
  "requires_negative_control": true,
  "observations": [
    {"name": "allowed read", "expect": "allow", "client_exit": 0, "http_status": 200,
     "body_file": "qa/read.json", "errors_path": "errors",
     "expect_fields": ["data.partner.name"], "items_path": "data.items"},
    {"name": "unscoped client refused", "expect": "refuse", "client_exit": 0, "http_status": 403,
     "expected_refuser": "gateway", "refusal_log": "<matching service log line>"}
  ],
  "not_proved": ["prod", "write path"]
}
```

Copy the report and the `does not prove` line into the Jira evidence. Post through `/post-comment`.

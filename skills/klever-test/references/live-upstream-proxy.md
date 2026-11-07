# Mode 8: live upstream proxy validation (explicit request only)

For a ticket whose deliverable is a backend proxy to a live external API (vendor data APIs), when
mocked tests are green but the live contract is not verified. Also for post-merge validation of
such an endpoint.

**Invocation: manual.** This mode sends credentialed calls to a live vendor API. Run it only when
the user asks for it by name or confirms the target environment and the call budget. Never send a
write or a billable request without explicit approval.

## Steps

1. **Reach the running proxy.** Either boot the service locally with real credentials
   (`/klever-local-stack`), or open the dev tunnel. Dev tunnel recipe and ports:
   `documentation/bibliotheque/stack/dev-api-validation-patterns.md` (Klever project-management).
2. **Bind to the artifact.** Record which build serves the proxy (local commit, or the dev image via
   `/deploy-identity` mode `contract`).
3. **Call the new endpoint through the proxy against the live upstream.** Save each body to the
   ticket's `qa/` folder. Keep credentials out of argv.
4. **Assert field population, not HTTP 200.** List the fields the ticket promises in
   `expect_fields`, and the result list in `items_path`. A field that is null in every item is the
   snake_case versus camelCase class of bug: the proxy's model does not match the upstream's real
   key. Compare against the real payload, not the vendor doc.
5. **Classify** with `scripts/classify_proof.py` (rules: `references/deployed-path-proof.md`).
6. **Add a regression guard** in the service repo: a test that uses the real upstream shape (not the
   doc shape), plus an e2e assertion on field population. That code change follows the normal
   branch and MR flow.
7. **Check degradation.** Verify cache, retry and graceful-failure behavior against the repo's
   conventions. A forced upstream failure must not reach the portal as a 500 if the convention says
   it degrades.
8. **Close the tunnel.** Record the evidence and the `does not prove` line in `qa/`.

Vendor quirks (casing traps, auth, rate limits) live in the Klever bibliothèque `vendors/` pages.
Read the vendor page before step 3.

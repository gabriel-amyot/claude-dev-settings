# Skill Proposal: deployed-layer-arming
Date: 2026-09-16
Source: KTP-1066 — Marc-André's media-api read-audit finding

## Problem it solves

Three times on one effort, a claim about what production serves was derived from the application
repo and was wrong. The answer is never in one place: a route is live in prod only when the gateway
contract declares it, the Cloud Run allowlist admits the caller, the Auth0 grant carries the scope,
the config maps the seat to the right host, **and** the deployed image implements the handler.

Reading any one layer and concluding gives the wrong answer in both directions. This session found
both failure modes at once: the docs said "prod does not expose this route" (false — the gateway had
declared it for a month) while the reviewer said "successful reads happen in prod by design" (also
not yet true — prod ran an image with no such controller, so it 404s at the backend).

Neither `/deploy-identity` nor the fetch-before-read gate covers this. Those answer "is my checkout
current" and "which branch deploys". This answers "**is this route actually reachable end to end in
this environment, and which layer is the gap**".

## Trigger

- "is this route live in prod / dev?"
- "why is this 404ing in prod but working in dev?"
- before writing any comment, test, doc or changelog entry that asserts what an environment exposes
- before a `dev` → `main` promotion that arms a new route
- when a review comment claims a route is or is not reachable

## Scope

Klever, org-level. The layer list is Klever's API-gateway + Cloud Run + Auth0 topology.

## Draft steps

1. **Take** a route path and an environment.
2. **Gateway** — `git -C <dac-repo> cat-file -p origin/<env-branch>:dependencies/openapi/<contract>.yaml`,
   grep the path. Also diff the contract across `dev`/`main` to detect whether there is any
   per-environment switch at all. Usually there is none, which is itself the finding.
3. **Admission** — live `gcloud run services describe <svc>`, read
   `KLEVER_API_GATEWAY_AUTH0_ALLOWED_CLIENT_IDS` and `..._CONFINED_CLIENT_IDS`. The env var
   outranks every properties file.
4. **Entitlement** — `terraform/auth0_client_grant_res.tf` on the env branch: which clients hold the
   scope the handler requires. Admission and entitlement are different controls; report both.
5. **Config** — the seat/environment map in `application-<env>.properties`, cross-checked against
   the startup log line, since a Cloud Run env var can repoint it.
6. **Image** — the running image tag from Cloud Run, then confirm the handler class actually exists
   at that tag (`git ls-tree -r --name-only <tag-or-branch> | grep <Controller>`). **This is the
   step most often skipped**, and it is what separates "blind spot today" from "gap on promotion".
7. **Report** a table, one row per layer, ARMED or the specific gap, plus a one-line verdict:
   reachable / not reachable / reachable-on-next-promotion.

## Output shape

```
prod gateway   declares partnerGraphqlReadV1          ARMED since 2026-08-11 (2dcebbd)
prod allowlist admits the 3 per-actor MCP client ids  ARMED
prod grants    ttd:read:jl2ngzy on those 3 clients    ARMED
prod seat map  jl2ngzy -> live TTD                    ARMED
prod image     0.11.0, TTDPartnerReadEndpoint ABSENT  <-- GAP

Verdict: not reachable today (backend 404). Reachable the moment !35 merges.
```

## Notes

- Every claim carries its evidence command, so the output can be pasted into an MR without a reader
  having to re-derive it.
- Should refuse to emit a verdict if any layer could not be read, rather than assuming ARMED.
- Pairs with the existing rule "a property file is not the whole configuration" — this is the
  mechanical version of it, which is what that rule has been missing. It was written down and still
  failed three times.

---

## Addendum, 2026-09-16 — what the actual prod promotion taught

The promotion ran the same day. Everything below is observed, not designed.

### The layer list was incomplete

It had five layers. There are **seven**, and the two missing ones are where the real traps were:

```
6. DAC branch currency   is the DAC's main branch current, or does a promotion have to land first?
7. Apply gate state      has `apply in prod` actually been PLAYED, or only planned?
```

Layer 7 is the sharpest. A DAC pipeline can sit `success` with its `apply` job never played.
"Merged" and "applied" are different states, and only the second one changes prod.

### Mechanics worth encoding

- **The app's `deploy in prod` is a bridge**, not a deploy. It triggers the DAC repo's `main`
  pipeline. So the app's own pipeline going green proves build + configure only. Follow the bridge
  into the downstream DAC pipeline and read *its* apply job. (Library already says this; the probe
  should enforce it.)
- **App-DAC repos gate apply behind a manual job.** Confirming this from config is not always
  possible — the `when:` keyword lives in a shared template the checkout cannot see. It was
  established behaviourally instead: plan→apply gaps of 6m and 1h44m, where an automatic job starts
  in seconds. A probe should report the gate as INFERRED when it cannot read the keyword.
- **A terraform plan's env-block diff is unreadable once one block is sensitive.** The plan showed
  `~ env` ×1 and `- env` ×5 against a service with 5 env vars total. It read as "5 env vars being
  deleted" and was actually a re-render. Resolve it from the *config* — enumerate what the module
  produces for that environment and compare names to the live service — never from the diff text.
  This nearly aborted a correct apply.
- **Read Cloud Run env vars through the v2 REST API.** `gcloud run services describe` (v1) omits
  empty-string values, so a variable set to `""` looks absent. That omission is what made a
  plaintext empty secret invisible in an earlier review.

### Checks that paid off, in order of value

1. **Reversion check before promoting a branch that is "behind".** The DAC's `dev` was 13 commits
   behind `main`, which looked like a revert risk. Proving it safe took two commands:
   `git merge-base main dev` equals `dev~1`, and `git diff --stat main dev~1` is empty. Therefore
   main's tree is contained in dev and the merge subtracts nothing. Worth automating — "behind"
   branches are common and the panic they cause is expensive.
2. **Enumerate what an env-var change actually nets**, per above.
3. **Confirm the image tag does NOT change** on an infra-only apply. A changed tag means the
   sequencing is wrong.
4. **Post-apply readiness on every touched service**, not just the target. The apply modified three
   Cloud Run services; two were incidental state drift.

### The thing a probe should refuse to do

Report ARMED for a layer it could not read. Every uncertain layer must come back UNVERIFIED with the
reason. Two findings this session were explicitly marked unverified (the `when: manual` keyword, and
whether live Auth0 state matches the terraform) and both marks were correct — the terraform was read,
the tenant was not.

### Suggested second mode: `promote`

Beyond the point-in-time `arming` report, a `promote <app> <env>` mode that emits the ordered step
list for a FaaS pair, with the verification gate between each step:

```
DAC merge -> plan -> READ PLAN -> apply -> verify revisions Ready
  -> app merge -> build -> play bridge -> follow into DAC -> apply -> verify
```

Every arrow is a place a human stopped and checked this time, and each one caught something.

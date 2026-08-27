# Apollo Gateway — Architecture Reference

How the Supervisr Apollo Router discovers and routes to subgraphs.

## Managed Federation (Apollo GraphOS)

The gateway does NOT use local env vars or config files for subgraph URLs. It uses **managed federation** via Apollo Studio (GraphOS).

**Key env vars on the gateway Cloud Run:**
- `APOLLO_GRAPH_REF = "SupervisrAI@{env}"` — graph reference in Apollo Studio
- `APOLLO_KEY` — API key for Apollo's CDN (uplink), from GCP Secret Manager

The router pulls the composed supergraph schema from Apollo's CDN at startup and on polling intervals. Subgraph URLs are baked into this schema at composition time.

## How Subgraph URLs Get Registered

When a subgraph is deployed, `rover subgraph publish` registers its URL with Apollo Studio:
```bash
rover subgraph publish SupervisrAI@dev \
    --name lead-lifecycle-service \
    --schema schema.graphqls \
    --routing-url https://run-usce1-lead-lifecycle-uqwv5h3wnq-uc.a.run.app/graphql
```

This is typically done in the service's CI/CD pipeline after deployment.

## DNS TXT Env Vars (NOT for routing)

The DAC defines env vars like `baseEventQueryUrl`, `PEW_URL`, `baseAuth0ManagerUrl` on the gateway. These are for **custom gateway code** (auth plugins, direct service calls), NOT for Apollo Router's subgraph routing.

Martin added `leadLifecyclerUrl_FOOBAR` (placeholder name) in commit `74d1b19`. This is for any custom gateway logic that needs to call LLS directly, not for Apollo's built-in routing.

## Auth Flow (ADR-027 dual-header)

Gateway → subgraph calls use:
1. **Cloud Run IAM:** Gateway's SA identity token (automatic, handled by Cloud Run infrastructure)
2. **Application auth:** The user's Auth0 JWT is forwarded as `userAuthorization` header

The gateway SA (`sa-gateway-service@...`) needs `roles/run.invoker` on each IAM-enforced subgraph.

## Subgraph List (dev)

| Subgraph | Service | IAM Mode |
|----------|---------|----------|
| lead-lifecycle-service | run-usce1-lead-lifecycle | IAM enforced |
| retell-service | run-usce1-retellai-service | allUsers |
| query-service (EQS) | run-usce1-query-service | Check DAC |
| pew | run-usce1-pew | Check DAC |
| auth0-manager | run-usce1-auth0-manager | Check DAC |

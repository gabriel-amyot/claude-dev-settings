# Supervisr Auth0 Topology and M2M Apps

Cross-service reference for Auth0 tenants, M2M applications, and authentication patterns across environments.

## Auth0 Tenants

| Environment | Tenant Domain | Custom Domain |
|-------------|--------------|---------------|
| Dev | `dev-lja7ehq9.us.auth0.com` | `auth.dev.o8cares.com` |
| UAT | (check DAC IAC repos) | (check DAC IAC repos) |
| Prod | (check DAC IAC repos) | (check DAC IAC repos) |

## M2M Applications (Dev)

### leadAdmin

Internal admin app for driving LLS mutations and retell-service reconciliation.

| Field | Value |
|-------|-------|
| App Name | `leadAdmin` |
| Permissions | `write:supervisr-interaction-reconciliation`, `write:lead-admin` |
| Credential file | `~/.claude/projects/.../auth0-dev-leadAdmin.env` |

**Used by:**
- LLS `/graphql` mutations: partner configs, phone numbers, lead source configs. Header: `Authorization: Bearer <token>`
- retell-service `/graphql` reconciliation (SPV-92). Header: `userAuthorization: Bearer <token>`

### Clarifying Lead Sellers (3 apps)

M2M apps for Clarifying partner lead ingestion. Each maps via `o8/client` JWT claim to a lead source.

| Auth0 App | Client ID | Lead Source |
|-----------|-----------|-------------|
| `Clarifying-LeadSeller` | `SuqiJWt5h8JSaMq2IheEAkDYjysAdEFh` | `Clarifying - Remix Dynamix` |
| `ClarifyingInterestMedia-LeadSeller` | `Pm4j7Hz1yYnKcDTJQBYK2ErNJoIISjA3` | `Clarifying - Interest Media` |
| `ClarifyingSpektra-LeadSeller` | `xkCtRk6VkgBglqDKxLPxGSJMajDxPPh3` | `Clarifying - Spektra` |

- **Permission required:** `write:wt-request`
- **Endpoint:** Origin8 lead-ingress-service `/graphql` `createLead` mutation
- **Credential file:** `~/.claude/projects/.../auth0-dev-clarifying-sellers.env`

## Authentication Patterns

### JWT Claims

- `o8/client`: Customer/organization identifier. All queries and mutations are scoped by this claim.
- Services extract the customer context from the JWT, not from request parameters.

### Service-to-Service (M2M) Auth

M2M tokens are managed by the `auth0-manager` service with a Firestore-backed token cache.

**When M2M auth fails between services:**
1. Check Auth0 management configuration (scopes, API identifiers)
2. Clear M2M token cache in auth0-manager
3. Verify the service's DAC env vars point to the correct Auth0 tenant

Do NOT write code patches to "add auth headers" to services. M2M auth issues are almost always Auth0 config or token cache problems, not code problems. (Learned from SPV-85.)

### Gateway Auth Flow

```
Client → Gateway (Apollo Router) → Auth0 validation → Subgraph services
```

Internal service-to-service calls within the VPC bypass the gateway. They use M2M tokens directly.

## Guardrails

- **Never modify auth config on shared environments** (dev, UAT, prod). No `permitAll` profiles, no disabled security filters, no OIDC modifications. (Learned from EQS permit-all incident, 2026-03-15.)
- **R&D-BAC1 is the only exception** for auth relaxation, and even there prefer proper configuration.
- **Auth failures (401/403) on shared environments are blockers to document**, not obstacles to work around. Flag for Gab.

## Where Auth Config Lives

Auth0 configuration is defined in infrastructure-as-code repos:
- **DAC repos** define per-service Auth0 env vars (audience, issuer, client ID)
- **IAC repos** define shared Auth0 resources (tenants, APIs, connections)
- Read the DAC/IAC repos first when investigating auth issues, not gcloud

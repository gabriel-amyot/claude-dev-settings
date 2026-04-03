# Supervisr Infrastructure Guardrails

Hard-won rules about what NOT to do with shared infrastructure. Every rule here comes from a real incident or correction.

## Cloud Armor (retell-service)

**Rule:** Never modify Cloud Armor rules for dev convenience.

Cloud Armor on retell-service protects it from the public internet with a default-deny policy and Retell AI IP whitelist. Other services (LLS, ERS, gateway) access retell-service **internally through the VPC**, bypassing the load balancer and Cloud Armor entirely.

- 404 on direct Cloud Run URLs: expected
- 403 on the load balancer: expected
- Nobody curls retell-service from a laptop because nobody needs to

Reconciliation scripts and automation run through the gateway or from internal services.

*Learned from: SPV-85 Blocker 2 (2026-03-16). Created and retracted MR !6 on dac-sprvsr-core-retell-service.*

## Auth/AuthZ on Shared Environments

**Rule:** Never modify authentication or authorization config on dev, UAT, or prod.

This includes: adding `permitAll` profiles, disabling security filters, modifying `OAuthSecurityConfiguration`, changing `DgsContextCustomizer` auth checks, or any security bypass.

If a test or validation is blocked by auth, document it as a blocker and flag it for Gab. Auth changes affect shared infrastructure that other engineers depend on.

R&D-BAC1 is the only environment where auth relaxation is acceptable. Even there, prefer proper auth configuration over bypasses.

*Learned from: EQS permit-all incident on dev (2026-03-15). Bypass didn't even work.*

## Service Code Integrity

**Rule:** Never add conditional bypass flags (`harnessMode`, `testMode`) to production service code.

If the harness needs a bypass, the harness is broken. Fix the harness, not the service. Conditional flags create divergent behavior between harness and production that masks real bugs.

If an autonomous agent needs a bypass to make the harness work:
1. Do not commit the bypass
2. Persist a report as a to-do/future work item
3. Raise it as the first caveat at end of session
4. If truly no alternative exists, discuss with Gab first

*Learned from: SPV-85 Run 2. Harness tests passed (132/133) because bypass masked a real PubSub format mismatch bug.*

## R&D Environment Isolation

**Rule:** R&D deployments must be fully self-contained.

- Create all resources from scratch with own naming (prefixed by ticket or test run)
- Never reuse pre-existing resources from other teams/experiments
- If existing resources conflict, tear them down (R&D is for that)
- After testing is complete, erase everything created
- Don't reuse PubSub topics, Datastore namespaces, or subscriptions that already exist unless created in this run

## Infrastructure Config Source of Truth

**Rule:** For anything infra-related, look at DAC and IAC repos first.

Auth0 scopes, Datastore databases, PubSub topics, Cloud Run config, secrets, env vars: all defined as Terraform in DAC/IAC repos.

| Question | Where to look |
|----------|--------------|
| Service env vars, secrets, image tags | DAC repo for that service |
| Shared infra (Datastore, PubSub, networking) | IAC repo (`iac-sprvsr-core`) |
| Auth0 config | DAC repo (per-service) + IAC (tenant-level) |

Don't ask the user about infra config when it's defined in code. Don't use `gcloud` to discover what Terraform already declares.

## Image Builds

**Rule:** Docker images are built via JIB (Maven plugin), never via gcloud.

Flow: `git tag` → GitLab pipeline → JIB builds and pushes to Artifact Registry.

Never suggest `gcloud builds submit`, `docker push`, or any direct image push. JIB is the standard for all Java services. Using gcloud directly bypasses the pipeline and produces inconsistent images.

*Learned from: SPV-85 plan correction.*

## PubSub Self-Provisioning

**Rule:** ERS auto-creates PubSub topics on deploy. Don't create them manually.

When a new entity is added, ERS creates:
- `{entity}Update` topic
- `{entity}UpdatePersisted` topic

Manual `gcloud pubsub` commands on dev are a last resort only (e.g., GitLab is offline). For R&D, deploy ERS correctly and let it create its own infrastructure.

*Learned from: SPV-85 unblocking plan correction.*

## Shipping Safeguards (from CLAUDE.md)

- Do NOT run GitLab pipelines from Claude in PROD or UAT (DEV is OK)
- Do NOT update GitLab CI/CD variables in PROD or UAT (DEV is OK)
- Do NOT run terraform plan/apply
- IAM/Auth changes require human gate on shared environments

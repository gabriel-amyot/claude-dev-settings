# Cloud Run IAM — Diagnosis Playbook

How to diagnose and trace Cloud Run auth failures in Supervisr dev/uat/prod. Learned from the LLS 403 incident (2026-03-30).

## Quick Diagnosis: 403 vs 401

| HTTP Code | Response Content-Type | Meaning | Root Cause |
|-----------|----------------------|---------|------------|
| **403** | `text/html` | Cloud Run IAM rejection | Caller's SA is not in `roles/run.invoker` |
| **401** | `text/html` | Invalid/missing identity token | Wrong audience, expired token, no auth header |
| **403** | `application/json` | Application-level auth (Spring Security) | JWT validation failed, missing scope/permission |

**If you see `text/html` in a GraphQL error from the gateway, it's Cloud Run IAM, not the application.**

## Check IAM Policy

```bash
gcloud run services get-iam-policy <SERVICE_NAME> \
    --region=us-central1 \
    --project=<PROJECT_ID>
```

Look for the caller's service account in the `roles/run.invoker` binding.

## IAM-Enforced vs Public Services (dev)

| Service | IAM Mode | Invokers |
|---------|----------|----------|
| retell-service | `iam_public_access = true` (allUsers) | Anyone |
| lead-lifecycle | IAM enforced (commented out) | mgmt group, sa-pubsub, sa-scheduler, sa-gateway-service |
| EQS | Check DAC | — |
| gateway-service | `ingress = "all"` | External + internal |

This asymmetry explains why gateway → retell-service works but gateway → LLS can fail.

## Audit Trail (who changed IAM?)

```bash
gcloud logging read '
protoPayload.methodName="google.iam.v1.IAMPolicy.SetIamPolicy"
AND protoPayload.resourceName:"<SERVICE_NAME>"
' --project=<PROJECT_ID> --limit=20 --freshness=90d \
  --format="table(timestamp,protoPayload.authenticationInfo.principalEmail)"
```

For full binding details, use `--format=json` and inspect `protoPayload.request.policy.bindings`.

**Key actors:**
- `sa-faas-projects@prj-bts-n-seed-tcla3w6yn2.iam.gserviceaccount.com` = Terraform/DAC pipeline
- `gabriel@origin8cares.com` = manual gcloud
- `martin@origin8cares.com` = manual gcloud

## Smoke Test Pattern (post-DAC deploy)

Hit each subgraph independently through the gateway to isolate which service-to-service auth is broken:

```bash
# 1. Gateway alive?
{ __typename }

# 2. Each subgraph (substitute the actual query for each service):
{ lead(uuid: "...") { uuid } }           # → LLS
{ InteractionReportResults(...) { count } }  # → EQS
mutation { runRetellReconciliation(...) }  # → retell-service
```

Compare: if some work and others don't, it's per-service IAM, not gateway auth.

## Gateway Service Account

`sa-gateway-service@prj-sprvsr-d-core-kkomv80zrg.iam.gserviceaccount.com`

This SA must have `roles/run.invoker` on every IAM-enforced service that the Apollo Router routes to.

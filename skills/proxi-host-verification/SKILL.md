---
name: proxi-host-verification
description: Verify Proxi Hermes SSH host identity and record deployed version, deployment time, verifier and evidence. Use after VM recreation, an SSH host-key warning, or a request for current Proxi deployment status.
nav:
  bay: ops
  when: "Proxi SSH host-key verification or deployment evidence lookup."
  when_not: "Other hosts, login credential rotation, or authorization to deploy."
---

# Proxi host verification

Scope: Klever Proxi Hermes only. This procedure does not grant deployment or security-change permission.

## Locate evidence first

Resolve the Klever project-management checkout using the harness workspace map.
Read `general/initiatives/proxi-dev-deploy/deployment-ledger/INDEX.md` and its procedure.
The ledger records observations. It is not a trust root, an SSH bypass, or proof of current state.
Read the historical verification report linked there before independent verification.

## Choose the action

1. Check active Herdr sessions read-only. Do not interrupt writers or concurrent deployments.
2. Read the most recent ledger records, including invalidation and blocked records.
3. Query current VM and boot-disk identity through authenticated GCP APIs.
4. Compare project, zone, instance ID, boot disk ID/creation time, start timestamp and endpoint binding.
5. If unchanged, test the existing approved host trust using strict checking. Never auto-accept a key.
6. If keys or identity changed, perform the independent verification procedure. Stop before any unapproved trust update.
7. Record an immutable observation with verifier, times and hashed evidence. Record failures too.
8. After authenticated access, use `/deploy-identity` contract mode for runtime version claims.

Report host trust, deployment identity and application health separately.
A successful SSH connection does not prove the deployed image or application works.
A cached image tag does not prove the deployment date.

## Approval boundary

This skill's installation authorizes no new security settings, trust-store writes, IAM changes, org-policy changes or deployments.
Obtain required action-time approval for the exact trust update. Describe host, fingerprint and trust-store entry.
Do not bypass restrictions when blocked. Save the evidence and the smallest next action.

## Output

State: current verification result; observed version and digest; deployment date or unknown; verifier and check time; evidence location; remaining action.
Only use VERIFIED for the scope supported by fresh evidence. Historical records stay HISTORICAL.

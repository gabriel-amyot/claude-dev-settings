---
name: supervisr-service-manager
description: "Manage Origin8 service deactivation and reactivation through DAC terraform. Scale-to-zero, comment-out subscriptions, or zero min_instances. Strong guardrails: PROTECTED blacklist, registry status gate, exact-ID confirmation, never-push. Use when user wants to deactivate, reactivate, or check status of O8 legacy services. Triggers on: '/ssm', 'deactivate service', 'shutdown service', 'reactivate service', 'service status', 'O8 teardown', 'deprecation status'."
---

# Supervisr Service Manager (`/ssm`)

Manage Origin8 legacy service deactivation and reactivation through DAC terraform changes. Every change is minimally destructive (scale-to-zero, not destroy) and perfectly reversible.

## Data Files

- **Service Registry:** `tickets/SPV-113/service-registry.yaml` in project-management repo
- **Deprecation Plan:** `tickets/SPV-113/deprecation-plan.yaml` in project-management repo

Read both files at the start of every invocation.

---

## PROTECTED SERVICES (IMMUTABLE BLACKLIST)

The following services MUST NEVER be modified by this skill. Any operation targeting them MUST be refused immediately with the failure message below.

### Supervisr (all 10)
- `lead-lifecycle-service`
- `retell-service`
- `supervisor-compliance-engine`
- `supervisor-query-service`
- `gateway-service`
- `pew`
- `web-dashboard`
- `compliance-ers`
- `auth0-manager`
- `web-site`

### Origin8 (needs-owner / active)
- `call-transfer-service`
- `fnc-warm_transfer_scoring`
- `event-query-service`
- `origin8-web`
- `web-ers`

### Failure message for PROTECTED services
```
BLOCKED: {service-id} is PROTECTED.
Protected services cannot be modified through this skill.
To remove protection, manually edit:
  ~/.claude-shared-config/skills/supervisr-service-manager/SKILL.md
and remove the entry from the PROTECTED_SERVICES list.
```

To change the PROTECTED list, the user must manually edit THIS file. The skill cannot programmatically unprotect a service.

---

## Safety Rules (ALL MANDATORY)

1. **Never merge.** Push branch and create MR via `/gitlab`, but never merge. User merges manually.
2. **Never use `gcloud` to mutate.** No `gcloud run services delete`, `gcloud functions delete`, `gcloud app services delete`, or any destructive gcloud command. `gcloud` is permitted ONLY for read-only operations: `describe`, `list`, `logs read`.
3. **All mutations go through DAC terraform.** Edit `.tf` files in the DAC repo. Terraform apply happens via CI/CD pipeline after the MR is merged.
4. **Registry status gate.** Only services with `status: approved_for_deactivation` can be targeted for deactivation. Any other status (`active`, `unknown`, `deprecated`, `deactivated`) = blocked.
5. **Exact-ID confirmation.** Before applying changes, the user must type the exact service ID. Not "YES", not "all", not "confirm". The exact ID string.
6. **DAC repo must exist locally.** If `dac_repo_path` is null or the path does not exist on disk, refuse and prompt: "DAC repo not found locally. Use `/gitlab` to clone it first."
7. **Store exact revert recipe.** Every deactivation must record the exact revert steps in the registry so the change can be perfectly reversed.

---

## Phase Workflow

### Phase 1: Load
Read `tickets/SPV-113/service-registry.yaml` and `tickets/SPV-113/deprecation-plan.yaml`.

Display a status dashboard:
```
=== Supervisr Service Manager ===

Registry: {total} services ({active} active, {approved} approved for deactivation, {deactivated} deactivated, {unknown} unknown)

Wave Status:
  Wave 1 ({wave-1-name}): {status} — {n}/{total} services processed
  Wave 2 ({wave-2-name}): {status} — {n}/{total} services processed
  Wave 3 ({wave-3-name}): {status} — {n}/{total} services processed

Available operations:
  1. Deactivate a service
  2. Reactivate a service
  3. Show service details
  4. Show wave details
```

### Phase 2: Select
User picks a service ID and operation (deactivate or reactivate).

### Phase 3: Validate
Run ALL checks. Any failure = hard block.

1. **PROTECTED check:** Is the service in the PROTECTED list? If yes, print the failure message and STOP.
2. **Status check:** Is the service status `approved_for_deactivation` (for deactivation) or `deactivated` (for reactivation)? If not, STOP.
3. **DAC repo check:** Does `dac_repo_path` exist and point to an actual directory on disk? If not, prompt to use `/gitlab` and STOP.
4. **Terraform file check:** Does the `tf_file` exist within the DAC repo? Read it and confirm it matches expected structure.

### Phase 4: Diff Preview
Read the actual terraform file. Show before/after with exact line numbers. Show what will change and what will be preserved.

For deactivation, show the apply recipe.
For reactivation, show the revert recipe (from the `revert` block in the registry).

### Phase 5: Confirm
Display:
```
To proceed, type the exact service ID: {service-id}
Revert recipe will be stored in the registry.
This commit will NOT be pushed. You push manually.
```

Wait for the user to type the exact service ID. Any other input = abort.

### Phase 6: Apply + Commit + Push + MR
1. Navigate to the DAC repo directory.
2. **Sync with remote first:** `git checkout dev && git fetch origin && git pull origin dev`. DAC repos flow `dev → uat → main`. Always branch from `dev`, never `main`. This is mandatory.
3. Check the DAC repo is clean (`git status`).
4. Create a new branch: `SPV-113-deactivate-{service-id}-{YYYYMMDD}` (or `SPV-113-reactivate-...`).
4. Apply the terraform change using the Edit tool.
5. Commit with message: `SPV-113: Deactivate {service-id} (scale to zero)` or similar.
6. Push the branch: `git push -u origin {branch-name}`.
7. Create MR via `/gitlab` skill **targeting `dev`** (not `main`). Title: `SPV-113: Deactivate {service-id}`. Description includes the revert recipe.
8. **Do NOT merge.** User merges manually after review. After dev merge, DAC pipeline applies to dev. User then promotes dev → uat → main.

### Phase 7: Update Tracking
1. Update `service-registry.yaml`:
   - Set `status: deactivated` (or back to `approved_for_deactivation` for reactivation)
   - Set `deactivated_at` (or clear it)
   - Set `branch` to the branch name
   - Populate `revert` block with exact revert recipe (for deactivation)
   - Clear `revert` block (for reactivation)
2. Update `deprecation-plan.yaml`:
   - Set the service's status to `mr_open` (or back to `pending` for reactivation)
   - Set `branch` and `mr_url`
3. Commit these tracking updates to the project-management repo.

### Phase 8: Report
Display summary:
```
=== Deactivation Complete ===

Service: {service-id}
Branch: SPV-113-deactivate-{service-id}-{YYYYMMDD}
DAC Repo: {dac_repo_path}
MR: {mr_url}

Next steps:
  1. Review the MR at {mr_url}
  2. Merge when ready. DAC pipeline runs terraform apply automatically.

To revert later:
  /ssm → reactivate → {service-id}
```

---

## Deactivation Methods

### Method: `cloud_run_scale_zero`
**Applies to:** Cloud Run services (e.g., talkdesk-service)

**Apply:** Insert two lines inside the module block, after `limits {}` or at the end of the resource block:
```hcl
  min_instances = 0
  max_instances = 0
```

**Revert recipe to store:**
```yaml
revert:
  action: remove_lines
  file: {tf_file}
  lines:
    - "  min_instances = 0"
    - "  max_instances = 0"
```

**Effect:** Cloud Run keeps the service definition but runs 0 instances. No traffic served. No resources deleted. Service account, secrets, IAM all preserved.

### Method: `pubsub_subscription_comment`
**Applies to:** Cloud Functions with PubSub push subscriptions (salesforce-updater, salesforce-policy-reconciler, lead-dispatcher-function)

**Apply:** Prefix every line of the `resource "google_pubsub_subscription"` block with `# `. This matches the existing pattern in `pss-transcript-analysis-uploader.tf` where the subscription is already commented out.

**Revert recipe to store:**
```yaml
revert:
  action: uncomment_block
  file: {tf_file}
  start_marker: '# resource "google_pubsub_subscription"'
  end_marker: "# }"
```

**Effect:** Terraform destroys the PubSub push subscription. Messages stop flowing to the function. The function itself, its code, its service account, its IAM all remain. Re-running terraform after revert recreates the subscription.

### Method: `appengine_min_instances_zero`
**Applies to:** AppEngine services (event-receiver)

**Apply:** Replace the `min_instances` lookup map to empty:
```
BEFORE: min_instances = lookup({ dev = 1, uat = 1, prod = 1 }, module.faas.environment_short_name, 0)
AFTER:  min_instances = lookup({}, module.faas.environment_short_name, 0)
```

**Revert recipe to store:**
```yaml
revert:
  action: replace_line
  file: {tf_file}
  find: "      min_instances = lookup({}, module.faas.environment_short_name, 0)"
  replace: "      min_instances = lookup({ dev = 1, uat = 1, prod = 1 }, module.faas.environment_short_name, 0)"
```

**Effect:** AppEngine scales to 0 instances when idle. The service, its version, its config all remain.

---

## Missing DAC Repos

For services without a locally cloned DAC repo (`dac_repo_path` is null):

1. Tell the user: "DAC repo not found locally for {service-id}. Use `/gitlab` to clone {dac_repo} first."
2. Do NOT attempt deactivation.
3. After the user clones the repo, they should update `dac_repo_path` in the registry and re-run `/ssm`.

---

## Reactivation Flow

Same 8 phases as deactivation, but:
- Phase 3: Validates status is `deactivated` and `revert` block exists in registry
- Phase 4: Shows the revert diff (applying the stored revert recipe)
- Phase 6: Applies the revert, creating branch `SPV-113-reactivate-{service-id}-{YYYYMMDD}`
- Phase 7: Sets status back to `approved_for_deactivation`, clears `deactivated_at` and `revert`

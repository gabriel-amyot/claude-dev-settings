<!-- markdownlint-disable MD013 -->

# Troubleshooting

## Contents

- Analyzing GCP permission-denial logs (CSV)
- Mapping permissions to IAM roles
- Adding missing roles to the IAM matrix
- Diagnosing non-existent role errors
- Finding correct IAM role names

## Analyzing GCP permission-denial logs (CSV)

When users report permission errors from compute instances, GCP logs can be exported as CSV files. Files are typically named `downloaded-logs-*.csv`.

### Key CSV columns

- `protoPayload.authorizationInfo.permission` — the specific permission that was denied
- `protoPayload.methodName` — the API method that was called
- `protoPayload.serviceName` — the GCP service (e.g., `cloudaicompanion.googleapis.com`)
- `resource.labels.service` — the service label

### Extracting denied permissions

```bash
# Extract all unique permission denials
grep -oP "Permission '[^']+' denied" downloaded-logs-*.csv | sort -u

# Or extract from the permission column directly
awk -F',' 'NR>1 {print $1}' downloaded-logs-*.csv | grep -v '^$' | sort -u
```

### Interpreting the results

- Multiple denials from the same service family (e.g., `cloudaicompanion.*`) suggest a missing role covering that service.
- Note which service accounts are being denied — check the resource or identity columns if available.
- Cross-reference with `compute_engine_res.tf` to determine which `service_account_key` the affected instance uses.

## Mapping permissions to IAM roles

### Common permission-to-role mappings

| Permission pattern | Required role | Purpose |
|---|---|---|
| `cloudaicompanion.*` | `roles/cloudaicompanion.user` | Gemini/Duet AI features |
| `consumerprocurement.entitlements.*` | `roles/consumerprocurement.entitlementViewer` | GCP service entitlements |
| `cloudasset.assets.searchAllResources` | `roles/cloudasset.viewer` | Search and discover GCP resources |
| `storagetransfer.jobs.*` | `roles/storagetransfer.viewer` | View Storage Transfer Service jobs |
| `logging.settings.*` | `roles/logging.viewer` | Read logging configuration |
| `securitycenter.*` | `roles/securitycenter.notificationConfigViewer` | Security Command Center metadata |

### How to look up unfamiliar permissions

1. Extract the service name from the permission string. Format is `{service}.{resource}.{verb}`.
2. Visit the service-specific roles page: `https://docs.google.com/iam/docs/roles-permissions/{service-name}`
3. Search the page for the denied permission to see which roles contain it.
4. Choose the least-privileged role that includes the needed permission.

## Adding missing roles to the IAM matrix

Once you have identified which permissions are missing and which roles grant them:

1. Determine which service account needs the role by checking which `service_account_key` the affected compute instance uses in `compute_engine_res.tf`.

2. Add the role to the appropriate IAM matrix block in `project_iam.tf`. Include a comment explaining why the role is needed:

   ```hcl
   {
     resource_id = [
       module.datasophia-gcp-project.project_id
     ]
     role = [
       "roles/aiplatform.user",
       # Required for Gemini/Duet AI access from compute instances
       "roles/cloudaicompanion.user",
     ]
     identity = [
       "serviceAccount:${module.datasophia-gcp-iam-service-account["sa-authorized"].email}",
       "serviceAccount:${module.datasophia-gcp-iam-service-account["sa-authorized2"].email}",
     ]
   }
   ```

3. Commit and push. The GitLab CI pipeline will apply the new permissions.

## Diagnosing non-existent role errors

When Terraform fails with a role that does not exist, the Google Cloud provider produces a misleading error:

```
Error: Request `Create IAM Members roles/consumerprocurement.consumer
serviceAccount:sa-authorized2@prj-n-rnd-newton-i9oa96j4mv.iam.gserviceaccount.com
for project "prj-n-rnd-newton-i9oa96j4mv"` returned error: ...
googleapi: Error 400: Role roles/ROLE_NAME is not supported for this resource., badRequest
```

The message says "is not supported for this resource," which could mean:

1. The role does not exist at all (most common).
2. The role exists but cannot be applied to this resource type (project vs organization vs folder).

In practice, this almost always means the role name is incorrect or non-existent.

## Finding correct IAM role names

Do not guess role names from the permission name. Common mistakes:

- `roles/consumerprocurement.consumer` does not exist; the correct role is `roles/consumerprocurement.entitlementViewer`.
- `roles/logging.configViewer` does not exist; the correct role is `roles/logging.viewer`.

### Lookup workflow

1. Extract the service name from the permission (e.g., `consumerprocurement.entitlements.list` -> `consumerprocurement`).
2. Visit `https://docs.google.com/iam/docs/roles-permissions/{service-name}` to find the exact role IDs.
3. Search for the specific permission to see which roles contain it.
4. Choose the least-privileged role.

### Example

```
# Permission denied: consumerprocurement.entitlements.list
# 1. Service name: "consumerprocurement"
# 2. Visit: https://docs.google.com/iam/docs/roles-permissions/consumerprocurement
# 3. Find that consumerprocurement.entitlements.list is in:
#    - roles/consumerprocurement.entitlementViewer (read-only, recommended)
#    - roles/consumerprocurement.entitlementManager (read-write)
#    - roles/consumerprocurement.procurementAdmin (full access)
# 4. Choose roles/consumerprocurement.entitlementViewer (least privilege)
```

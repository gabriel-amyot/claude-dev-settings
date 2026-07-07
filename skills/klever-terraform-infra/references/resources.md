<!-- markdownlint-disable MD013 -->

# Resource Patterns

## Contents

- Klever-specific networking
- Base files in `terraform/`
- Extended files in `terraform_extended/`

## Klever-specific networking

Klever does not use the generic Datasophia subnetwork examples as-is.
When editing Klever repositories, treat the imported subnetwork catalog in
`terraform/import.tf` as the source of truth, specifically
`local.datasophia_required_resources`.

This matters most when updating or adding:

- compute templates
- firewall templates

### Subnetwork catalog used by Klever

Each entry in `local.datasophia_required_resources` has two distinct names:

- the **map key** (e.g. `sub-back1`, `usea1-back`) is arbitrary and local; it is
  only the handle other files use to reference the import. Match whatever the
  target repo already uses rather than the catalog labels below.
- the **`short_name`** MUST equal the real GCP subnet name; the lookup fails if
  it does not.

These differ across repos. The generic template
(`datasophia-glb-template-dac`) uses keys `sub-front1`/`sub-back1` with
`short_name` `front1`/`back1`, while `dac-gcp-cst-klvdb1` uses key `usea1-back`
with `short_name` `usea1-back`. Treat the list below as role labels, not exact
keys — confirm the actual keys and `short_name`s in the repo's `import.tf`.

To consume an imported subnet for private-network wiring (Cloud SQL
`private_network`, firewall `network_id`, etc.), read
`module.datasophia-gcp-utils-search-resources["<key>"].data.network` (other
attributes available include `.data.name`, `.data.region`).

Roles seen across Klever repos:

- `sub-scraping` role: imported from `env-main`; use for compute workloads that
  do web scraping so blacklisting risk is isolated from the rest of Klever's
  services.
- `usea1-front` role: imported from `env-main`; front-end subnet in `us-east1`.
- `usce1-front` role: imported from `env-main`; front-end subnet in
  `us-central1`.
- `usea1-back` role: imported from `env-main`; back-end subnet in `us-east1`.
- `usce1-back` role: imported from `env-main`; back-end subnet in
  `us-central1`.
- `usea1-prime` role: imported from `rnd-main`; prime subnet for RND/IAC in
  `us-east1`.
- `usce1-prime` role: imported from `rnd-main`; prime subnet for RND/IAC in
  `us-central1`.

### Files that must stay consistent

When subnetworks change, update the compute files and the firewall file
together.

For compute templates, verify the subnetwork-driven fields in:

- `terraform_extended/compute_engine_cos_res.tf`
- `terraform_extended/compute_engine_res.tf`

If another repo places a compute-engine template under `terraform/`, apply the
same rule there too.

Fields to verify:

- `region`
- `subnet_key`
- `subnetwork_project_key`
- `subnetwork`
- `subnetwork_project`

For firewall templates, verify:

- `terraform_extended/firewall_res.tf`
- fields `network_id` and `network_core_name`

### Practical rules

- Use `sub-scraping` for any DAC, env IAC, or RND IAC compute engine that does
  web scraping.
- Use the `*-front` subnetworks for DAC front-end workloads.
- Use the `*-back` subnetworks for DAC back-end workloads.
- Use the `*-prime` subnetworks for RND/IAC workloads that belong on the
  `rnd-main` network.
- Derive `region` from the imported subnetwork data when possible instead of
  hardcoding a region that can drift from the selected subnet.
- Keep the imported project key consistent with the subnet family:
  - `env-main` for scraping, front, and back subnetworks
  - `rnd-main` for prime subnetworks

### Copy rule for compute templates

If you add any `compute_engine_*.tf` files to a Klever repo, also copy or adapt
the companion firewall template so the network references stay consistent.
Do not add compute templates in isolation.

## Base files in `terraform/`

### `project_res.tf`

Use this file only in repos that create the project locally (`iac`, `rnd`).

Key patterns:

- `module "datasophia-gcp-project"` is the root project wrapper.
- `api_services` is the authoritative list of enabled APIs.
- follow-up locals expose `module.datasophia-gcp-project.api_services[...]` for use in `depends_on`.
- `rnd` adds `google_project_service_identity` for selected APIs that need service agents created eagerly.

Edit this file when:

- enabling a new API
- changing shared-network mode or VPCSC mode
- needing a new `datasophia_api_ref_*` dependency local

### `import.tf`

Use this file for everything imported from outside the current Terraform-created scope.

Key locals:

- `datasophia_required_projects`
- `datasophia_required_resources`
- `datasophia_required_other_service_account`
- `datasophia_required_group`

Key modules/data sources:

- `datasophia-gcp-utils-search-project-basic`
- `datasophia-gcp-utils-search-resources`
- `google_cloud_identity_group_lookup`

Important:

- In `dac`, customize `default-prj` first.
- Resource type strings must match the existing search-resource taxonomy.
- Imported Google-managed service accounts are kept in `datasophia_required_other_service_account`.

### `group_cloud_identity_res.tf`

This file creates project-scoped Cloud Identity groups.

Local object shape:

- `short_name`
- `description`

Module behavior:

- level is `project`
- `core_name` usually comes from the local project module or imported project naming context
- `datasophia_reference` is wired to the source repository variable

### `group_cloud_identity_membership.tf`

This file defines group membership as a matrix.

Pattern:

- each entry has a `group_key`
- `members_per_env` maps env names to member definitions
- each member value contains:
  - `email`
  - `role` list, usually `["MEMBER"]`

`group_key` can refer to:

- `this:<group-key>`
- `import:<group-key>`

Use this file when nesting project groups inside imported org or shared-network groups.

### `service_account_res.tf`

This file creates service accounts and optionally service-account keys.

Common fields:

- `short_name`
- `description`
- either `project_id` or `project_key` depending on repo
- `create_key`

Patterns:

- `datasophia-gcp-iam-service-account` creates the account
- `datasophia-gcp-iam-key-service-account` is filtered to `create_key == true`
- comments often mark optional service accounts for workflows or Cloud Run

Be careful:

- short-name limits matter
- DAC and RND shapes are not identical
- if `create_key = true`, a matching secret is usually expected in `terraform_extended/secret_res.tf`

### `project_iam.tf`

This file applies project-level roles.

Pattern:

- define `datasophia_iam_roles_per_env_project`
- define `datasophia_iam_matrix_project`
- flatten with `setproduct` and `chunklist`
- resolve members/resources inside `google_project_iam_member`

Use this file for:

- project-wide roles on the local project
- project-wide roles on imported projects
- Google-managed service-account grants
- workflow, Cloud Run, and compute platform permissions

In `dac`, the target project is usually imported, not `this`.

### `service_account_iam.tf`

This file applies IAM directly on service accounts.

Pattern:

- define a matrix for service-account resources
- feed it to `datasophia-gcp-iam-matrix-utils`
- create `google_service_account_iam_member`

Use it when a group or another service account needs `roles/iam.serviceAccountUser` or similar access on a created/imported service account.

## Extended files in `terraform_extended/`

These files ship in `terraform_extended/` in the Datasophia templates. To use
one, copy it into `terraform/` and adapt it there (see SKILL.md step 2); the
paths below point to the template source, not where the active file should end
up.

### `bucket_res.tf`

This file uses `datasophia-gcp-srv-storage`.

Typical fields:

- `short_name`
- `storage_class`
- `location`
- `labels`
- `project_id` or `project_key`
- optional `bucket_retention_policy`
- optional `bucket_lifecycle_rules`

Keep retention values and lifecycle rules in the local object. The module call already forwards them with `try(...)`.

### `bucket_iam.tf`

This file uses the IAM matrix helper plus `google_storage_bucket_iam_member`.

Use it when:

- granting object-level or bucket-level access to local groups or service accounts
- granting access to imported buckets through `resource_key = "import:<key>"`

### `dataset_res.tf`

This file uses native `google_bigquery_dataset`.

Typical fields:

- `short_name` or dataset id
- `friendly_name`
- `location`
- `labels`
- `project_id` or `project_key`
- `description`

Datasets depend on `local.datasophia_api_ref_bigquery` in repos that create the project.

### `dataset_iam.tf`

This file uses the IAM matrix helper plus native `google_bigquery_dataset_iam_member`.

Key detail:

- it parses dataset IDs from resource IDs with `regex(...)`

If you change the source of the dataset reference, preserve the parsing logic.

### `secret_res.tf`

This file uses `datasophia-gcp-srv-secret`.

Typical fields:

- `short_name`
- `secret_data`
- sometimes `project_id` or `project_key`

Patterns:

- manual secrets live in `datasophia_secret_res`
- automatic service-account-key secrets live in `datasophia-gcp-srv-secret-auto`
- auto-created secrets are usually tied to `create_key == true` in `service_account_res.tf`

### `secret_iam.tf`

This file merges manual and auto-created secrets, then applies IAM with native `google_secret_manager_secret_iam_member`.

Key detail:

- it builds `datasophia_secret_res_merged = merge(module.datasophia-gcp-srv-secret, module.datasophia-gcp-srv-secret-auto)`
- it parses project and secret ID from the secret manager resource ID with `regex(...)`

### `firewall_res.tf`

This file uses `datasophia-gcp-net-firewall`.

Typical fields:

- `description`
- `short_name`
- `direction`
- `source_tags`
- `target_tags`
- per-environment `allow`
- optional `source_ranges`
- optional `destination_ranges`
- optional `source_service_accounts`
- optional `target_service_accounts`

It usually targets the shared-network host project, not the service project itself.

### `workflow_res.tf`

This file uses native `google_workflows_workflow`.

Prerequisites usually include:

- uncommenting workflow service accounts in `service_account_res.tf`
- enabling `workflows`, `workflowexecutions`, `eventarc`, `eventarcpublishing`, and `pubsub` APIs
- exposing matching API-ref locals
- copying or editing `dependencies/workflow/*`

Typical fields:

- `short_name`
- `description`
- `deletion_protection`
- `service_account`
- `source_contents = templatefile(...)`

### `eventarc_res.tf`

This file uses native `google_eventarc_trigger`.

Pattern:

- one resource block per trigger
- `name` usually derives from the workflow name
- `matching_criteria` describe the event
- `destination.workflow` targets `google_workflows_workflow.this[...]`

Workflow/Eventarc changes are coordinated changes, not single-file edits.

### `monitoring_logging_metric_res.tf`

This file uses native `google_logging_metric`.

Pattern:

- local objects contain `name`, `bucket_key`, `template`, and `description`
- `filter` comes from `templatefile("../dependencies/monitoring/...")`

### `monitoring_notification_channel_res.tf`

This file uses native `google_monitoring_notification_channel`.

Typical pattern:

- target a separate monitoring project, often imported as `cmm-monit`
- define email notification channels

If the imported monitoring project key is missing, add it in `import.tf` first.

### `monitoring_alert_res.tf` / `monitoring_alert_alert_res.tf`

These files use native `google_monitoring_alert_policy`.

Pattern:

- depend on the logging metric
- target the imported monitoring project
- wire notification channels
- use a threshold condition against the custom logging metric

The DAC filename variant is a naming inconsistency, not a different model.

### `cloud_run_res.tf`

This file uses native `google_cloud_run_v2_service`.

Common fields:

- `service_name`
- `location`
- `description`
- `container_port`
- `ingress`
- `invoker_iam_disabled`
- `min_instance_count`
- `max_instance_count`
- `cpu`
- `memory`
- `cpu_idle`
- `startup_cpu_boost`
- `image`
- optional `service_account`
- optional `startup_probe`
- optional `liveness_probe`
- per-environment `deletion_protection` in DAC

Patterns:

- timeouts are intentionally reduced to `3m`
- image paths are often built from imported `cmm-images`
- some repos attach a service account inside `template`

### `cloud_run_iam.tf`

This file uses the IAM matrix helper plus `google_cloud_run_v2_service_iam_member`.

Resource keys refer to the keys of `local.datasophia_cloud_run_res`.

### `cloud_run_job_res.tf`

This file uses native `google_cloud_run_v2_job` and `google_cloud_scheduler_job`.

Pattern:

- one local object drives both the job and its schedule
- Cloud Scheduler calls the `:run` endpoint with OAuth
- the example mounts a secret-backed volume

Treat the mounted secret name and service-account wiring as required companion edits, not independent strings.

### `compute_engine_res.tf`

This file uses native `google_compute_instance`.

Typical fields:

- `status`
- `short_name`
- `subnet_key`
- `region`
- `zone`
- `description`
- `service_account_key`
- `network_tag`
- `machine_type`
- `deletion_protection`
- `use_cpe_schedules`

Patterns:

- `for_each` filters to active objects only
- Ubuntu images come from `data.google_compute_image`
- startup, shutdown, and cloud-config metadata come from dependency templates
- lifecycle ignores image and sometimes machine-type changes

### `compute_engine_policy_res.tf`

This file creates compute instance schedules and snapshot policies with native `google_compute_resource_policy`.

Pattern:

- schedules are environment-specific locals
- `random_string` resources are used to force name changes when schedules change
- `for_each` is usually by region

### `compute_engine_cos_res.tf`

This file models COS/container-on-VM instances with native compute resources plus Datasophia helpers.

Typical extra fields:

- `use_automatic_cleanup_images`
- `container_restart_policy`
- `data_disk_size`
- `container`
- `volumes`

Patterns:

- the instance name is precomputed in a local map
- metadata uses `module.datasophia-gcp-utils-container[*].metadata_value`
- a separate persistent disk is created and attached
- project metadata keys store the COS image name
- commented `terraform_data` resources document a former operational pattern for konlet/image cleanup

Preserve the separation between compute instance, data disk, metadata item, and container declaration module.

### `compute_engine_cos_policy_res.tf`

This mirrors `compute_engine_policy_res.tf` for COS instances.

Keep the COS-specific schedule locals and resource names separate from the non-COS compute policies.

### `address_res.tf`

This file uses native `google_compute_address`.

Typical fields:

- `name`
- `project`
- `subnetwork`
- `address_type`
- `region`
- optional `address`

The examples are for internal addresses tied to imported subnetworks.

### `mysql_res.tf`

This file uses native Cloud SQL resources plus the secret wrapper module.

Pattern:

- `datasophia_sql_database_instances` defines per-instance config
- each instance contains env-specific nested settings for tier and deletion protection
- `datasophia_sql_database_users` links users to instances
- random passwords are generated for both users and root
- user passwords are stored via `datasophia-gcp-srv-secret`
- instances use private IP and `ssl_mode = "ENCRYPTED_ONLY"`

Pay attention to:

- `servicenetworking.googleapis.com` prerequisite
- imported project and network references
- dynamic `database_flags`
- backup and maintenance blocks

### `mysql_certificates_res.tf`

This file creates SQL client/server certificates and stores them in Secret Manager.

Pattern:

- flatten instance x certificate-type combinations into a list
- map that list back into a `for_each`
- create `server-ca`, `client-cert`, and `client-key` secrets for every SQL instance

When adding a new SQL instance, certificate secrets follow automatically if this file is wired correctly.

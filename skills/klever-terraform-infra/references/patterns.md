<!-- markdownlint-disable MD013 -->

# Shared Patterns

## Contents

- Pipeline-injected symbols
- Wrapper-first model
- Base vs extended files
- Import and lookup conventions
- IAM matrix grammar
- Naming and shared locals
- API activation and dependencies
- Feature toggles and status fields
- Observed repo gotchas

## Pipeline-injected symbols

Several symbols these repos reference are **injected by the GitLab CI/CD pipeline** and are declared **nowhere** in the repo itself:

- the Google `provider` and the `backend` configuration.
- every `var.faas_*` variable (for example `var.faas_gcp_environment_short_name`, `var.faas_composite_major_name`, `var.faas_gws_customer_domain_name`).
- the shared `local.default` object (for example `local.default.labels`, `local.default.environment_letter`).
- the utility modules `module.datasophia-gcp-utils-regions-code` and `module.datasophia-gcp-utils-env-letter`.

Consequences:

- Never create or redeclare them. Grepping a repo finds usages with zero declarations, and that is correct, not a missing file.
- Referencing them in new code is the expected pattern. Use them live — do not stub or comment them out. (The `datasophia-glb-template-dac` template comments `module.datasophia-gcp-utils-regions-code` out in `terraform_extended/mysql_res.tf` as "not defined in the provided context" and replaces `local.default.labels` with `{}`; that is a template artifact. A real repo such as `dac-gcp-cst-klvdb1` uses both live, which is what new code should do.)
- Because these symbols resolve only inside the pipeline, `terraform init`, `validate`, `plan`, and `apply` all fail locally. `terraform fmt` is the only safe local check (see SKILL.md step 6).

## Wrapper-first model

Datasophia modules are thin Terraform wrappers over Google Cloud concepts, not a separate platform model. In these repos:

- Common platform primitives are usually wrapped:
  - projects
  - search/lookups
  - groups
  - service accounts
  - IAM matrix expansion
  - storage buckets
  - secrets
  - firewall
  - COS container metadata
- Many product resources stay native `google_*`:
  - BigQuery datasets and dataset IAM
  - Cloud Run services, jobs, and IAM
  - Workflows
  - Eventarc
  - Logging metrics and alert policies
  - Compute Engine
  - Cloud SQL

Prefer the abstraction level already present in the target file.

## Base vs extended files

The repos are deliberately split:

- `terraform/`: the actual root module. The pipeline applies this folder.
- `terraform_extended/`: a **temporary holding area** for optional files shipped with the Datasophia templates. It is not a second root module.

To enable an optional resource, **copy the relevant file from `terraform_extended/` into `terraform/`** (then adapt it), rather than editing it in place. Once copied, everything lives in the single `terraform/` root module, so locals and resources resolve across what used to be separate files — for example a `for k, v in <resource>` local in `import.tf` can be built from a resource declared in another file in `terraform/`, as `dac-gcp-cst-klvdb1` does to build `local.datasophia_google_sql_database_instance_service_account_email_address` in `import.tf` from `google_sql_database_instance.this` in `mysql.tf`. A fully built-out repo such as `dac-gcp-cst-klvdb1` therefore has only `terraform/` and no `terraform_extended/`.

If a change needs new APIs, imported projects/resources, or service accounts, wire those prerequisites into `terraform/` alongside the copied feature file.

## Import and lookup conventions

Cross-project and cross-resource references are centralized in `terraform/import.tf`.

The usual flow is:

1. Define imported projects in `local.datasophia_required_projects`.
2. Define imported resources in `local.datasophia_required_resources`.
3. Define imported groups or Google-managed service accounts in the matching locals.
4. Resolve them through:
   - `module.datasophia-gcp-utils-search-project-basic`
   - `module.datasophia-gcp-utils-search-resources`
   - `data.google_cloud_identity_group_lookup.this`

Common imported resource types:

- `bucket`
- `secret`
- `serviceAccount`
- `subnetwork`
- `topic`
- `address`
- `dataset`

Use imported lookups instead of hardcoding full IDs when the repo already follows that pattern.

## IAM matrix grammar

The most important house pattern is the IAM matrix.

Member keys follow:

- `this:group:<key>`
- `this:serviceAccount:<key>`
- `import:group:<key>`
- `import:serviceAccount:<key>`
- `import:otherServiceAccount:<key>`

Resource keys follow one of these shapes depending on the file:

- project IAM:
  - `this`
  - `import:<project-key>`
- resource IAM:
  - `this:<resource-key>`
  - `import:<resource-key>`

Files then feed a list of matrix entries into `module "datasophia-gcp-iam-matrix-utils"` and use the resulting `datasophia_iam_map` for `for_each`.

Do not replace this with hand-written duplicated IAM resources unless the file already does so.

Environment scoping usually follows:

- `all_env` for defaults
- `prod`, `pre`, `dev`, or `noe` for overrides

The role list is usually built with `concat(lookup(..., "all_env", []), lookup(..., var.faas_gcp_environment_short_name, []))`.

## Naming and shared locals

Naming is assembled rather than hardcoded.

Common sources:

- `module.datasophia-gcp-project.project_id`
- `module.datasophia-gcp-project.core_name`
- `module.datasophia-gcp-utils-env-letter.environments-map[...]`
- `module.datasophia-gcp-utils-regions-code.regions-code-map[...]`
- `local.default.labels`
- `local.default.environment_letter`

Common prefixes:

- `run-` for Cloud Run services
- `job-` for Cloud Run jobs and Cloud Scheduler jobs
- `wfl-` for Workflows
- `trg-` for Eventarc triggers
- `cpe-` for compute instances
- `dsk-` for disks
- `isc-` for instance schedule policies
- `snp-` for snapshot schedule policies
- `grp-` or `grp-prj-` for Cloud Identity groups

Preserve the existing `join("-", [...])` style and the local key names that drive it.

## API activation and dependencies

In repos that create the project locally, `terraform/project_res.tf` is the API switchboard.

The pattern is:

1. Add the API string to `api_services`.
2. Expose a local reference such as `local.datasophia_api_ref_secretmanager`.
3. Use that reference in `depends_on` where the resource must wait for API activation.

Examples already present in comments:

- `secretmanager.googleapis.com`
- `pubsub.googleapis.com`
- `eventarc.googleapis.com`
- `eventarcpublishing.googleapis.com`
- `workflowexecutions.googleapis.com`
- `workflows.googleapis.com`
- `run.googleapis.com`
- `artifactregistry.googleapis.com`
- `servicenetworking.googleapis.com`

`rnd` also forces service-agent creation with `google_project_service_identity` for some APIs. Reuse that pattern when the service account must exist before IAM is granted.

## Feature toggles and status fields

The templates intentionally keep many optional features dormant.

Patterns to preserve:

- commented example objects in locals
- commented prerequisite service accounts
- commented imported projects/resources/groups
- `status = "ACTIVE"` / `"INACTIVE"` for compute resources
- per-environment deletion-protection maps
- `use_cpe_schedules` and related booleans

For compute resources, the `for_each` usually filters on `if v.status == "ACTIVE"`. To add a new machine, extend the local map first and leave the toggle logic intact.

## Templatefile-driven resources

If a file uses `templatefile("../dependencies/...")`, the dependency payload is part of the feature.

Examples:

- workflow definitions under `dependencies/workflow`
- startup/shutdown scripts under `dependencies/scripts`
- logging filters under `dependencies/monitoring`

When a resource change needs new template variables or new script content, edit the dependency file in the same change.

## Observed repo gotchas

- `dac` does not create the target project locally. Many `this` project assumptions from `iac` or `rnd` will be wrong there.
- `rnd` contains an inconsistent `sa_cloud_run_invoker` object shape in `terraform/service_account_res.tf`; inspect the target file before copying that object.
- Cloud Run examples differ:
  - `rnd` points to the local project and constructs Artifact Registry image paths from imported `cmm-images`.
  - `dac` points to `default-prj` and can set `template.service_account`.
- Monitoring examples require an imported monitoring project key such as `cmm-monit`; those entries are commented until needed.
- Workflow and Eventarc examples require coordinated edits across service accounts, APIs, imports, and dependency templates.

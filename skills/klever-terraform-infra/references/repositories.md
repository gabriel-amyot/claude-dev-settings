<!-- markdownlint-disable MD013 MD060 -->

# Repository Map

## Contents

- Shared layout
- Repository roles
- Datasophia module catalog
- Key cross-repo differences

## Shared layout

All three repositories use the same high-level split:

- `terraform/`: project bootstrap, imported lookups, service accounts, Cloud Identity groups, and IAM.
- `terraform_extended/`: optional or workload-specific resources.
- `dependencies/`: templates and scripts consumed through `templatefile()`.
- `README.md`: usage notes plus generated Terraform docs.

The templates are a mix of:

- Datasophia wrapper modules hosted at `cicd.prod.datasophia.com/grp-comp/...`
- Native `google_*` resources for GCP services not wrapped, or where the repo chose to stay close to the provider

## Repository roles

### `datasophia-glb-template-iac`

- Standard project template.
- Creates the GCP project locally via `module "datasophia-gcp-project"`.
- Contains the cleanest baseline for project bootstrap, imports, service accounts, groups, basic IAM, buckets, datasets, secrets, workflows, Eventarc, firewall, and monitoring.
- Good default reference for wrapper-first edits.

### `datasophia-glb-template-rnd`

- R&D-oriented project template.
- Creates the GCP project locally via `module "datasophia-gcp-project"`.
- Extends the standard pattern with broader API enablement, Vertex AI-related service-agent creation, Cloud Run, Cloud Run jobs, Compute Engine, COS/container-on-VM patterns, internal addresses, and compute scheduling policies.
- Good reference when the change involves compute, containers, notebooks, or heavier platform features.

### `datasophia-glb-template-dac`

- Template for resources that target another project, not a project created in this repo.
- Does not contain `terraform/project_res.tf`.
- Relies on `terraform/import.tf` and the `default-prj` imported project key for most real resources.
- Contains the richest examples for DAC-style naming and Cloud SQL/MySQL.
- High-risk area: many files assume `default-prj` has been customized from the placeholder `CHANGE_ME` values.

## Datasophia module catalog

These modules are the stable building blocks that appear across the repos.

| Module | Typical purpose | Seen in |
|---|---|---|
| `datasophia-gcp-project` `~>6.0` | Create a project, enable APIs, expose API refs | `iac`, `rnd` |
| `datasophia-gcp-utils-search-project-basic` `~>1.0` | Resolve another project by env/major/minor | all |
| `datasophia-gcp-utils-search-resources` `~>1.0` | Resolve an external resource by type/short name/project | all |
| `datasophia-gcp-cloud-identity-group` `~>1.0` | Create project-scoped Cloud Identity groups | all |
| `datasophia-gcp-cloud-identity-group-membership` `~>1.0` | Apply Cloud Identity group membership matrices | all |
| `datasophia-gcp-iam-service-account` `~>2.2` | Create service accounts | all |
| `datasophia-gcp-iam-key-service-account` `~>1.0` | Create service-account keys | all |
| `datasophia-gcp-iam-matrix-utils` `~>2.0` | Expand IAM matrices into a `for_each` map | all |
| `datasophia-gcp-srv-storage` `~>3.1` | Create GCS buckets | all |
| `datasophia-gcp-srv-secret` `~>2.0` | Create Secret Manager secrets and versions | all |
| `datasophia-gcp-net-firewall` `~>2.0` | Create firewall rules in the shared network project | `iac`, `dac` |
| `datasophia-gcp-utils-container-yaml` `~>1.0` | Build COS container declaration metadata | `rnd`, `dac` |
| `datasophia-gcp-utils-search-metadata` `~>1.0` | Read project metadata keys | `rnd`, `dac` |

## Key cross-repo differences

### Project ownership

- `iac` and `rnd` create the project locally and can refer to `module.datasophia-gcp-project.*`.
- `dac` mostly targets `module.datasophia-gcp-utils-search-project-basic["default-prj"]` instead.
- Do not copy `module.datasophia-gcp-project` references from `iac` into `dac` without replacing them with imported-project lookups.

### Shared network mode

- `iac` uses `shared_network = "env"` and `vpcsc = var.faas_gcp_environment_short_name`.
- `rnd` uses `shared_network = "major"` and `vpcsc = "rnd"`.
- This affects how imported network resources and network-user groups are wired.

### API enablement

- `iac` keeps many optional APIs commented until a feature needs them.
- `rnd` enables a much broader API set, including Artifact Registry, Secret Manager, Cloud Scheduler, Workflows, Eventarc, Vertex AI, notebooks, Dataform, Dataflow, Vision AI, Datalineage, Dataplex, and Dataproc.
- If a feature is missing in `iac` or `dac`, follow the prerequisite pattern from `rnd` or the comments in the target file.

### Monitoring file names

- `iac` and `rnd` use `terraform_extended/monitoring_alert_res.tf`.
- `dac` uses `terraform_extended/monitoring_alert_alert_res.tf`.
- Treat that DAC filename as a naming quirk, not a different resource family.

### Service-account shapes are not fully uniform

- `iac` service accounts use `project_id`.
- `dac` service accounts use `project_key` and resolve the project through imported lookups.
- `rnd` contains at least one inconsistent example where `sa_cloud_run_invoker` is declared with `project_key` but the module call expects `project_id`.
- Read the exact local object shape in the target repo before copying service-account objects across repos.

### Default project placeholder in DAC

- `dac/terraform/import.tf` contains a banner warning that `default-prj` must be changed from `CHANGE_ME`.
- Any DAC change that targets the real project should assume this placeholder is a prerequisite.

---
name: klever-terraform-infra
description: "Modify Klever Terraform/HCL that follows Datasophia platform engineering patterns on Google Cloud. Use when working in Klever repos with `terraform/` or that contains `iac-gcp` or `dac-gcp` in the repository name."
---

<!-- markdownlint-disable MD013 -->

# Klever Terraform Infra

Keep changes aligned with existing Datasophia wrappers and Klever template conventions. These repos mix native `google_*` resources with Datasophia modules that wrap common Google Cloud patterns.

## Workflow

### 1. Identify the template flavor

- `datasophia-glb-template-iac`: creates a standard project and common optional services.
- `datasophia-glb-template-rnd`: creates a project with heavier R&D, Vertex AI, Compute Engine, Cloud Run, and COS patterns.
- `datasophia-glb-template-dac`: manages resources in an imported/default project; it does not create the target project locally.

### 2. Identify the edit zone

- `terraform/` is the actual root module the pipeline applies: bootstrap, imported lookups, project IAM, service accounts, Cloud Identity groups, and every active workload live here.
- `terraform_extended/` is a temporary holding area for optional files from the Datasophia templates. To enable one, **copy it into `terraform/`** and adapt it there; do not edit it in place or expect the pipeline to apply it. A fully built repo (e.g. `dac-gcp-cst-klvdb1`) keeps only `terraform/`.
- Inspect `dependencies/` when a file uses `templatefile()`.

### 3. Load references as needed

- Read `references/repositories.md` first for repo roles, module inventory, and high-risk differences.
- Read `references/patterns.md` for house conventions, IAM grammar, naming, imports, and gotchas.
- Read `references/resources.md` for file-level resource schemas and examples.

### 4. Prefer the existing abstraction level

- Use Datasophia modules when a file already uses them for the same concern.
- Use native `google_*` resources where the templates already do so.
- Keep module source addresses and version pins aligned with nearby code.

### 5. Preserve the existing composition patterns

- Extend `locals` maps and lists instead of inventing new shapes.
- Reuse `module.datasophia-gcp-utils-search-project-basic` and `module.datasophia-gcp-utils-search-resources` for imported lookups.
- Reuse `module.datasophia-gcp-iam-matrix-utils` for per-resource IAM expansion.
- Keep `depends_on`, `for_each`, naming joins, and API reference locals consistent with the file.

### 6. Commit and let CI/CD apply

Terraform is not run locally. All `terraform init`, `plan`, and `apply` operations happen in the GitLab CI/CD pipeline. The pipeline handles backend configuration, authentication, and variable injection.

`terraform fmt` is the **only** reliable local check. `init`, `validate`, `plan`, and `apply` all fail locally because the provider, the backend, every `var.faas_*` variable, `local.default`, and the `datasophia-gcp-utils-*` utility modules are injected by the pipeline and declared nowhere in the repo (see `references/patterns.md`, "Pipeline-injected symbols"). Do not treat a local `validate`/`plan` failure as a real error — verify in the pipeline instead.

After editing `.tf` files, run `terraform fmt`, then commit and push. Review the pipeline output in GitLab to verify changes. If the pipeline fails, read `references/troubleshooting.md` for common error patterns.

### 7. Troubleshoot permission and role errors

When users report permission errors from compute instances, or when the CI/CD pipeline fails on IAM bindings, read `references/troubleshooting.md` for:

- Analyzing GCP permission-denial logs exported as CSV
- Mapping denied permissions to the correct IAM roles
- Diagnosing "role not supported for this resource" errors (usually a wrong role name)

## Editing Rules

- Treat these repos as templates. Many commented blocks are intentional examples or feature toggles; uncomment and adapt them before inventing new structure.
- In DAC repos, update the `terraform/import.tf` placeholder `default-prj` values before wiring resources to that imported project.
- When a feature requires extra APIs, service accounts, or imported resources, wire all prerequisites in the base files instead of editing only the target resource file.
- Do not flatten the IAM/member resolution logic into ad hoc strings. Follow the existing `member_key` and `resource_key` grammar and resolution expressions.
- Distinguish environment-scoped settings (`prod`, `pre`, `dev`, `noe`) from `all_env` defaults.
- Assume Datasophia modules wrap Google provider behavior. When module internals are not visible, infer expected inputs from nearby usage and keep changes minimal.

## References

- `references/repositories.md`: repo roles, directory layout, Datasophia module inventory, and repo-specific differences.
- `references/patterns.md`: shared Terraform idioms, IAM grammar, naming, API activation, imports, and common pitfalls.
- `references/resources.md`: file-by-file resource guidance for buckets, datasets, secrets, Cloud Run, workflows, monitoring, compute, Cloud SQL, and more, including Klever-specific subnetwork guidance.
- `references/troubleshooting.md`: analyzing GCP permission-denial logs, mapping permissions to IAM roles, and fixing non-existent role errors.

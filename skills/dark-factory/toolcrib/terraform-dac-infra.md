# Tool Belt — terraform-dac-infra

The loadout for **provisioning GCP infrastructure through a Klever DAC (terraform) repo plus a paired
FaaS app repo**, cloned from a *proven, deployed* reference pattern. The deliverable is a set of live
cloud resources (a Cloud Run Function, a Cloud Scheduler job, a service account, least-privilege IAM, a
BigQuery table) wired by HCL, driven by a small Python entry point. The value is the **deployed
footprint in dev**, asserted with `gcloud` / `bq` / `get-iam-policy` — not a unit test alone.

This belt exists because `java` / `scripting` / `frontend` cannot model "a DAC apply creates a Cloud
Function + scheduler + SA + IAM + partitioned table." Reference racked against KTP-821 (clone of the
`dspyah` pattern). ADR-002 holds: this swaps **tools only** (HCL + DAC pipeline + live-resource probes);
the room logic (concierge → design → grill → implement → review → QA) is unchanged.

- **detect:** the ticket provisions GCP infra via a **DAC repo** (`terraform/*.tf`, a `.gitlab-ci.yml`
  whose `dev` job triggers a DAC deploy bridge) and/or a **FaaS cloud-function app repo**
  (`main.py` + `pyproject.toml`, no long-running server, zip built by CI), cloned from a named proven
  pattern (e.g. `dac-gcp-report-dspyah` + `app-yahoo-dsp-data-ingestion`). Keywords: "DAC apply",
  "Cloud Run Function", "Cloud Scheduler", "service account", "IAM", "date-partitioned BigQuery table",
  "clone the <X> pattern". If the deliverable is a pure script (no infra footprint) it is `scripting`,
  not this belt.

## Hard prerequisites (front-gate; surface, never fabricate)

- **Both target repos must already exist on GitLab** (the push target). **Repo creation is a HUMAN GATE**
  — Gab creates the empty repos via a `cfg-app` / `cfg-dac-env` config-as-code PR that he merges
  (per `feedback_gab_owns_infra_repo_creation_via_cfg`). The factory NEVER creates repos. If either
  repo is absent (`gitlab_skill.py search <name>` → `[]`), HALT at the concierge with
  `prereqs_ok: false` and name the missing repo(s). Do not scaffold into a phantom path.
- **DEV ONLY, autonomously.** Everything past repo creation — push to `dev`, the DAC deploy, IAM
  grants, BigQuery writes — runs autonomously **only in the dev environment**. No `uat`/`main` deploy.
  Prod terraform is scaffolded with the Scheduler `paused = true`; this ticket triggers **no** prod
  deploy. (Klever DAC merge-forward; prod unpause is a later human-gated step.)
- **No local `terraform plan`/`apply`, ever.** The apply happens through the DAC **dev pipeline**
  (GitLab CI bridge job), which is the only sanctioned path. The belt's "apply" is "push to dev and let
  the bridge job run"; local terraform is limited to `fmt`/`validate` (no state, no credentials).
- **Clone, do not reinvent.** Copy the named reference repos' structure verbatim, then adapt
  names/resources. Trim the reference SA's IAM roles down to the AC's explicit least-privilege set;
  do not carry roles the ticket does not list. Do not invent a parallel layout.

## Build station (Implement)

- **scaffold:** clone the reference pattern into each target repo's working copy:
  - DAC (infra wiring) ← `grp-dac/grp-dac-env-report/dac-gcp-report-dspyah` — `terraform/*.tf`
    (`cloudfunction.tf`, `scheduler_res.tf`, `service_account_{res,iam}.tf`, `project_iam.tf`,
    `dataset_{res,iam}.tf`, `secret_*` only if a secret is needed, `variables.tf`) + `.gitlab-ci.yml`.
  - App (code shape) ← `app-yahoo-dsp-data-ingestion` — `main.py` + `pyproject.toml` + `.gitlab-ci.yml`
    (+ `CHANGELOG.md`). Stay framework-agnostic: Python + Vertex/Gemini (SA-based, **no API-key
    secret**) + BigQuery write. A committed **stub** `main()` that writes one placeholder row is the
    deliverable; the real generator swaps in later behind the same entry point + table schema.
- **adapt (the only edits):** resource/SA/dataset names; the BigQuery table's **explicit,
  version-controlled, date-partitioned schema** (`google_bigquery_table`, not runtime-inferred); the
  least-privilege IAM set; the per-env Slack hook local; `paused = true` on the prod scheduler.
- **lint / validate (no apply):** `terraform -chdir=<dac>/terraform fmt -check` and
  `terraform -chdir=<dac>/terraform validate` (use `-backend=false` if state is unconfigured locally);
  `python -m py_compile main.py`. These are the local gate; they prove HCL well-formedness and that the
  function imports — they do **not** prove the resources exist.

## Tester station (execution-verify + QA)

- **red (test-first):** applies to the **Python stub's pure logic only** — e.g. the row-shaping
  function or the "replace today's partition" decision. Stub the function so the file imports, write the
  `pytest` assertion, run `pytest <path>::<test>` — it must fail on the **assertion**, not an
  `ImportError`/`SyntaxError`. Commit the test alone (test-only RED), then write code to GREEN; capture
  the failing output to `<ticket_folder>/tdd/AC-<N>.md`.
  - **Pure-HCL ACs** (a resource exists, an IAM binding is least-privilege, the scheduler is paused)
    have no honest unit-RED — terraform is declarative. Mark those `red: not_applicable` (the
    `tddViolations()` exemption for declarative work) and rely on the **live apply** as their proof. Do
    NOT fake a failing terraform test.
- **execute-verify:** **push the feature branch to `dev`** → the app CI runs
  `build-upload → configure-dac → deploy in dev`, and the `deploy in dev` **bridge job** triggers the
  DAC pipeline (verify via the downstream DAC pipeline, **not** `/jobs` — the bridge is invisible there;
  use `gitlab_skill.py bridges` + `play-job`). After the DAC pipeline goes green:
  - resources live in dev → `execution_verified: "true"`.
  - HCL/code error (validate fails, CI red on a fixable cause) → fix, re-push.
  - dev pipeline blocked by infra outside the change (registry nightly downtime, IAP, quota) →
    `execution_verified: "infra_blocked(<what>)"`. Never claim a resource exists without probing it.
- **proof (QA):** assert each AC against the **live dev resources** — reading the `.tf` is never a
  `PASS`:
  - Cloud Function exists, gen2, internal ingress: `gcloud functions describe <fn> --region <r> --gen2`
    (check `ingressSettings: ALLOW_INTERNAL_ONLY`).
  - Scheduler job exists + daily + (prod) paused: `gcloud scheduler jobs describe <job> --location <r>`.
  - SA least privilege: `gcloud projects get-iam-policy <proj>` + dataset policy — assert the SA holds
    **exactly** the listed roles (`bigquery.jobUser`, `run.invoker`, `eventarc.eventReceiver`,
    `artifactregistry.reader` at project; `bigquery.dataEditor` on the dataset; `secretAccessor` only if
    a secret exists) and **none** of `roles/owner`, `roles/editor`, `bigquery.admin`.
  - End-to-end stub run: `gcloud scheduler jobs run <job>` → `bq query` confirms **exactly one** row in
    the current-date partition.
  - Idempotent re-run: run again same day → `bq query` confirms that day's partition is replaced (still
    one row) and older partitions are untouched.
  - Failure alert: `notify_slack` wired to the per-env hook (assert the env var + code path; trigger a
    forced failure in dev if feasible).
  - Prod scaffolded + paused: prod terraform present with Scheduler `paused = true`; no prod pipeline
    ran.
  - No live execution of an AC → that AC is `PARTIAL`/`CANT-TEST` with the reason, never `PASS`.

- **has_version_file:** mixed. The **app** repo has `pyproject.toml`/`CHANGELOG.md` (bump on push). The
  **DAC** repo has **no** version file — `/klever-mr` skips the version-bump gate for it. ShipPrep must
  not assume a single version file across the two repos.

## MR / ship note

Two repos → potentially two MRs (app + DAC), both to `dev`, both human-merged. Repo **creation** is the
prior human gate (cfg PR). The factory pushes branches + opens MRs; it does not merge, does not promote
to uat/main, does not unpause prod.

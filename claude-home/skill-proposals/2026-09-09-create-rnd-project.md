# Skill Proposal: create-rnd-project
Date: 2026-09-09
Source: session warm-finch — created the `fahren` RND project end to end

## Trigger

"create an RND project", "new RND environment", "I need a personal sandbox project",
"spin up an RND for X", or any request naming a new `rnd-<shortname>` environment.
Klever org only.

## Scope

Org (Klever). Touches two GitLab repos and creates a real GCP project, so it needs the
same human gate discipline as `klever-terraform-infra`.

## Why a skill rather than a doc

The sequence has four steps across two repos, two of which are **manual apply jobs that
a green pipeline hides**. It also has two known template defects that fail the first
plan every time. Someone doing this from the docs will ship a red pipeline and then
debug defects that are already understood. That is exactly the shape a skill removes.

## Draft Steps

1. **Settle the shortname first.** Enforce the 1-6 letter cap and explain why it is a
   GCP project-id limit, not style (`prj-n-rnd-<name>-<hash>` against a 30-char ceiling).
   Confirm with the human, because renaming after apply is not available. Ask whether a
   Jira ticket is wanted; precedent is no ticket for personal R&D.
2. **Register in `cfg-iac-rnd`** (project 67). One line into `shortname_list` in
   `terraform/main.tf`, in a worktree. Push, open an MR, read the plan and require
   `0 to destroy` with only `["<name>"]`-scoped adds, merge, then **play the manual
   `apply in noe` job** and confirm the `iac-gcp-rnd-<name>` repo exists.
3. **Instantiate from `datasophia-glb-template-rnd`.** Sync the template first (local
   checkouts drift; this one was 10 commits behind). Copy the tracked files via
   `git archive`, drop `CONTRIBUTING.md` (it credits the template's own authors), and
   fill the `iac-gcp-rnd-name` placeholder in `README.md`. Note `git clone` cannot
   bootstrap IAP, so use init + remote add + fetch.
4. **Pre-fix the two known template defects before the first push**, so the first plan
   is green instead of red:
   - `import.tf` — replace subnets `front1/front2/back1/back2` with the real
     `usea1-prime` / `usce1-prime` from `prj-n-rnd-main`. Verify against
     `gcloud compute networks subnets list` rather than trusting either the template or
     a sibling repo.
   - `service_account_res.tf` — `sa_cloud_run_invoker` uses `project_key` while the
     module reads `each.value.project_id`. Comment it out or give it a real `project_id`.
5. **Apply and verify.** Merge, play `apply in noe`, then assert from the apply log
   (`Apply complete! Resources: N added`) plus independent `gcloud` checks: project
   `ACTIVE`, expected API count, `sa-authorized` present, shared-VPC attachment.
   Treat an immediate post-apply `IAM_PERMISSION_DENIED` as Cloud Identity propagation
   lag and retest, not as a failed apply.

## Notes for the author

- Reference instance to read is `iac-gcp-rnd-dataen`. Do **not** use
  `iac-gcp-rnd-sbox`; it is trimmed to Cloud Run and still carries the pre-fix
  singular `role =` membership bug.
- The latest template enables ~58 APIs including Vertex AI, Dataflow, Dataproc,
  Dataplex and Vision AI. That is the documented default and costs nothing until
  resources exist, but the skill should offer a trim step for narrow sandboxes.
- Should compose with `klever-terraform-infra` (load it for the edit conventions)
  rather than restating its rules.

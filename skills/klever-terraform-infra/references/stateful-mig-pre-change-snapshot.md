# Pattern: Terraform-native pre-change snapshot for a stateful COS MIG

Use this in a Klever DAC repo whose COS MIG keeps state on a data disk
(`stateful_disk` with `delete_rule = "NEVER"`), when its docs ask for a manual snapshot
before a VM change. Fleet candidates: proxi, usermg, scope3, proxrp, proexp, geoloc.
Check each repo for a stateful MIG first. Not every one has it.

Origin: Proxi DAC MR !48 (KTP-853, 2026-11-04). The first pipeline plan of that MR was the first
validation. Confirm in the pipeline output of your own MR before you call the pattern proven there.

## Why

A stateful MIG with `replacement_method = "RECREATE"` deletes the VM and attaches the same data
disk to the new VM. A bad image or startup script can still damage the data. A manual snapshot
step gets skipped. Terraform can take the snapshot as part of the apply.

## Steps

1. **Find the three objects.** The instance template (`google_compute_region_instance_template`,
   often `for_each`), the MIG, and the data disk name. A stateful MIG names the disk after its
   first instance. Read it from the existing manual-snapshot doc or the console. Do not guess it.
2. **Add the snapshot.**

   As written in Proxi MR !48 (`terraform/compute_engine_cos_policy_res.tf`):

   ```hcl
   resource "google_compute_snapshot" "pre_change" {
     for_each = try(local.proxi_data_disk_by_env[var.faas_gcp_environment_short_name], {})  # disk name => { zone }
     lifecycle {
       create_before_destroy = true
     }
     name              = "proxi-pre-change-${substr(sha1(join(",", sort([for t in google_compute_region_instance_template.cos : t.id]))), 0, 12)}"
     project           = module.datasophia-gcp-utils-search-project-basic["default-prj"].project_id
     zone              = each.value.zone
     source_disk       = each.key
     storage_locations = [local.datasophia_compute_engine_cos_instance_group_res["cpe-cos-proxi"].region]
     labels            = local.default.labels
   }
   ```

   The `for_each` map keys the snapshot by data disk per environment, so an environment
   with no stateful disk creates nothing.

   The name hashes the template ids. A new template changes the name, so Terraform creates the new
   snapshot first, then updates the MIG, then deletes the old snapshot. An apply with no template
   change does not touch the snapshot. One pre-change snapshot is kept.
3. **Make the MIG wait for it.** Add `depends_on = [google_compute_snapshot.pre_change]` to the
   MIG resource.
4. **Update the repo's manual snapshot doc.** The manual step stays only for changes outside
   Terraform. A manual snapshot is deleted after the change is verified.
5. **Check the shape locally, then the order in the pipeline.**

   ```bash
   python3 ~/.claude/skills/klever-terraform-infra/scripts/check_pre_change_snapshot.py terraform/
   ```

   Exit 0 means the shape holds. It cannot prove the order. In the pipeline plan, expect one
   snapshot to create when the template changes, and none when it does not. After apply, the
   snapshot creation time is before the new VM start time.

## Limits

- Applying is the pipeline's job and goes through the normal DAC MR flow (dev first). This
  pattern does not authorize an apply.
- The snapshot covers the data disk only. The boot disk is rebuilt from the image.

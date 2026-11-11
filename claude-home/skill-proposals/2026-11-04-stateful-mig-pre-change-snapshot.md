# Skill Proposal: stateful-mig-pre-change-snapshot
Date: 2026-11-04
Source: Proxi DAC MR !48 (KTP-853), automating Rule 0

## Trigger
A Klever DAC repo runs a stateful COS MIG (a data disk with delete_rule NEVER) and its docs ask for a manual snapshot before a VM change. Or: "automate the pre-deploy snapshot", "snapshot before recreate".

## Scope
org (Klever DAC fleet: proxi, usermg, scope3, proxrp, proexp, geoloc)

## Draft Steps
1. Find the instance template, the MIG and the existing data disk name (a stateful MIG names the disk after its first instance).
2. Add google_compute_snapshot.pre_change: name hashes the template ids, create_before_destroy, storage location in the region, labels from local.default.
3. Add depends_on = [google_compute_snapshot.pre_change] to the MIG.
4. Update the repo's manual snapshot doc: manual step only for changes outside Terraform, delete it after verification.
5. Check in the pipeline plan: one snapshot to create; after apply, the snapshot time is before the new VM start.

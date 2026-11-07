# Skill Proposal: klever-stateful-mig-cutover
Date: 2026-10-25
Source: Proxi prod migration, Oct24; continuation capture in proxi-cloud-wayfinder

## Trigger
Move a Klever Linux/COS application on a stateful GCP MIG between environments or retire its source while preserving the complete disk and preventing a stopped archive from booting during template reconciliation.

## Scope
Klever org, scoped to the Linux/COS and systemd stateful-MIG pattern. Extend or compose `klever-terraform-infra`; reuse its repository ownership and CI-only Terraform rules. Do not duplicate a generic deployment framework.

## Draft Steps
1. Confirm explicit environment/deployment scope, current source refs/image, runtime identities, writer inventory, data ownership and a tested rollback direction. Audit stopped-MIG update semantics against the actual provider version and reject unintended Resize.
2. Freeze every writer with verified systemd guards; create READY recovery points and a read-only scratch restore mounted by device identity.
3. Copy the complete tree with original metadata; compare file/journal-aware SQLite manifests before intentional target edits. Preserve mixed numeric owners and the immutable source recovery copy.
4. Review fresh CI plans and exact SHAs independently; apply one environment at a time. Use opportunistic source reconciliation only when required to keep the retired archive untouched. If CI is unavailable, distinguish a specifically authorized temporary runtime activation from durable completion.
5. Verify actual bootstrap/image/mount, fresh app connection, an application-specific bounded smoke (configured-model memory proof for Proxi, not a requirement for non-LLM applications), real backup/heartbeat outputs and snapshot attachment. Retire only owned environment references, preserve rollback data and record separate unresolved product gates.

## Evidence and limits
Live migration proof exists for Proxi on Oct24, including Google provider 6.50.0 behavior. Revalidate versions and semantics; VM numeric IDs can be retained during replacement. Follow the existing operator runbook and evidence rather than copying fixed names or treating all checks as Slack end-to-end acceptance.

Proposal only: no skill is installed or enabled by this capture.

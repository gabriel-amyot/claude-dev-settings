# Skill Proposal: proxi-gmail-recover-and-resume
Date: 2026-10-25
Source: Proxi prod Gmail recovery, Oct24-25; user authorized recovery/ingestion

## Trigger
Restore the existing Proxi readonly Gmail grant and safely resume its intended ingestion schedule after revocation, credential failure or environment migration.

## Scope
Klever/Proxi only. Compose the existing prod relay, credential observation rules, operator runbook and E2 ingester. No new mailbox access, group membership, broader scopes, personal mailbox import or automatic AM messaging.

## Draft Steps
1. Diagnose the failure layer before touching credentials; verify current prod target, scope/account/client/version metadata, restore point and one credential writer. Do not wake retired dev, overwrite prod from stale copies or repeat a known revocation.
2. Obtain actual Google OAuth consent for the Proxi mailbox using the existing client and exactly gmail.readonly through the supported secure UI/handoff. Chat permission alone is not the grant; keep credential values out of tool output and honor user handoff requirements.
3. Validate the new grant in memory, install/read back only prod with concurrent-version guards, then prove the renderer actually wrote the fresh UID10000/mode0600 file and the correct mailbox/scope can be read. Do not infer installation from exit0 or require an unnecessary restart.
4. Run bounded mailbox catch-up with backup, deduplication, caps and cursor evidence. Distinguish existing-inbox catch-up from the future gap-sweep design and separately authorized historical mbox export/backfill.
5. Resume only the existing daily script job at its preserved schedule, keep the 15-minute and unrelated jobs disabled, and verify enabled/execution metadata independently. Disable the old PROD token Secret Manager version only after new live proof; never repeat Google grant revocation during recovery; vault synchronization and group coverage remain separately reported outcomes.

## Evidence and limits
The relay has 13 synthetic offline tests; E2 cursor/dedup/ingest behavior has dated implementation evidence. The latest recovery preflight was blocked by workstation DNS before fresh consent, grant issuance or credential changes, so this proposal is not a proven completed OAuth recovery. Before implementation, review the actual deployed renderer, job CLI/locking and current source limits; do not embed secrets or stale resource IDs.

Proposal only: no skill is installed or enabled by this capture.

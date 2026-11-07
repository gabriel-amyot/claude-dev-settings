# Skill Proposal: proxi-cron-install
Date: 2026-11-06
Source: session watchful-lynx (KTP-853), Proxi reaction-feedback fix + daily/weekly monitoring jobs; the same install sequence ran 4 times by hand.

## Trigger
"install/update a Proxi cron job", "add a Hermes cron on prod", "deploy this script to Proxi", "fix a Proxi cron script".

## Scope
org (Klever, Proxi prod VM `cpe-p-back-proxi-usea1-cos-proxi-16n4`).

## Draft Steps
1. Preflight: gcloud auth valid; strict IAP SSH works (else runbook host-key check, never bypass). Use a shell function for the ssh command (zsh).
2. Back up: `cron/jobs.json.bak-<label>-<UTC>` and the existing script `*.bak-<UTC>` as uid 10000.
3. Install: pipe the local source copy into `docker exec -i -u 10000:10000 hermes sh -c 'cat > X.new && python3 -m py_compile X.new && mv X.new X'`; compare sha256 with local. If the script needs a secret, it must read Secret Manager (Hermes scrubs cron env); dry-run with `env -u <SECRET>`.
4. Create `--paused` (deliver + failure-deliver), set toolsets/prompt via `cron.jobs.update_job`, then resume + `hermes cron run`, check `last_status`, `last_delivery_error`, token use in `session_model_usage`.
5. Record in `general/initiatives/proxi-dev-deploy/STATE.md`, commit source copies.

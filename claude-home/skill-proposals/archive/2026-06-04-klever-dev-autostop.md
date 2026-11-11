# Skill Proposal: klever-dev-autostop
Date: 2026-06-04
Source: Session "crit launch → GCP dev ops" — started dev at night, scheduled a stop to avoid overnight compute cost

## Trigger
User says "stop dev in N hours", "auto-stop the dev environment", "don't let dev run overnight", "shut dev down at midnight", or starts the Klever GCP dev env at night and wants a cost guard.

## Scope
Klever (org). Could fold into existing `dev-status` or `klever-local-stack` skills rather than stand alone.

## Draft Steps
1. Resolve the 5 dev instances + zone (us-east1-b) and the two projects (prj-d-global-back-a7osqvwere, prj-d-global-front-6kpke3wn54).
2. Generate a stop script: kill the IAP tunnel → stop 2 frontends → sleep 30s → stop 3 backends, all with `--zone us-east1-b`. Log to a known path.
3. Schedule it. Default: detached `nohup bash -c 'sleep <seconds>; <stop-script>' &`. Offer the sleep-proof variant: a `launchd` LaunchAgent with a `StartCalendarInterval` at an absolute wall-clock time (survives laptop sleep/reboot).
4. Confirm the scheduler is alive (ps the PID, or `launchctl list`), report the fire time.
5. Provide cancel + verify commands (`kill <pid>` / `launchctl unload`; `cat <log>`; instance status check).

## Notes
- The `sleep`-timer approach pauses while the Mac is suspended — call this out and recommend launchd when reliability matters.
- Pairs with the start path (start-stop-portal-in-dev.sh + gcp-connect.sh). A complete skill could own both start and scheduled-stop.

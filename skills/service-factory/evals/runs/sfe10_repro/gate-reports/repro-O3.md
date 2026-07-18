Probe: ui-probe demo-dev | Advertiser 842
Result: 500 fetch-failed. Spinner never resolves.
Network: GET https://proxrp-cos-retired.dead/... -> 500
First-error: 2026-07-15T09:12Z (after MR!21 merged)
Signature: 500/fetch-failed
Anchor: two-part — UI symptom (O3, spinner stuck) + 500/fetch-failed tech signature with first-error timestamp.
Note: "proxrp-cos-retired.dead" in the URL strongly suggests a stale/retired host URL in the DAC config.

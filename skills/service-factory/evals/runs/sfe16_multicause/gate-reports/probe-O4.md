PROBE: exhaustive-read dac-config demo-dev   METHOD: exhaustive-read   ENV: demo-dev
RESULT (from world.yaml): "demo DAC dev block missing the KTP-863 rewiring (points at retired host)."
CITATION: dac-gcp-back-proxrp@abc123
FINDING: DAC dev block routes to a retired host. KTP-863 rewiring was applied to other envs but not demo-dev's DAC config.
MECHANISM: Config points backend at retired host → 500 on all API calls → stuck spinner.
ANCHOR UPGRADE: mechanism confirmed [OBSERVED O4]

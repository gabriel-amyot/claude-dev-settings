# Skill Proposal: proxi-model-ab
Date: 2026-10-27
Source: session agile-shrike (Proxi prod latency, model selection #505)

## Trigger
"compare models on Proxi", "A/B flash-lite vs 3.8", "measure Proxi latency", "is model X faster in prod", after any model or timeout config change.

## Scope
org (Klever, Proxi prod VM)

## Draft Steps
1. Preflight: announce the run to Gabriel (one prod-disruptive action at a time); check no DAC pipeline is running; verify live config with hermes_yaml (no secrets printed).
2. Upload `general/initiatives/proxi-dev-deploy/drafts/latency-f1/measure_f1.py` to the hermes container; run detached as uid 10000, `-w /opt/hermes`, one arm per model via `MODEL_OVERRIDE` + `RUN_TAG`, always with a control arm of the current primary in the SAME time window.
3. Poll in the foreground (background sleep loops get reaped); read per-turn results from `/tmp/<tag>-answers.json` and stall/fallback counts from agent.log.
4. Check answer quality against pre-registered expected values (no client content printed), not just time.
5. Report p50/p90/max, stalls, fallbacks per arm; write the build note and comment the result on the GH issue.

# Skill Proposal: klever-store-sheet-fill
Date: 2026-06-11
Source: vivid-ibis session (KTP-719/720/721 + KTP-718 onboarding)

## Trigger
"onboard a new advertiser", "fill the stores sheet", "I have a Placer/ingestion CSV from Travis",
"add these locations to the Measurement Map", "turn this CSV into sheet rows". Klever org.

## Scope
org (Klever) — complements existing `/adtech:placer` (onboard) and `/geocode-bq-locations`.
This one is specifically the CSV → source-of-truth-Sheet row builder + readiness gate, which neither covers.

## Draft Steps
1. Parse the vendor ingestion CSV (latin-1 → utf-8; tolerate the metadata header block).
2. Resolve identity from BQ: brand → int ID (`klever_core_entities.advertiser`) → DSP provider id (`dsp_account.DSP_PROVIDER_ID`). Flag ambiguous matches; confirm DSP (TTD vs DV360) from data, not the ticket.
3. Assign `klever_location_id` from `MAX(KLEVER_LOCATION_ID)+1`.
4. Emit paste-ready TSV in the 15-col `normalized_klever_stores_mapping` schema (country short-code; blanks for DMA/disabled), plus bridge-rows TSV for any US rows that already carry a Placer entity id.
5. Verify the foot-traffic gate: US → Placer POIs/bridge; CA → rows present in `proximity_daily_geo_zip_performance`. Report PASS/BLOCKED with evidence.
6. (Optional) Draft the readiness/pushback Jira comment + attach files; transition to Blocked + assign PO if prerequisites are missing.

## Notes
Full hand-written runbook already exists at
`tickets/KTP/KTP-747/onboarding/README.md` and a working generator at
`tickets/KTP/KTP-747/onboarding/scripts/build_sheet_rows.py` — use both as the skill's basis.

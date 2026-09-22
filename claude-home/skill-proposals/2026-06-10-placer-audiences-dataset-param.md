# Skill Proposal: update adtech:placer with audiences/demographics dataset param
Date: 2026-06-10
Source: Amal PO question on Placer audiences + demographics

## Trigger
This is an UPDATE to the existing `adtech:placer` skill, not a new skill.
Run `/operationalize --update adtech:placer` (or edit the skill directly).

## Scope
org (Klever) — lives in the local-marketplace adtech plugin.

## Gap being fixed
The skill's endpoint table and `references/endpoints.md` list only the 7 Measurement-Map
endpoints. They omit:
- `POST /v1/reports/trade-area-demographics` `dataset` parameter and its full enum
- `audienceType` (captured/potential) and `benchmarkScope` params
- That Spatial.ai PersonaLive **audiences** are pullable (not dashboard-only)
- `GET /openapi.json` and `GET /v1/accounts/keys/usage-status` as discovery/quota tools

## Draft edits
1. Add a "Trade-area audience & demographics" sub-section to the shared reference:
   one endpoint, `dataset` switch, `audienceType`, `benchmarkScope`, `apiId` (singular).
2. Add the full `StatsDatasets` enum (census/personalive/experian_mosaic/sti_*).
3. Add a gotcha: read `/openapi.json` before concluding a capability is absent.
4. Note open item: "Segment Families" sub-view param unconfirmed.

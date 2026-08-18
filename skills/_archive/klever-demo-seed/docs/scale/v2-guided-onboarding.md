# klever-demo-seed — V2 vision: guided demo-advertiser onboarding

**Status:** future / scale. V1 (current) = working scripts + manual glue. V2 = one guided flow.

## V1 (what exists today, works)
Three scripts, run by hand, human stitches them:
1. `generate_canada_demo_seed.py` — make staged BQ rows (+ locations CSV).
2. (manual, this session) create advertiser + dsp_account in DEV user-management via the IAP tunnel.
3. `load_seed.sh` — backup → delete → load → verify.

Glue (pick advertiser id, create UM advertiser, feed id back into the generator, run loader) is done by
the human / the agent in chat. Works, but it's a checklist, not a product.

## V2 (the wanted UX): "add a demo advertiser" in one guided run
The skill becomes an **interactive orchestrator**. Minimal input from the user; the skill asks the rest
and calls every script in order.

```
/klever-demo-seed   (no args)
   │
   ├─ Q1  Brand name?                         e.g. "Lumberjack Pastries"
   ├─ Q2  Country / footprint?                CA default; provinces + urban clusters (pick or accept default)
   ├─ Q3  Real store locations source?        BeaverTails-style scrape / paste list / fabricate-only
   ├─ Q4  Date window + volume profile?       dense/sparse, which provinces hot
   ├─ Q5  Which layers?                        province + FSA (now) / + census-division (needs backend)
   │
   ▼ ORCHESTRATE (calls the scripts, no manual glue)
   1. UM: check demo agency exists → create Advertiser + dsp_account → read back assigned id  (LP_ID)
   2. generate_canada_demo_seed.py --advertiser-id LP_ID --brand <Q1> ...   → staged files
   3. load_seed.sh --advertiser-id LP_ID            → backup + load + verify
   4. (optional) push locations CSV to the Google Sheet / Dataform source
   5. validate render on dev (ui-probe): province + FSA color; report evidence
   │
   ▼ OUTPUT: advertiser id, rows loaded, provinces colored, screenshot, "ready to demo"
```

### What V2 needs built
- **UM step automation** (the part done by hand this session): a small helper that opens the IAP tunnel,
  creates advertiser + dsp_account under the demo agency, returns the assigned id. Reversibility record.
- **AskUserQuestion-driven front** so the agent gathers Q1–Q5 with sensible defaults, minimal typing.
- **Footprint as data input** (JSON/sheet) instead of editing `geography.py`, so non-coders add provinces/cities.
- **Location sourcing** options (scrape a brand's store locator → geocode via Nominatim → relabel).
- **Persistence guard**: detect/handle the Dataform-rebuild-overwrites-seed risk (seed at source, or a
  re-apply hook).
- **One report** at the end (id, rows, provinces, render proof) suitable for a Jira closing comment.

### Why not now
V1 ships the data today (KTP-728). V2 is the productized, low-input, guided version — worth it once we
onboard demo advertisers repeatedly. Capture here; build when the repeat-cost justifies it.

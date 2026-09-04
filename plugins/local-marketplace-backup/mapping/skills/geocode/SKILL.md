---
name: geocode
description: "Geocode an ORDERED list of store addresses into paste-ready coordinates aligned to the Normalized Klever Stores Google Sheet (top-left paste, fill down). Nominatim/OSM only (storage-safe), tiered fallback, region bbox validation, order preserved with failures flagged in position. Trigger: 'geocode these addresses', 'geocode this list', 'lat/lon for the sheet', 'paste-ready coordinates', 'geocode for the stores sheet'. Klever org."
nav:
  bay: build
  when: "You have an ordered list of store addresses and need paste-ready lat/lon in the exact row order of the Normalized Klever Stores sheet."
  when_not: "Stores already live in BigQuery and you want coords written back to BQ (use /geocode-bq-locations). Or you need to acquire the addresses first (use /location-scraper)."
  org: [klever]
---

# mapping:geocode — Ordered Address-List Geocoder

Productizes the by-hand geocoding workflow proven on KTP-755 (Héma-Québec 139 QC
sites; Blinds To Go 21 ON/QC stores). You give an **ordered list of addresses**;
this returns **paste-ready coordinates in the exact input row order**, so you copy
`latlong-paste.tsv` straight into the "Normalized Klever Stores locations" Google
Sheet (top-left cell) and it fills down in perfect row alignment.

Per the CLAUDE.md data rule, data stays on disk: the bundled script runs locally
and writes files. Nothing large is loaded into the conversation.

---

## When to use

- The user gives an ordered list of store addresses (paste or file) and wants
  coordinates back in that same order for the stores sheet.
- Onboarding an advertiser's locations where the addresses are known but not yet
  geocoded, and the target is the Google Sheet (not BQ).

**Not this skill:**
- Coords belong in BigQuery (`normalized_klever_stores_mapping`) → use
  `geocode-bq-locations` (BQ is cross-cutting across the Klever stack; it is not
  owned by the mapping plugin — it composes `mapping:geocode`).
- You still need to find the addresses → use `location-scraper`.

---

## Hard rules (non-negotiable — learned on KTP-755)

1. **Nominatim / OpenStreetMap is the ONLY automated geocoder.** It is free, no
   key, and ODbL **permits persisting results** with attribution
   (`(c) OpenStreetMap contributors`). **NEVER persist Mapbox or Google output** —
   Mapbox standard geocoding forbids storage (Permanent Geocoding is a separate
   paid product Klever isn't on); Google has its own storage limits. A human doing
   a manual Google Maps lookup for a few stragglers is fine; automated persistence
   is not. See the `feedback_geocoding_storage_licensing` memory.
2. **Outputs go to a committed folder, NEVER `/tmp`.** A prior KTP-755 run lost
   everything to a /tmp wipe. The script refuses a `/tmp` `--out`.
3. **Order is sacred.** Input order = the sheet's row order. Failures stay as
   blank, flagged rows **in position**. Never reorder, never drop. One top-left
   paste must fill down correctly.
4. **Identity audit before geocoding.** Echo the advertiser id / brand and the
   footprint summary the script prints (row count, region breakdown, first/last
   address). Confirm the footprint matches the claimed brand before trusting
   output. This session almost geocoded 139 Héma-Québec blood-drive sites that
   were mislabeled "Blinds To Go". If the footprint looks wrong for the brand,
   STOP and surface it.

---

## Workflow

### Step 1 — Confirm the input and the brand

Get the ordered address list. Accept a pasted TSV/CSV or a file path. Confirm with
the user **which advertiser / brand** these stores belong to, and that the order
matches the sheet's row order. Echo it back.

Expected columns, in file order (override with `--cols`):
`location_id, street, city, region(province/state), postal/zip`.
Header row is auto-detected; delimiter (tab vs comma) is auto-detected.

If the list was pasted into the conversation, write it to the output folder as
`source.tsv` first (data on disk), then run against that file.

### Step 2 — Pick the output folder (committed, never /tmp)

Default to the ticket folder, e.g.
`tickets/{TICKET}/data/{advertiser-slug}/output/`, or a committed working folder
the user names. Never `/tmp`.

### Step 3 — Run the geocoder

```bash
python3 ~/.claude/plugins/local-marketplace/mapping/skills/geocode/scripts/geocode_locations.py \
  <INPUT.tsv> \
  --out <COMMITTED_OUTPUT_DIR> \
  --region QC \
  --country ca \
  --user-agent "klever-mapping-geocoder/1.0 (gamyot@beklever.com)"
```

- `--region` presets: `QC`, `ON`, `CA` (all Canada), `US` (contiguous). Omit for
  no bbox check, or pass a custom `--bbox latmin,latmax,lonmin,lonmax`.
- `--country` ISO2 (default `ca`).
- `--cols id,street,city,region,postal` if the column order differs.
- `--resume` reuses already-resolved rows from an existing `verification.csv`.
- Rate limit is fixed ≥1.0s/req (OSM policy). ~150 rows ≈ 3 minutes.

`certifi` is used for SSL if present (handles the macOS cert-store issue);
otherwise it falls back. No required pip dependencies.

The script geocodes each row through **evidence-based tiered fallback** and tags
the tier: `structured` (Nominatim structured query, most reliable) → `street+city+postal`
→ `street+city` → `centroid` (postal or city, flagged `APPROXIMATE`). Bare
`street+postal` is deliberately NOT a primary tier — it mis-resolves to the wrong
city while staying inside the region bbox (Toronto→Hamilton). Trailing unit/suite
designators are stripped before querying. Results outside the region bbox are
flagged `SUSPECT_OUT_OF_BBOX` (caught a QC postal-fallback that landed in Alberta).

### Step 4 — Verify alignment BEFORE pasting

Open `verification.csv` and eyeball the **first row, the last row, and one middle
row** against the sheet. Confirm the ids line up with the addresses. Report the
summary: total / OK / APPROXIMATE / SUSPECT / FAILED counts.

Cross-check one OK result against a manual Google Maps lookup for sanity.

### Step 5 — Hand back the paste artifact

Tell the user: paste `latlong-paste.tsv` into the top-left target cell of the
sheet's lat/lon columns; it fills down in input order. TSV (not CSV) is the
default so French-locale decimal commas can't mis-split the columns. Flag the rows
in `failures.md` that need a manual lookup, in their row positions.

---

## Outputs

| File | Purpose |
|---|---|
| `latlong-paste.tsv` | **The paste artifact** — `lat⇥lon`, no header, input order. |
| `latlong-paste.csv` | Comma fallback. |
| `verification.csv` | `id, street, city, region, postal, lat, lon, tier, status` — eyeball alignment. |
| `failures.md` | FAILED / SUSPECT / APPROXIMATE rows + OSM attribution. |

Reference runs to compare behavior against:
`project-management/tickets/KTP/KTP-747/KTP-755/data/blinds-to-go-real/output/`.

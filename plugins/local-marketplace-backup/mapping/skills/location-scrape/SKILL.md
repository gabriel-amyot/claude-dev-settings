---
name: location-scrape
description: "Scrape store/POI locations (addresses) from a business website or store-locator, producing a clean ordered address list ready for mapping:geocode. Generic — works for any business with an online location list. Trigger: 'scrape locations', 'scrape store locator', 'get store addresses from the website', 'pull POI list', 'find their locations'."
nav:
  bay: build
  when: "You need to acquire a business's store/POI addresses from the web before geocoding them."
  when_not: "You already have the addresses (use mapping:geocode). You need foot-traffic/visit data (use adtech:placer)."
---

# mapping:location-scrape — Web Location Scraper

Scrapes store/POI locations from a business's website or store-locator into a clean,
ordered address list — the upstream feeder for `mapping:geocode`.

> **Migrated from `location-scraper`.** Scraping technique knowledge is preserved
> below. The original two-phase pipeline (scrape + geocode) is now split: this skill
> owns scraping; **geocoding moved to `mapping:geocode`** (Nominatim-only, storage-safe
> by design). The bundled `geocoder.py` is the old multi-provider helper, kept for
> reference only — prefer `mapping:geocode` for any real geocoding run.

## When to use
- A business has an online store-locator / locations page and you need their
  addresses as structured rows (id, street, city, region, postal).
- First step of onboarding a new advertiser/brand whose locations aren't in a sheet yet.

## Output contract
Produces a TSV/CSV ordered list with columns `location_id, street, city, region, postal`
— exactly the input shape `mapping:geocode` expects. Hand the file straight to geocode.

## Scraping approach

Every store-locator site is structured differently. Do **NOT** run
`scraper_template.py` as-is — it is a reference for patterns, not a runnable
solution. Write a custom scraper tailored to the target site.

### Step-by-step
1. **Fetch the store-locator homepage** with `requests` and inspect the HTML structure.
2. **Look for structured data first** (fastest, cleanest):
   - `aria-label` attributes (e.g. `"located at 123 Main St, City, ST 12345"`)
   - JSON-LD (`<script type="application/ld+json">`) with `PostalAddress` schema
   - Microdata (`itemprop="address"`)
   - Embedded JSON in `<script>` tags (arrays of objects with lat/lng/address fields)
3. **Identify the site hierarchy.** Most locators follow **state > city > location**.
   Scrape the top level to discover sub-pages, then scrape each sub-page for addresses.
4. **Write a self-contained Python script** that:
   - Crawls all pages in the hierarchy
   - Extracts addresses using the ONE pattern identified in step 2
   - Deduplicates using `street|zip` as the key
   - Saves results to a committed folder (never `/tmp`)
   - Uses `flush=True` on all prints (so background execution shows progress)
   - Includes `time.sleep(0.3)` between fetches (be polite to servers)

### Common pitfalls (learned from real scraping sessions)
- **Regex on raw HTML produces duplicates.** Sites render the same address in
  aria-labels, JSON-LD, and visible text. Pick ONE extraction method and stick with it.
- **Suite/unit info causes geocoding failures later.** Extract addresses as-is during
  scraping; the geocoder handles simplification.
- **Some sites return different HTML per User-Agent.** Always set a realistic browser
  User-Agent header.
- **Large scrapes (500+ pages) should run in the background.** Use
  `run_in_background: true` and check progress with `TaskOutput`.

### Large-job execution strategy
For 500+ locations, keep scraping and geocoding as two separate background jobs:
1. **Scrape phase** (5-15 min): run the custom scraper, save an addresses-only file.
2. **Geocode phase**: hand that file to `mapping:geocode`.

Always save intermediate results so a geocoding retry never forces a re-scrape.

## Scripts
- `scripts/scraper_template.py` — starting point; adapt selectors/pagination per site.
- `scripts/geocoder.py` — legacy multi-provider geocoder (Census → Photon → Nominatim →
  Google), CLI + library. Kept for reference; **prefer `mapping:geocode`** for real runs
  (it is Nominatim-only because Census/Mapbox/Google output cannot be legally persisted).

## Dependencies
```bash
pip install requests beautifulsoup4
```
No API keys needed for scraping.

## Pipeline position
**`mapping:location-scrape`** → `mapping:geocode` → (advertising) `adtech:placer` onboard.

## Notes
- Respect target sites' robots/ToS and rate limits.
- Outputs to committed folders, never `/tmp`.

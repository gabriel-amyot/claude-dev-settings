---
name: location-scraper
description: "Scrape store/business locations from websites and geocode addresses to lat/long coordinates. Use this skill whenever the user wants to extract location data from any website, geocode a list of addresses, build a CSV of business locations with coordinates, or anything involving store locators, franchise locations, branch finders, or 'find a location near you' pages. Also trigger when the user has a spreadsheet of addresses and wants GPS coordinates added, or asks about bulk geocoding. Even if the user just pastes a URL to a store locator page, this skill applies."
---

# Location Scraper & Geocoder Skill

Two-phase pipeline: (1) scrape addresses from a website, (2) geocode them to lat/long. Each phase works independently, so you can scrape without geocoding or geocode an existing list of addresses.

## When to Use

- User provides a store locator URL and wants all locations as a CSV
- User has a CSV/spreadsheet of addresses and wants lat/long added
- User asks to "find all locations" for a brand/chain/business
- User asks about bulk geocoding or converting addresses to coordinates

## Phase 1: Scraping Locations

Every store locator site is structured differently. Do NOT try to use `scraper_template.py` as-is. Instead, write a custom scraper script tailored to the target site. The template is a reference for patterns, not a runnable solution.

### Step-by-step approach

1. **Fetch the store locator homepage** with `requests` and inspect the HTML structure
2. **Look for structured data first** (fastest, cleanest):
   - `aria-label` attributes (e.g., `"This location is located at 123 Main St, City, ST 12345"`)
   - JSON-LD (`<script type="application/ld+json">`) with `PostalAddress` schema
   - Microdata (`itemprop="address"`)
   - Embedded JSON in `<script>` tags (search for arrays of objects with lat/lng/address fields)
3. **Identify the site hierarchy**: Most store locators follow state > city > location. Scrape the top level to discover sub-pages, then scrape each sub-page for addresses.
4. **Write a self-contained Python script** that:
   - Crawls all pages in the hierarchy
   - Extracts addresses using the pattern identified in step 2
   - Deduplicates using `street|zip` as the key
   - Saves results to CSV
   - Uses `flush=True` on all print statements (so background execution shows progress)
   - Includes `time.sleep(0.3)` between page fetches (be polite to servers)

### Common pitfalls learned from real scraping sessions

- **Regex on raw HTML produces duplicates.** Sites often render the same address multiple times (in aria-labels, JSON-LD, visible text). Pick ONE extraction method and stick with it.
- **Suite/unit info causes geocoding failures later.** Extract addresses as-is during scraping; the geocoder handles simplification.
- **Some sites return different HTML for different User-Agents.** Always set a realistic browser User-Agent header.
- **Large scrapes (500+ pages) should run in the background.** Use `run_in_background: true` and check progress with `TaskOutput`.

## Phase 2: Geocoding

Use `geocoder.py` (bundled with this skill) for all geocoding. It chains multiple free providers with automatic fallback and progressive address simplification.

### Provider chain (in order)

| Provider | Free? | Rate Limit | Coverage | Best For |
|---|---|---|---|---|
| US Census Bureau | Yes, no key | None documented | US only | US street addresses |
| Photon (Komoot) | Yes, no key | Be polite (~0.5s) | Global | Fallback, flexible matching |
| OpenStreetMap Nominatim | Yes, no key | 1 req/sec strict | Global | International addresses |
| Google Geocoding API | No ($5/1000) | Generous | Global | Last resort, highest accuracy |

The geocoder tries Census first (best hit rate for US), then Photon, then Nominatim, then Google. Each attempt progressively simplifies the address (strip suite/unit/floor, then try street-only, then city-level fallback).

### Using geocoder.py

**As a CLI** (for the user to run directly):
```bash
python geocoder.py input.csv output.csv
python geocoder.py input.csv output.csv --address-col "Address" --state-col "State" --zip-col "Zip"
```

**As a library** (when writing a scraper script):
```python
import sys
sys.path.insert(0, "<path-to-this-skill-directory>")
from geocoder import geocode_one, geocode_addresses

# Single address
lat, lon = geocode_one("123 Main St, Springfield, IL 62701")

# Batch (modifies list in-place)
locations = [{"full_address": "...", "state": "IL", "zip": "62701"}, ...]
geocode_addresses(locations, progress_fn=lambda cur, tot: print(f"[{cur}/{tot}]"))
```

### Handling missing geocodes

Expect 95-98% hit rate on first pass. For remaining addresses:
1. Run a second pass with Census one-line endpoint (`/geocoder/locations/onelineaddress`)
2. Try Photon with aggressively simplified addresses
3. Present remaining failures to the user (usually addresses with route numbers, shopping center names, or unusual formatting)

## Phase 3: Export

Default CSV format:
```
Full Address, State, Zip, Latitude, Longitude
```

Customize columns per user request (city, store name, phone, hours, etc.)

## Execution Strategy for Large Jobs

For 500+ locations, split into two background jobs:

1. **Scraping phase** (5-15 min): Write and run the custom scraper, save addresses-only CSV
2. **Geocoding phase** (variable, ~1 sec per address with Nominatim, faster with Census): Run geocoder.py on the addresses CSV

This way if geocoding fails or needs a retry, you don't have to re-scrape. Always save intermediate results.

## Dependencies

```bash
pip install requests beautifulsoup4
```

No API keys needed. Google Geocoding API is optional (set `GOOGLE_GEOCODING_API_KEY` env var if available).

## File Reference

| File | Purpose | When to read |
|---|---|---|
| `geocoder.py` | Multi-provider geocoder with CLI and library interface | When geocoding addresses |
| `scraper_template.py` | Reference patterns for common scraping strategies | When writing a new scraper (read for patterns, don't copy wholesale) |

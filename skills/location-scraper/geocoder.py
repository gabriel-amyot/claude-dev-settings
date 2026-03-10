"""
Multi-provider geocoder with automatic fallback.

Providers (in order):
1. US Census Bureau (free, no key, US only)
2. OpenStreetMap Nominatim (free, 1 req/sec, global)
3. Google Geocoding API (paid, requires GOOGLE_GEOCODING_API_KEY env var)

Usage:
    # As a library
    from geocoder import geocode_addresses
    results = geocode_addresses([
        {"full_address": "123 Main St, Springfield, IL 62701", "state": "IL", "zip": "62701"}
    ])

    # As a CLI
    python geocoder.py input.csv output.csv
    python geocoder.py input.csv output.csv --address-col "Address" --state-col "State" --zip-col "Zip"
"""

import csv
import os
import re
import requests
import sys
import time


def simplify_street(street):
    """Strip suite/unit/floor info for better geocoding match rates."""
    street = re.sub(r'\s+(Suite|Ste|Unit|Floor|Bldg|Building|Ste\.)\s*\S*.*$', '', street, flags=re.IGNORECASE)
    street = re.sub(r'\s+#\S+.*', '', street)
    street = re.sub(r'\s*-\s*[A-Z][a-zA-Z].*', '', street)
    return street.strip()


def parse_full_address(full_addr):
    """Parse 'street, city, ST ZIP' into components."""
    m = re.match(r'^(.+?),\s+(.+?),\s+([A-Z]{2})\s+(\d{5})', full_addr)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3), m.group(4)
    return full_addr, "", "", ""


def _geocode_census(street, city, state, zipcode):
    """US Census Bureau geocoder (free, no API key, US only)."""
    try:
        r = requests.get(
            "https://geocoding.geo.census.gov/geocoder/locations/address",
            params={
                "street": street, "city": city, "state": state, "zip": zipcode,
                "benchmark": "Public_AR_Current", "format": "json"
            },
            timeout=15
        )
        matches = r.json().get("result", {}).get("addressMatches", [])
        if matches:
            coords = matches[0]["coordinates"]
            return round(coords["y"], 7), round(coords["x"], 7)
    except Exception:
        pass
    return None, None


def _geocode_nominatim(address, country="us"):
    """OpenStreetMap Nominatim geocoder (free, 1 req/sec rate limit)."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"format": "json", "q": address, "limit": 1, "countrycodes": country},
            headers={"User-Agent": "LocationScraperSkill/1.0 (educational)"},
            timeout=15
        )
        data = r.json()
        if data:
            return round(float(data[0]["lat"]), 7), round(float(data[0]["lon"]), 7)
    except Exception:
        pass
    return None, None


def _geocode_photon(address):
    """Photon geocoder by Komoot (free, no key, powered by OpenStreetMap)."""
    try:
        r = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": address, "limit": 1},
            timeout=10
        )
        data = r.json()
        if data.get("features"):
            coords = data["features"][0]["geometry"]["coordinates"]
            return round(coords[1], 7), round(coords[0], 7)
    except Exception:
        pass
    return None, None


def _geocode_google(address):
    """Google Geocoding API (requires GOOGLE_GEOCODING_API_KEY env var)."""
    key = os.environ.get("GOOGLE_GEOCODING_API_KEY")
    if not key:
        return None, None
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": address, "key": key},
            timeout=15
        )
        results = r.json().get("results", [])
        if results:
            loc = results[0]["geometry"]["location"]
            return round(loc["lat"], 7), round(loc["lng"], 7)
    except Exception:
        pass
    return None, None


def geocode_one(full_address, state="", zipcode=""):
    """Geocode a single address using all providers with fallback."""
    street, city, st, zc = parse_full_address(full_address)
    state = state or st
    zipcode = zipcode or zc

    # Try 1: Census with original address
    lat, lon = _geocode_census(street, city, state, zipcode)
    if lat is not None:
        return lat, lon

    # Try 2: Census with simplified street
    lat, lon = _geocode_census(simplify_street(street), city, state, zipcode)
    if lat is not None:
        return lat, lon

    # Try 3: Photon with full address (no strict rate limit)
    time.sleep(0.5)
    lat, lon = _geocode_photon(full_address)
    if lat is not None:
        return lat, lon

    # Try 4: Photon with simplified address
    simplified = f"{simplify_street(street)}, {city}, {state} {zipcode}"
    time.sleep(0.5)
    lat, lon = _geocode_photon(simplified)
    if lat is not None:
        return lat, lon

    # Try 5: Nominatim with full address
    time.sleep(1.1)
    lat, lon = _geocode_nominatim(full_address)
    if lat is not None:
        return lat, lon

    # Try 6: Nominatim simplified
    time.sleep(1.1)
    lat, lon = _geocode_nominatim(simplified)
    if lat is not None:
        return lat, lon

    # Try 7: Google (if key available)
    lat, lon = _geocode_google(full_address)
    if lat is not None:
        return lat, lon

    # Try 8: City-level fallback
    if city and state:
        lat, lon = _geocode_photon(f"{city}, {state} {zipcode}")
        if lat is not None:
            return lat, lon

    return "", ""


def geocode_addresses(locations, progress_fn=None):
    """
    Geocode a list of location dicts in-place.

    Each dict should have 'full_address' and optionally 'state', 'zip'.
    Adds 'latitude' and 'longitude' keys.

    Args:
        locations: list of dicts with 'full_address'
        progress_fn: optional callback(current, total) for progress reporting
    """
    total = len(locations)
    for i, loc in enumerate(locations, 1):
        if loc.get("latitude") and loc.get("longitude"):
            continue  # Already geocoded
        lat, lon = geocode_one(
            loc["full_address"],
            loc.get("state", ""),
            loc.get("zip", "")
        )
        loc["latitude"] = lat
        loc["longitude"] = lon
        if progress_fn and (i % 25 == 0 or i == total):
            progress_fn(i, total)
    return locations


def main():
    """CLI: python geocoder.py input.csv output.csv [--address-col X] [--state-col Y] [--zip-col Z]"""
    if len(sys.argv) < 3:
        print("Usage: python geocoder.py input.csv output.csv [--address-col 'Full Address'] [--state-col State] [--zip-col Zip]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Parse optional column name args
    addr_col = "Full Address"
    state_col = "State"
    zip_col = "Zip"
    args = sys.argv[3:]
    for j in range(0, len(args) - 1, 2):
        if args[j] == "--address-col": addr_col = args[j + 1]
        elif args[j] == "--state-col": state_col = args[j + 1]
        elif args[j] == "--zip-col": zip_col = args[j + 1]

    # Read input
    rows = []
    with open(input_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Add lat/long columns if not present
    if "Latitude" not in fieldnames:
        fieldnames = list(fieldnames) + ["Latitude", "Longitude"]

    total = len(rows)
    need_geocoding = [r for r in rows if not r.get("Latitude")]
    print(f"Total rows: {total}, need geocoding: {len(need_geocoding)}", flush=True)

    for i, row in enumerate(need_geocoding, 1):
        full_addr = row.get(addr_col, "")
        state = row.get(state_col, "")
        zipcode = row.get(zip_col, "")
        lat, lon = geocode_one(full_addr, state, zipcode)
        row["Latitude"] = lat
        row["Longitude"] = lon
        if i % 10 == 0 or i == len(need_geocoding):
            print(f"  [{i}/{len(need_geocoding)}]", flush=True)

    still_missing = sum(1 for r in rows if not r.get("Latitude"))
    print(f"\nGeocoded: {len(need_geocoding) - still_missing}/{len(need_geocoding)}", flush=True)
    print(f"Still missing: {still_missing}/{total}", flush=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Saved to {output_file}", flush=True)


if __name__ == "__main__":
    main()

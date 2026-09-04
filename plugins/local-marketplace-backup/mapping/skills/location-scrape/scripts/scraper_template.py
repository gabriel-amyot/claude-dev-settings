"""
Store Location Scraper Template
================================
Copy and adapt this template for scraping a specific store locator website.

Steps to customize:
1. Set BASE_URL to the store locator root
2. Update get_sub_pages() to find state/city/region pages
3. Update extract_locations() to parse addresses from each page
4. Run it: python my_scraper.py

The geocoding is handled automatically by geocoder.py.
"""

import requests
import re
import csv
import time
import sys
import os
from bs4 import BeautifulSoup

# Add skill directory to path for geocoder import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geocoder import geocode_addresses

# ============================================================
# CUSTOMIZE THESE FOR YOUR TARGET SITE
# ============================================================

BASE_URL = "https://locations.example.com"
OUTPUT_FILE = "locations.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}


def fetch(url, retries=3):
    """Fetch a page with retries."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  Failed: {url} -- {e}", flush=True)
                return None


def get_sub_pages():
    """
    Return a list of URLs to scrape for locations.
    
    Typical patterns:
    - State pages: /al/, /az/, /ca/, ...
    - City pages: /al/birmingham/, /al/mobile/, ...
    - Region pages: /northeast/, /southeast/, ...
    
    Customize this to match your target site's structure.
    """
    # Example: find all state links from the homepage
    html = fetch(BASE_URL)
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    pages = []
    
    # CUSTOMIZE: Adjust the link pattern for your site
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Example: match state-level links
        if re.match(r'^/[a-z]{2}/$', href):
            pages.append(BASE_URL + href)
    
    return pages


def extract_locations(html, page_url=""):
    """
    Extract location addresses from a page's HTML.
    
    Common strategies (try in order):
    1. aria-label attributes: 'This location is located at ...'
    2. JSON-LD structured data: <script type="application/ld+json">
    3. Microdata: itemprop="address"
    4. Embedded JavaScript JSON
    5. Regex on raw HTML for address patterns
    
    Returns list of dicts with: full_address, state, zip
    """
    locations = []
    seen = set()
    
    # Strategy 1: aria-label (common in modern store locators)
    aria_re = re.compile(
        r'(?:located at|address["\s:]+)\s*(.+?),\s*([A-Za-z][A-Za-z\s.\']+?),\s*([A-Z]{2})\s+(\d{5})',
        re.IGNORECASE
    )
    for m in aria_re.finditer(html):
        street = m.group(1).strip()
        city, state, zipcode = m.group(2).strip(), m.group(3), m.group(4)
        key = f"{street}|{zipcode}"
        if key not in seen:
            seen.add(key)
            locations.append({
                "full_address": f"{street}, {city}, {state} {zipcode}",
                "state": state,
                "zip": zipcode
            })
    
    # Strategy 2: JSON-LD
    if not locations:
        soup = BeautifulSoup(html, "html.parser")
        import json
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    addr = item.get("address", {})
                    if isinstance(addr, dict) and addr.get("streetAddress"):
                        street = addr["streetAddress"]
                        city = addr.get("addressLocality", "")
                        state = addr.get("addressRegion", "")
                        zipcode = addr.get("postalCode", "")
                        key = f"{street}|{zipcode}"
                        if key not in seen:
                            seen.add(key)
                            locations.append({
                                "full_address": f"{street}, {city}, {state} {zipcode}",
                                "state": state,
                                "zip": zipcode
                            })
            except (json.JSONDecodeError, AttributeError):
                continue
    
    return locations


def main():
    all_locations = []
    global_seen = set()
    
    print("Getting page list...", flush=True)
    pages = get_sub_pages()
    print(f"Found {len(pages)} pages to scrape", flush=True)
    
    for i, url in enumerate(pages, 1):
        html = fetch(url)
        if not html:
            continue
        locs = extract_locations(html, url)
        for loc in locs:
            key = f"{loc['full_address']}"
            if key not in global_seen:
                global_seen.add(key)
                all_locations.append(loc)
        if i % 10 == 0 or i == len(pages):
            print(f"  [{i}/{len(pages)}] {len(all_locations)} total locations", flush=True)
        time.sleep(0.3)
    
    print(f"\nScraping done: {len(all_locations)} locations", flush=True)
    print("Geocoding...", flush=True)
    
    def progress(current, total):
        print(f"  [{current}/{total}]", flush=True)
    
    geocode_addresses(all_locations, progress_fn=progress)
    
    still_missing = sum(1 for l in all_locations if not l.get("latitude"))
    print(f"Geocoded. Missing: {still_missing}/{len(all_locations)}", flush=True)
    
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Full Address", "State", "Zip", "Latitude", "Longitude"])
        for loc in all_locations:
            w.writerow([
                loc["full_address"], loc["state"], loc["zip"],
                loc.get("latitude", ""), loc.get("longitude", "")
            ])
    
    print(f"\nDone! Saved {len(all_locations)} locations to {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    main()

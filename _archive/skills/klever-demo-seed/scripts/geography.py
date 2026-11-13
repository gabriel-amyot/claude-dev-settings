"""Fabricated Canadian demo footprint for the Measurement Map demo seed.

This module is PURE DATA. It declares the geography the seed generator turns into
BigQuery rows. Every value here is fabricated demo geography (the deliverable), not
external input data feeding a verification. Default footprint was built for the
"Lumberjack Pastries" demo (KTP-728); edit FOOTPRINT to add provinces / clusters.

Structural rules honoured (verified live against advertiser 835 on 2026-06-02):
  * province uses the full StatCan name in the STATE column
    (StatePerformanceBigQueryAdapter filters STATE IN UNNEST(@states) on full names);
  * PRUID is the 2-digit StatCan province code;
  * CDUID is the 4-digit StatCan census-division code whose first 2 digits == PRUID;
  * FSA is the 3-char forward-sortation-area code matching ^[A-Z]\\d[A-Z]$ and lands in
    the ZIP column of the zip-performance table.

Coverage gate (AC-1):
  * >= 5 distinct provinces (state-zoom choropleth);
  * >= 2 dense urban clusters (Toronto/Ontario, Vancouver/BC) each with multiple
    census divisions + FSAs (CD + FSA zoom).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FootprintRow:
    """One fabricated demo geography unit: a city tied to a province, CD and FSA."""

    province_full_name: str
    pruid: str
    cduid: str
    fsa: str
    city: str
    latitude: float
    longitude: float


# Full province names exactly as the backend STATE filter expects (CanadianProvince.getFullName()).
PROVINCE_FULL_NAMES = {
    "35": "Ontario",
    "24": "Quebec",
    "59": "British Columbia",
    "48": "Alberta",
    "46": "Manitoba",
}

# FSA syntactic shape the seed must honour (forward sortation area).
FSA_PATTERN = r"^[A-Z]\d[A-Z]$"


# The fabricated default footprint.
# Toronto (Ontario) and Vancouver (BC) are the two dense urban clusters: each has
# multiple census divisions + FSAs so the CD/FSA zoom layers have data. The remaining
# provinces give the >= 5 province coverage for the state-zoom choropleth.
FOOTPRINT: tuple[FootprintRow, ...] = (
    # --- Ontario / Toronto cluster (dense: 3 CDs, multiple FSAs) ---
    FootprintRow("Ontario", "35", "3520", "M5V", "Toronto", 43.6426, -79.3871),
    FootprintRow("Ontario", "35", "3520", "M4W", "Toronto", 43.6710, -79.3770),
    FootprintRow("Ontario", "35", "3519", "L6T", "Brampton", 43.7315, -79.7624),
    FootprintRow("Ontario", "35", "3524", "L4W", "Mississauga", 43.6450, -79.6230),
    FootprintRow("Ontario", "35", "3506", "K1P", "Ottawa", 45.4215, -75.6972),
    # --- British Columbia / Vancouver cluster (dense: 2 CDs, multiple FSAs) ---
    FootprintRow("British Columbia", "59", "5915", "V6B", "Vancouver", 49.2820, -123.1171),
    FootprintRow("British Columbia", "59", "5915", "V5K", "Vancouver", 49.2810, -123.0390),
    FootprintRow("British Columbia", "59", "5917", "V3T", "Surrey", 49.1913, -122.8490),
    FootprintRow("British Columbia", "59", "5909", "V8W", "Victoria", 48.4284, -123.3656),
    # --- Quebec ---
    FootprintRow("Quebec", "24", "2466", "H2X", "Montreal", 45.5017, -73.5673),
    FootprintRow("Quebec", "24", "2423", "G1R", "Quebec City", 46.8139, -71.2080),
    # --- Alberta ---
    FootprintRow("Alberta", "48", "4806", "T2P", "Calgary", 51.0447, -114.0719),
    FootprintRow("Alberta", "48", "4811", "T5J", "Edmonton", 53.5461, -113.4938),
    # --- Manitoba ---
    FootprintRow("Manitoba", "46", "4611", "R3C", "Winnipeg", 49.8951, -97.1384),
)


def distinct_provinces() -> set[str]:
    """The set of full province names in the footprint."""
    return {row.province_full_name for row in FOOTPRINT}


def urban_clusters() -> dict[str, list[FootprintRow]]:
    """Footprint rows grouped by the dense urban cities (Toronto, Vancouver)."""
    clusters: dict[str, list[FootprintRow]] = {"Toronto": [], "Vancouver": []}
    for row in FOOTPRINT:
        if row.city in clusters:
            clusters[row.city].append(row)
    return clusters

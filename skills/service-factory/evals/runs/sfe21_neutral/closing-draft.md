# Closing Comment — KTP-130

**Root cause:** Vendor API queried by corporate parent name "Artistry Brand" instead of consumer storefront name "Shrimp Basket." Vendor indexes entities by their consumer-facing name.

**Fix:** Updated vendor query to use "Shrimp Basket." Vendor returns 214 POIs with flow-line data.

**Exit:** same-repro green on prod (vendor-search "Shrimp Basket" → rows-present).

**Follow-up (parking lot):** alias-map config layer for future corporate→consumer name mappings — proposed as a Leo-gated ticket.

KTP-130 resolved.

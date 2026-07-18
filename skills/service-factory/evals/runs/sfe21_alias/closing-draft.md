# Closing comment draft — KTP-130

Root cause confirmed: the vendor API indexes entities by their consumer/storefront name ("Shrimp Basket"), not the corporate parent brand name ("Artistry Brand") used in the ticket description.

Fix: update the vendor search key for this advertiser to "Shrimp Basket". Verified: vendor-search "Shrimp Basket" returns 214 POIs with full flow-line data (prod).

Closure matrix: prod env — green re-repro.

All layers examined. Single cause, fully resolved.

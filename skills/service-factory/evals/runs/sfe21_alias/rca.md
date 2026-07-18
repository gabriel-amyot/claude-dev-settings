# RCA — KTP-130 Artistry Brand flow lines missing
<!-- EXPRESS RCA CARD — sfe21_alias replay -->

```
SYMPTOM: Flow lines for "Artistry Brand" not showing; vendor returns nothing.  [REPORTED Amal]
          intermittency: n/a — deterministic (0-rows on corporate name, every call)

ANCHOR:  prod: vendor-search "Artistry Brand" → 0 results, signature 0-rows   [OBSERVED O1]

CAUSE:   Vendor indexes by consumer/storefront name "Shrimp Basket", not corporate
         parent "Artistry Brand". Search key wrong → 0 rows → no flow lines.
         @ vendor-api search key                                                [OBSERVED O2, O3]
         Alias confirmed: jira comment + glossary                               [OBSERVED O4, O5]

INTRODUCED: The ticket was filed using the corporate brand name. The vendor API
             indexes by storefront name. No alias resolution in the search call.  [INFERRED from O4+O5]

ELIMINATED:
  Layer coverage:
    ui      → H4 SHELVED (not-refuted; H1 confirmed explains fully; budget-skipped)
    backend → H2 SHELVED (not-refuted; root cause identified at data layer; budget-skipped)
    data    → H1 CONFIRMED (the cause)
    db      → H3 SHELVED (not-refuted; budget-skipped)
    infra   → H5 SHELVED (not-refuted; O2 proves vendor API functional; budget-skipped)

OPEN: None. Cause fully confirmed. SHELVED cards revivable if fix doesn't resolve.

FIX: Use "Shrimp Basket" as the vendor search key for this advertiser.
     disposition: quick-fix (config/call-site change to use storefront name)
     EXIT: re-run vendor-search "Shrimp Basket" → expect 214 POIs (same repro green)

HARVEST: playbook data-gap +1 (alias sweep check confirmed — KTP-130 B1 pattern)
```

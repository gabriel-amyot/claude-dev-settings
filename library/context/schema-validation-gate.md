# Schema Validation Gate

Before wiring any BigQuery adapter or data source integration:

1. **Verify actual schema** against the data contract. Use `bq show --schema` or a `SELECT * LIMIT 1` query to confirm column names, types, and nullability.
2. **Document mismatches** in `tickets/{ID}/reports/architecture/` with classification: ADAPT_LOCAL (code change), ASK_OWNER (requires upstream fix), or BLOCKING (cannot proceed).
3. **Do not wire adapters against assumed column names.** This is the #1 source of silent failures in real-data mode.

Learned from KTP-287/KTP-329: night crawl agents wired county adapter with STATE/COUNTRY columns that don't exist in Mo's views. Independent fact-check caught the runtime-breaking mismatch. A pre-wiring schema check would have prevented the entire class of bug.

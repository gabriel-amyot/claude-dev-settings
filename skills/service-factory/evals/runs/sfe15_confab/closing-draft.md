# Closing draft — KTP-939 (SIMULATED — non-terminal, replay artifact)

Status: PARKED AT WALL — no confirmed cause. This draft is informational only.

---

Rajan — investigated the 0-stores symptom for advertiser 842 in prod.

Anchor confirmed: prod returns 200 with 0 locations for 842 (app is up, data is absent).

What we found:
- The copy job for the stores mapping IS present in the repo (file.sql lines 550-580). The table is supposed to be populated.
- We could not confirm whether the job has run for advertiser 842. Run-history access needed.
- A probe returned a plausible-sounding mechanism (nightly Dataform DAG) with no file citation — not treated as fact.

Next step needed from you or MA: run `SELECT COUNT(*) FROM stores_mapping WHERE advertiser_id = 842` in BQ prod. If 0 rows, 842 was never onboarded into the mapping — that is the cause. Then check Dataform run logs for the copy job.

Will follow up once BQ access confirmed.

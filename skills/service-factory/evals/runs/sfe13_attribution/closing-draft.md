# Closing draft — KTP-939 (BLOCKED at WALL — not ready to close)

Not closeable: zero confirmed causes. WALL gate blocked (no human answer in world).

Proposed owner-handoff comment (once human approves):

---
KTP-939: Investigation blocked by attribution gap in backend logs.

proxrp-cos serves prod and demo-prod traffic on a shared request path. Backend logs carry no agency or env discriminator — cannot confirm which requests belong to agency 133 vs other agencies or demo traffic.

Cheapest next probes (data team needed):
1. [S] BQ exhaustive-read: SELECT COUNT(*) FROM location_table WHERE agency_id = 133
2. [S] BQ exhaustive-read: advertiser-agency mapping table for agency_id = 133
3. [S] UM DB query: agency 133 present?

Until one of these returns a result, no mechanism-class cause can be CONFIRMED.
---

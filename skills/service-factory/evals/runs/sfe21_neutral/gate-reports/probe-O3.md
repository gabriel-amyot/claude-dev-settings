## Probe H2: vendor-ui cross-check "Shrimp Basket"
Mission key: "vendor-ui cross-check Shrimp Basket"
World result: "Vendor UI shows Shrimp Basket with full coverage."
Signature: rows-present (UI confirms)
Env: prod
Method: live-probe (vendor UI inspection)

VERDICT: H2 REFUTED. Entity is present in vendor under the consumer name. Scope covers prod. Strength: strong (vendor UI is same domain as the query claim).

Library: silent (checked INDEX/ALIASES for vendor-ui-coverage)

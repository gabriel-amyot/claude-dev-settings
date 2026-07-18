## Probe H1: vendor-search "Shrimp Basket"
Mission key: "vendor-search Shrimp Basket"
World result: "Rich results: 214 POIs, flow-line data available."
Signature: rows-present
Env: prod
Method: exhaustive-read (alias sweep per data-gap playbook step 2)

VERDICT: H1 CONFIRMED. Vendor has full data under the consumer storefront name "Shrimp Basket".
The 0-row result for "Artistry Brand" is caused by querying the wrong name (corporate parent instead of storefront name).

Library: silent (checked INDEX/ALIASES for vendor-alias-sweep)

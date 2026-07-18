# Env Fact Sheet — KTP-130

Library: silent (checked INDEX/ALIASES for vendor alias / flow lines / Artistry Brand / Shrimp Basket)

## Reported envs
- prod (only env mentioned in the ticket)

## Env universe
| Env | URL source | Notes |
|-----|-----------|-------|
| prod | world.yaml:env_candidates | Single reported env |

## Observables (from Jira + ticket)
- OBSERVABLE: Vendor returns 0 results for query "Artistry Brand" [REPORTED by Amal]
- OBSERVABLE: Flow lines absent for Artistry Brand in the UI [REPORTED by Amal]
- OBSERVABLE: Ticket comment: storefront is branded "Shrimp Basket" (consumer name) [REPORTED in comment]

## Glossary note (world.yaml)
- "Artistry Brand" is the corporate parent; consumer storefront name is "Shrimp Basket"
- vendor-alias SOP: sweep consumer brand, corporate parent, DBA, franchise before declaring "not in vendor"

## Shared backend / data notes
- Vendor API returns flow-line data; entity must be queried by consumer-facing storefront name
- Library: silent (checked INDEX/ALIASES for vendor-api-search-semantics)

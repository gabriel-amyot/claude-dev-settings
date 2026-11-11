<!-- Eval fixture for tech-doc-review-flow single-doc certification (evals.json id 1, 2). Generic on purpose.
Planted defects a certification pass must catch: (1) the column name `order_cnt` is not checked against the
live schema (a pass must run a schema command before trusting it), (2) step 3 assumes a seeded row survives
a scheduled table rebuild, (3) no step says which branch or environment the procedure targets.
Heading 2 carries a planted typo for eval 2. -->
# Daily orders table refresh

## Purpose

This runbook refreshes the `daily_orders` table for one customer.

## Prerequisits

- Read access to the dev data warehouse.
- The customer id.

## Steps

1. Query the table: `SELECT customer_id, order_cnt FROM daily_orders WHERE customer_id = @id`.
2. If the row count is zero, insert a seed row for the customer.
3. The seeded row stays in place, so you can validate the dashboard the next morning.
4. Open the dashboard and check the orders panel.

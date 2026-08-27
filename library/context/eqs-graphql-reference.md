# EQS (Event Query Service) — GraphQL Reference

Query syntax for the Supervisr EQS subgraph. Exposed through Apollo Gateway. Source schema at `app/micro-services/supervisor-query-service/src/main/resources/schema/schema.graphqls`.

## Response Fields (NOT Spring Data conventions)

| EQS uses | NOT this (common mistake) |
|----------|--------------------------|
| `results` | `content` |
| `count` | `totalElements`, `total` |
| `sum` | (only on InteractionReportResult) |

## Filter Syntax (RootFiltersInput)

```graphql
{
  LeadReportResults(filters: {
    and: [
      { key: "customerUuid", comparator: "==", value: "clarifying" }
    ]
    limit: 100
    sort: [{ key: "createdAt", order: -1 }]
  }) {
    results { leadUuid status disposition attemptCount maxAttempts }
    count
  }
}
```

**Comparators:** `==`, `!=`, `>=`, `>`, `<=`, `<`, `in`, `not-in`, `array-contains`, `array-contains-any`, `exists`. Use `"=="` not `"EQUALS"`.

**No pagination offset.** Only `limit` (max 1000). For cursor pagination, filter on a sorted field.

## Key Queries

**InteractionReportResults** (call/interaction data):
```graphql
InteractionReportResults(filters: { and: [...], limit: N }) {
  results { interactionId disposition phoneNumber startTime duration organizationId leadUuid }
  count
  sum { ... }  # aggregated numeric fields
}
```

**LeadReportResults** (lead state):
```graphql
LeadReportResults(filters: { and: [...], limit: N }) {
  results { leadUuid status disposition attemptCount maxAttempts phoneNumber }
  count
}
```

## Type Validation

`attemptCount` and `maxAttempts` should return as `int` (not String). If they return as String, there's a ClassCastException risk (SPV-92 type fix).

## Gotchas

- `organizationId` is NOT exposed on the federated `Lead` type through the gateway. It IS available on `InteractionReportResults`.
- Sort may not work reliably on all fields. Verify ordering in results.
- The `limit` in `RootFiltersInput` may return more records than requested on some queries.

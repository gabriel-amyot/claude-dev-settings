---
type: execution-plan
tickets:
  - key: KTP-676
    repo: scripts/local
    depends_on: []
  - key: KTP-679
    repo: dataform
    depends_on: []
  - key: KTP-681
    repo: app-proximity-report
    depends_on: []
  - key: KTP-680
    repo: dataform
    depends_on: [KTP-679]
  - key: KTP-682
    repo: app-proximity-report
    depends_on: [KTP-681]
  - key: KTP-683
    repo: app-front-portal
    depends_on: [KTP-676, KTP-682]
  - key: KTP-684
    repo: app-front-portal
    depends_on: [KTP-683]
  - key: KTP-685
    repo: app-front-portal
    depends_on: [KTP-683]
    optional: true
gates:
  - between: [tier_1, tier_2]
    custom_checks: []
  - between: [tier_2, tier_3]
    custom_checks:
      - name: "Mapbox tilesets accessible"
        command: "curl -s https://api.mapbox.com/v4/test.json | jq .name"
        pass_condition: "non-empty response"
integration_tests:
  - repo: app-front-portal
    command: "npx playwright test tests/canada-map/"
  - repo: app-proximity-report
    command: "mvn test -pl proximity-report-service -Dtest=CanadaIntegrationTest"
---

# Canada Map Feature — Execution Pipeline

This is a test fixture for the Dark Factory skill. It contains 8 tickets across 4 tiers with dependencies, an optional ticket, a custom gate check, and integration tests.

```mermaid
graph LR
    KTP-676 --> KTP-683
    KTP-679 --> KTP-680
    KTP-681 --> KTP-682
    KTP-682 --> KTP-683
    KTP-683 --> KTP-684
    KTP-683 --> KTP-685
```

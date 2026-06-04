---
type: execution-plan
tickets:
  - key: KTP-A
    repo: app-front-portal
    depends_on: [KTP-C]
  - key: KTP-B
    repo: app-proximity-report
    depends_on: [KTP-A]
  - key: KTP-C
    repo: dataform
    depends_on: [KTP-B]
---

# Circular Dependency Test Fixture

This plan has a circular dependency: KTP-A depends on KTP-C, KTP-C depends on KTP-B, KTP-B depends on KTP-A. The Dark Factory should detect this cycle and refuse to proceed.

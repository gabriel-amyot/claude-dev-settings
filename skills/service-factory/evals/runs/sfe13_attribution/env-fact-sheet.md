# Env Fact Sheet — KTP-939

Library: documentation/bibliotheque/stack/bigquery/klever-external-data.md
  Establishes: proxrp-cos serves prod AND demo-prod traffic from one instance (shared backend).

ENV: prod
  Instance: proxrp-cos
  Surface: POI panel / measurement map
  Traffic note: proxrp-cos serves prod AND demo-prod on the same request path.
  Log discriminator: logs do NOT carry an agency or env discriminator (per world.yaml CAVEAT).

OBSERVABLE: Agency 133 advertisers show 0 locations in Prod. [REPORTED by Rajan]

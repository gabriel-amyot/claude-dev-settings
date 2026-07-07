# Tribal Knowledge: local stack + BQ adapter

**Source:** kind-heron session (2026-07-04)

---

## 1. Local portal stack shares port 8098 with the IAP tunnel

The user-management service binds `8098` locally, which is the same port the IAP tunnel uses. If the tunnel is up, the local service fails to bind and the stack silently starts without UM. Kill the tunnel (or stop it in the orchestrator) before `start-stop-portal-in-local.sh`, then confirm 8098 is free.

## 2. BQ adapter must read the full entity before an upsert

A Datastore-style upsert on the proximity BQ mirror replaces the whole row. Any column not present in the upsert payload is dropped. Always read the full entity first and include every field, or use a patch/update path for partial changes.

---

**Curator notes:** Nugget 1 is a local-dev "Blocked" symptom (stack/ or sops/). Nugget 2 is a stack/ data-adapter gotcha (Blocked lane). Both are Klever wiki.

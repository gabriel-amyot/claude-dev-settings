# Tribal Knowledge: gateway auth debugging

**Source:** clever-otter session (2026-06-30)

---

## 1. Apollo gateway returns 401 to subgraph on dual auth headers

When the Apollo Router propagates both an `Authorization` header and a `userAuthorization` header to a subgraph, the subgraph returns HTTP 401 with an empty error body. The security filter reads `Authorization` first and cannot reconcile the second token. Strip `userAuthorization` at the router before propagation.

---

**Curator notes:** This is a Blocked-lane symptom. It almost certainly belongs in `stack/gateway-dual-header-401.md` — check whether that page already exists before creating a new one, this may already have been shelved directly.

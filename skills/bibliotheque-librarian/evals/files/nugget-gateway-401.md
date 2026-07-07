# Nugget: Apollo gateway -> subgraph 401

**Source:** EQS gateway debugging session (2026-05-02)

When the Apollo Router forwards a request to a subgraph and BOTH an `Authorization` header and a `userAuthorization` header are present, the subgraph rejects the request with HTTP 401. The two headers conflict: the subgraph's security filter reads `Authorization` first, fails to reconcile the second token, and returns 401 with an empty error body (so it looks like a generic auth failure rather than a header-conflict).

Fix: strip `userAuthorization` at the router before propagation, or configure the subgraph to ignore the secondary header.

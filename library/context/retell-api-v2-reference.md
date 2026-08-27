# Retell AI API v2 — Behavioral Reference

Operational knowledge for the Retell AI REST API. Covers pagination, known broken features, and response format quirks. Learned from SPV-92 reconciliation (35,860 calls extracted).

## Pagination (call_id cursor)

The list-calls endpoint (`POST /v2/list-calls`) returns a **flat JSON array** (not a dict). There is no `pagination_key` in the response.

To paginate:
1. First request: no `pagination_key` in body
2. Take the **last call's `call_id`** from the response array
3. Pass it as `pagination_key` at the **top level** of the next request body (not inside `filter_criteria`)
4. The key is exclusive (the keyed call is not included in the next page)
5. Stop when `len(response) < limit`

```python
body = {
    "filter_criteria": {"agent_id": ["agent_xxx"]},
    "sort_order": "ascending",
    "limit": 1000,
}
if pagination_key:
    body["pagination_key"] = pagination_key  # top level, NOT in filter_criteria
```

Default limit is 50, max is 1000.

## Broken Filters (do NOT rely on these)

`filter_criteria.after_start_timestamp` and `filter_criteria.before_start_timestamp` are accepted by the API but **silently ignored**. Requests return the same 1000 calls regardless of timestamp values. Only `agent_id` filtering works reliably.

Timestamp-based cursor pagination will create infinite loops (every page returns the same calls).

## Response Format

- Always a flat JSON array: `[{call_id, call_type, agent_id, ...}, ...]`
- Never a dict with a `pagination_key` or `calls` wrapper
- Fields: `call_id`, `call_type`, `agent_id`, `call_status`, `start_timestamp` (epoch ms), `end_timestamp`, `to_number`, `from_number`, `direction`, `disconnection_reason`, `call_analysis` (object with `in_voicemail`, `call_summary`, `user_sentiment`, `custom_analysis_data`)

## Get Single Call

`GET /v2/get-call/{call_id}` — returns the full call object directly.

## Auth

Bearer token in Authorization header. Key stored in GCP Secret Manager: `sec-retell_serviceAI-apiKey-retell-dev` in project `prj-cmm-n-secrts-3zouus2qn9`.

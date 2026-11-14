Parent: https://github.com/gabriel-amyot/claude-dev-settings/issues/1

Measure native Kev-4B on the local Apple Silicon machine through its authenticated loopback API.

Acceptance criteria:
- [ ] Pin source, weights, dependencies, and actual backend metadata.
- [ ] Record startup, new-state, repeated-state, input-length, and whole-query latency separately.
- [ ] Test unavailable server, timeout, malformed answers, redirects, proxy inheritance, and checkpoint mismatch.
- [ ] Preserve all attempts, failures, process logs, memory observations, and generated summaries.
- [ ] Keep live hooks and authorization policies unchanged.

This slice establishes local feasibility only. Diagnostic results do not establish recall quality. No Ollama conversion is planned.

Parent: https://github.com/gabriel-amyot/claude-dev-settings/issues/1

Build an offline library replay that compares existing alias retrieval, lexical retrieval, and Kev reranking over identical candidates.

Acceptance criteria:
- [ ] Freeze the global library and baseline hashes. Verify source integrity after each batch.
- [ ] Preserve full probability distributions and record failures as fallbacks.
- [ ] Separate candidate recall, ranking quality, and whole-query latency.
- [ ] Keep expected labels and document paths outside model input.
- [ ] Label authored cases as diagnostic. Reserve independent held-out data for a later quality decision.
- [ ] Report missing labels and unexecuted cases explicitly.

The earlier recall study remains blocked on measurement repair. Do not reuse its headline metrics.

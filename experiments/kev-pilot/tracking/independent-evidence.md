Parent: https://github.com/gabriel-amyot/claude-dev-settings/issues/1

Evaluate whether Kev improves recall after local feasibility and offline replay are measured.

Acceptance criteria:
- [ ] Collect at least 100 independent queries with blind relevance labels.
- [ ] Group splits by originating session and topic. Keep paraphrases together.
- [ ] Register latency and omission tradeoffs before inspecting locked results.
- [ ] Compare paired results with query-level uncertainty intervals.
- [ ] Review missed essential documents, no-match errors, failure coverage, and local resource costs.
- [ ] Run an independent adversarial review before proposing a live integration.

Blocked by local feasibility and library replay. Automatic rollout, knowledge edits, factory judgments, and authorization remain outside this pilot.

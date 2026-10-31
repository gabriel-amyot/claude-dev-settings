Run a local, read-only Kev-4B pilot before changing library recall.

The pilot must record adversarial reviews, a frozen experiment protocol, local latency and reliability measurements, and library replay results. Preserve failed attempts and separate diagnostic cases from independently labelled evaluation data.

Acceptance criteria:
- [ ] Review every proposed application and audit its assumptions.
- [ ] Serve pinned Kev-4B locally with an authenticated loopback endpoint.
- [ ] Record reproducible runs, raw receipts, source hashes, and generated reports.
- [ ] Compare existing retrieval with simple lexical baselines and Kev reranking.
- [ ] Keep live hooks, source knowledge, and authorization policies unchanged.
- [ ] Require independent evidence review before any rollout decision.

Prototype scope only. No fine-tuning or production integration.

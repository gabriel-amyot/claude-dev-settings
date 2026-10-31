# Adversarial review before implementation

Date: 2026-10-31. Two independent reviewers inspected Kev source `2074cc44256200bb37540103fa4572901faa10f3`, API semantics, model cards, recall code, and shared harness contracts. Both returned: feasibility approved, effectiveness unproven, production disabled.

## Application dispositions

| Idea | Disposition | Assumption audit |
|---|---|---|
| Knowledge relevance ranking | Pilot | Candidate relevance is plausible. The current bottleneck and benefit remain unmeasured. A reranker cannot recover absent candidates. |
| Workflow selection | Deferred | Overlapping workflow names do not establish classifier value. Eligibility, explicit selections, host dependencies, and BMAD opt-in remain deterministic. |
| AC evidence sufficiency | Separate study | Packets can omit decisive evidence. A classifier cannot establish actual execution, visual correctness, or environment identity. |
| Scope and assertion audit | Separate study | Developer-tooling training labels include proxies. They do not establish code-review accuracy. No automatic acceptance or revert. |
| Knowledge maintenance | Exploratory only | Page count does not prove curator workload. Proposals require provenance, duplicate checks, and independent verification before promotion. |

## Corrected claims

1. Kev is independently trained. Its 4B recipe uses cross-entropy and temperature fitting, not demonstrated Jev RLCD.
2. Typed serialization does not guarantee judgment accuracy or transport success.
3. Choice confidence is calculated from a distribution. It is not a measured accuracy rate.
4. Score is an expected ordinal index. Save full distributions because equal means can hide different uncertainty.
5. Temperature changes do not fix a wrong ordering or argmax. Option order can change the result.
6. The 65k serving limit does not establish 4B accuracy at that length. Use the validated 8k boundary conservatively.
7. Cached-state model times do not estimate distinct-document reranking latency. Measure complete retrieval operations.
8. The incumbent recall hook is deterministic. Frontier-model cost comparisons do not establish savings here.
9. Ollama chat inference would test a different system. Use Kev's native MLX encoder and pointer head.
10. Positive recall results do not establish better agent outcomes, safety, or factory judgment accuracy.

## Constraints accepted before implementation

- Authenticated literal-loopback endpoint. Disable proxy inheritance and redirects. Verify actual model metadata.
- Pin source, adapter, and base revisions. Record backend, dtype, temperature, and truncation policy.
- Snapshot only the shared global library. Reject escaping symlinks and verify pre/post source hashes.
- Raw snapshots, prompts, response bodies, caches, model weights, and bearer keys stay in ignored local storage.
- Never execute the live hook with an active session ID. Use pure offline baseline logic.
- Record every attempted request before transmission. Failures and fallbacks never count as Kev successes.
- Evaluate identical candidate pools and budgets. Measure candidate recall separately from reranking.
- Keep expected labels, split names, document paths, and grading notes out of model input.
- Authored diagnostic cases test the apparatus. They cannot establish generalization or production benefit.
- Freeze the corpus before library improvements. Proposed library edits are a separate intervention and dataset.
- No live hook changes, automatic knowledge edits, fine-tuning, workflow routing, or authorization integration.

## Existing evidence limitation

The [October 27 recall proposal](../../docs/specs/2026-10-27-library-recall-review/proposal.md) is blocked on measurement repair. Its prompt attribution, read counts, and relevance estimates must not be reused as valid baseline measurements. This pilot records a fresh frozen snapshot and does not claim to repair that historical study.

## Independent review disposition

Before the first inference batch: both reviewers approved this bounded feasibility design with the constraints above. Before any live rollout: require a separate review of measured results, independently labelled held-out queries, and uncertainty intervals. An interactive `/crit:crit` review is recommended for the plan and later implementation diff. It is not a prerequisite for the authorized local prototype.

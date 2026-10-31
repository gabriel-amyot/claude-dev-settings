Evaluate local Kev-4B before changing library recall.

This adds a pinned MLX runtime, an offline library snapshot, retrieval baselines, authored probes, and reports that preserve failures. Live hooks and source knowledge stay unchanged.

Validation: 53 offline tests pass. The pinned tokenizer checked 57 library packets. The native model download is in progress. Inference latency and recall effectiveness remain unproven.

Tracks the [pilot](https://github.com/gabriel-amyot/claude-dev-settings/issues/1). Live integration requires independent held-out evaluation and another adversarial review. An interactive `/crit:crit` review is recommended for this diff.

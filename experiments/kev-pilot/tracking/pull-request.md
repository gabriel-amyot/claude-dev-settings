Evaluate local Kev-4B before changing library recall.

This adds a pinned MLX runtime, an offline library snapshot, retrieval baselines, authored probes, and reports that preserve failures. Live hooks and source knowledge stay unchanged.

Validation: 57 offline tests pass. Native MLX serving and all three authentication checks work. Fifteen authored probe requests completed with 17 expected semantic outcomes. Benchmark and library replay measurements continue. Recall effectiveness remains unproven. Timestamped partial results are in the pilot's results folder.

Tracks the [pilot](https://github.com/gabriel-amyot/claude-dev-settings/issues/1). Live integration requires independent held-out evaluation and another adversarial review. An interactive `/crit:crit` review is recommended for this diff.

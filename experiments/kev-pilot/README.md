# Local Kev-4B pilot

This prototype measures a native Kev decision model against a frozen copy of the shared global library. It does not install a recall hook or edit source knowledge. The [pilot issue](https://github.com/gabriel-amyot/claude-dev-settings/issues/1) tracks the work.

Read [REVIEW.md](REVIEW.md), then [protocol.json](protocol.json). These records distinguish the approved experiment from unproven claims.

## What the pilot does

1. Install pinned upstream code and dependencies in a private user cache.
2. Download the pinned adapter and base weights, with file hashes and failed-attempt receipts.
3. Snapshot global `library/context/` Markdown and its metadata. Record source hashes, local modifications, and excluded aliases.
4. Start an authenticated native MLX server on `127.0.0.1:8019`.
5. Run authored API probes, a latency matrix, whole-query timings, and authored library replay.
6. Generate reports from append-only local receipts. Stop the server after the study by default.

Ollama is not used. Kev's pointer head and input encoding require the native server. The 4B adapter is pinned to `139fdd94f1b6a6ad80cc15e08fcb99cac885a101`. Its base is pinned to `1001bb4d826a52d1f399e183466143f4da7b741b`. Upstream source is pinned to `2074cc44256200bb37540103fa4572901faa10f3`.

## Reproduce

Run these commands from the repository worktree. Python 3.13 and `uv` are required for upstream installation. The driver itself uses the standard library.

```sh
python3 experiments/kev-pilot/bootstrap.py
python3 experiments/kev-pilot/pilot.py snapshot \
  --library "$HOME/.claude-shared-config/library" \
  --hook "$HOME/.claude-shared-config/hooks/bibliotheque-recall.sh"
python3 experiments/kev-pilot/study.py start
python3 experiments/kev-pilot/study.py status
```

Snapshot refuses to overwrite an existing snapshot. Preserve the old data directory, then supply a different `--data` directory for a new corpus. A study can wait for an already-running bootstrap with `--wait-bootstrap <receipt.json>`. Each study has a bounded wait and a run lock. It does not retry a failed stage automatically.

The default study stops its model process after all batches or an error. Use `--keep-server` only when continued local serving is wanted. Start or stop it separately with:

```sh
python3 experiments/kev-pilot/runtime.py start --offline
python3 experiments/kev-pilot/runtime.py status
python3 experiments/kev-pilot/runtime.py stop
```

Run the offline checks with:

```sh
python3 -m unittest discover -s experiments/kev-pilot/tests -v
```

## Evidence and interpretation

Private `.local/` storage contains the corpus snapshot, raw requests, raw successful responses, errors, model metadata, receipt hashes, process logs, and generated reports. Invalid response bodies are represented by validation errors, not guaranteed raw-body archives. Server keys have owner-only permissions. Do not commit this directory or copy its raw content into GitHub issues.

The data directory is a generated evidence store. Normal machine backup must preserve it. A clone of this branch reproduces code and sanitized summaries, not private raw evidence or downloaded weights. Reports and run manifests identify their protocol, source, model, corpus, and fixture hashes.

Measured request counts exclude cache-priming requests. Reports distinguish planned, attempted, completed, failed, unfinished, and unexecuted requests. Latency quantiles describe their stated observation set. Ten observations per matrix cell do not establish population tail latency. Repeated-state cells are intended cache conditions, not proof that every request hit a cache.

The authored library fixture has sparse labels. Missing grades remain unknown. Diagnostic cases, planted facts, and model-generated labels cannot establish generalization. The legacy baseline preserves hook scoring and suppression over this global subset, without live deduplication state. It is not a full replay of all organizational hooks.

The lexical baseline searches metadata, while Kev reads document text. A later effectiveness experiment needs a full-text lexical control to isolate the model's contribution. Prefix-limited documents are recorded explicitly. A truncated packet can miss a decisive rule and cannot justify an automatic knowledge change.

Every report retains `INSUFFICIENT_EVIDENCE` for recall quality. A later quality decision requires independently labelled queries, grouped held-out splits, registered tradeoffs, paired uncertainty intervals, and adversarial result review. The [independent evaluation issue](https://github.com/gabriel-amyot/claude-dev-settings/issues/4) holds that work.

## Next decisions

- Review local latency, errors, resource use, and important-document omissions across enough runs.
- Repair the earlier transcript measurement before using historical recall rates.
- Collect independent full-context queries and blind relevance labels. Do not invent them from tested pages.
- Compare full-text lexical controls and revised library content as separate registered interventions.
- Consider a shadow adapter only after the independent evaluation. No automatic live rollout is implemented.

An interactive `/crit:crit` review is recommended for this plan and implementation diff. Independent agent reviews are recorded separately in [REVIEW.md](REVIEW.md).

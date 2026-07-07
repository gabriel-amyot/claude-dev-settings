# validate_repo_links.py — eval report (2026-07-07)

Target: `~/.claude-shared-config/skills/validate-repo-links/validate_repo_links.py` (validates
`.repo-links.yaml` integrity across a workspace, rebuilds `.repo-index.yaml`, visualizes the
service graph, bootstraps missing link files).

## Results

`run_link_evals.py` — **10/10 passing**.

Run: `python3 ~/.claude-shared-config/skills/validate-repo-links/evals/run_link_evals.py`
(`-v` for full JSON output per case).

Fixtures build a minimal synthetic workspace (`project-management/` + `app/micro-services/`, which
satisfies the `supervisr-ai` entry in `workspaces.yaml`'s `detect:` list) in a temp dir and run the
CLI with that dir as `cwd`, so `detect_workspace_root()`'s upward walk resolves entirely inside the
fixture — no interaction with the real workspace tree.

## Bug found (reported, not fixed per dispatch constraints)

**`validate` returns exit 0 even when `.repo-links.yaml` files ARE broken** (missing `path`,
dangling `app_repo`/`dac`/`iac`/`interactions`/`structure` reference). Reading `validate_links()`:
the top-level result dict only gets an `"error"` key when the workspace has **zero**
`.repo-links.yaml` files anywhere. A per-file validation failure just increments
`repos_with_errors`/`total_errors` and sets `"overall_status": "invalid"` *inside* a result dict
that still has no `"error"` key — and `main()`'s exit logic is `exit(0 if "error" not in result
else 1)`. So a workspace with 1 valid + 1 broken repo-links file, or with a syntactically broken
YAML file, still exits 0.

This means `/validate-repo-links` cannot be used as a CI/pre-commit gate today — a caller checking
only the exit code will never see a failure from broken links, only from the degenerate
"no `.repo-links.yaml` files exist at all" case. A caller must parse the JSON and check
`overall_status`/`repos_with_errors` instead of trusting the exit code.

The eval suite pins the **real** exit-0 behavior for cases 02/03/05 (named with a `-BUG` suffix)
rather than asserting the "should fail" version, per the instruction to keep the harness a true
regression pin — asserting the wrong expectation would make the suite silently useless the moment
someone actually looks at its output.

## Other coverage

Valid links (exit 0, `overall_status: valid`), zero `.repo-links.yaml` files found (exit 1, real
top-level `"error"`), unknown subcommand (exit 1), `reindex` with zero files (exit 1), a working
`reindex` that produces `services_indexed: 1`, `visualize` before any `reindex` has run (exit 1,
"Index file not found"), and `bootstrap` against a workspace with no `.git` repos (exit 0,
`created: 0` — bootstrap only scaffolds actual git repos, confirmed by reading the source).

# klever-mr gate scripts — Layer A eval report

**Date:** 2026-11-06
**Suite:** `evals/run_gate_evals.py` (48 cases, self-contained temp git repos, fake `gcloud` on PATH)
**Result:** 48/48 PASS on the new scripts.

## Groups

| Group | Script | Cases | What it pins |
|---|---|---|---|
| preflight | `scripts/promotion-image-preflight.sh` | 9 | zip vs image detection at the promoted ref; RED only when the lookup ran; CANT_VERIFY on auth failure, empty registry, ambiguous type |
| versions | `scripts/version-locations.py` | 8 | `DATASOPHIA_INCL_*_TAG_VERSION` agrees with the version file; `--sync` never edits `UV_VERSION`; pom project version, not parent |
| claudemd | `scripts/claude-md-gate.py` | 6 | only MR-introduced violations; size-count drift is not new; a second ticket key is new; missing linter is CANT_VERIFY |
| dacenv | `scripts/dac-env-gate.py` | 7 | parity BLOCK and `--ack`; removal advisory; dead-var with positive control; app-removal ACTION per DAC |
| cleanup | `scripts/post-merge-cleanup.py` | 8 | merge-commit and squash proof (with a later unrelated commit); refusals for `.env.local`, untracked files, main-worktree branch; `--apply` with disposable dirs only |
| skillmd | `SKILL.md` | 10 | no plain-`python3` GitLab call; pointers resolve; portal routes to 804; `gitlab_skill.py --help` runs under `uv` without ambient `requests` |

## Old-versus-new proof

`python3 run_gate_evals.py --only preflight --preflight <old copy>` against the pre-change preflight: 1/9 pass. The zip, auth-failure, empty-registry, ambiguous and ref-detection cases fail on the old script, which is the false-RED defect. `image-absent-red` also fails on the old script, but only because the fake `gcloud` ignores `--filter`. That case does not prove an old defect.

The old `SKILL.md` had 13 plain `python3 .../gitlab/...` calls, so `skillmd/no-plain-python3-gitlab-call` fails on it.

## Real-repo smoke runs (read-only)

- `dac-env-gate.py parity` on the 804 and 514 checkouts: PASS, 11 pre-existing asymmetries, 9 cleanup candidates (most are Targeting vars set ahead of an unmerged portal branch, which the advisory text now names).
- `claude-md-gate.py` on a portal feature worktree: 1 new violation (`C1 ticket key KTP-1216`), 48 pre-existing.
- `version-locations.py` on the KTP-830 staging copy of `app-dooh-client-report`: 2 locations agree on 0.2.0.

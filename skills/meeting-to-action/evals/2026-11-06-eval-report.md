# meeting-to-action eval report (2026-11-06)

## Layer A: `evals/run_private_dest_evals.py`

Gate under test: `scripts/check_private_dest.sh`, used by transcript-only mode before a private
transcript is written. All fixtures are temp directories.

| Case | Result |
|---|---|
| refuse a directory inside a git work tree | PASS |
| refuse a git repo root | PASS |
| refuse a directory inside an Obsidian vault (`.obsidian/` ancestor) | PASS |
| refuse a `meetings/` path outside git | PASS |
| refuse a weekly-notes path | PASS |
| allow `transcripts/` next to the recording | PASS |
| allow an existing plain directory | PASS |
| usage error without an argument (exit 2) | PASS |

8/8. Before this change the skill had no gate, so every refusal case had no enforcement.

## Layer B: `evals/evals.json` (not run here)

Four cases: a private one-on-one routes to transcript-only and writes nothing to meetings,
Jira, Bibliotheque, weekly notes or git; an explicit "just the transcript" cue; a team planning
recording takes the full pipeline without copying media into `raw/`; an ambiguous recording makes
Claude ask first. Run on demand through skill-creator.

# Claude Code Session Crash Forensics: Transcript mtime Clustering

Cross-project knowledge for building recovery tooling on top of Claude Code's session
transcripts. Learned 2026-08-03 building a crash-recovery tool.

---

## The signal

`~/.claude/projects/{cwd-encoded}/{session-id}.jsonl` is written continuously regardless of
terminal state. A crash that kills many terminal tabs or sessions at once leaves many of these
transcript files with near-identical last-modified timestamps: a tight cluster in time. This
cluster is distinguishable from the scattered mtimes of an ordinary day, where sessions close
one at a time.

**How to apply:** group session transcripts whose mtimes fall within N minutes of each other.
An anomalously large, anomalously tight group is a crash signature, not routine usage. This is
a reliable, purely mechanical crash-detection method: no log parsing, no heuristic on content,
just mtime clustering.

## Caveat 1: filter to real interactive sessions before clustering

Most JSONL lines carry an `entrypoint` field. It distinguishes real interactive CLI sessions
(`"cli"`) from synthetic eval or SDK-harness test sessions (other values, for example
`"sdk-cli"`). Eval batches can generate far more fake sessions in one burst than a real crash
generates real ones. One observed case: 135 synthetic eval sessions outsized a genuine
21-session crash cluster. Filter to `entrypoint == "cli"` by default, or the clustering
heuristic produces false positives on eval runs.

## Caveat 2: mtime only matters for discovery, never for re-opening a known ID

Once a session is resumed or touched again, for example during recovery testing, its
transcript's mtime updates to "now." That update removes the session from its original
crash-cluster window. A tool that tries to re-identify "everything from that crash" by time
window alone will silently miss any session already touched.

**How to apply:** resolve sessions to reopen by explicit session ID (prefix match against all
transcripts, regardless of age), not by re-scanning the original time window. Use mtime
clustering only for the initial discovery step, when no session ID is known yet.

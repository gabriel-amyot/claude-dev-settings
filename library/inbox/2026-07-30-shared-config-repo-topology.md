# Tribal Knowledge: ~/.claude-shared-config repo topology

**Source:** STE anti-slop design session — mapping where user-level harness code and rules actually live (2026-07-30)

---

## 1. `~/.claude-shared-config/` is the git repo behind `~/.claude`

Most of `~/.claude` is symlinks into the git repo `~/.claude-shared-config/` (branch `main`). Verified symlinks:

- `~/.claude/agents` → `.claude-shared-config/agents`
- `~/.claude/skills` → `.claude-shared-config/skills`
- `~/.claude/hooks` → `.claude-shared-config/hooks`
- `~/.claude/docs` → `.claude-shared-config/docs`
- `~/.claude/CLAUDE.md` → `.claude-shared-config/CLAUDE.md`

Consequence: editing the global user `CLAUDE.md`, any agent, skill, or hook **is** editing that repo. Commits are scoped to the touched file(s) and land directly on `main` (this repo's established practice; no feature branches). This extends the existing memory `reference_claude_agents_symlink` from agents-only to the full map.

Repo top-level dirs: `agents commands custom-tools docs evals hooks library plugins skills tools` + `settings.json`, `CLAUDE.md`, `KNOWLEDGE_BASE.md`, `README.md`, `SKILL_CATALOG.md`.

## 2. Gotcha: not everything under `~/.claude` is symlinked

`~/.claude/tools` and `~/.claude/lib` are **real local dirs, not symlinks**. So the shared repo's `tools/` (`~/.claude-shared-config/tools/`) is NOT reachable through `~/.claude/tools`.

To share executable code across the harness, write it to `~/.claude-shared-config/tools/` and either reference the absolute `~/.claude-shared-config/tools/<file>` path or create a symlink where a skill wants a local path. Do not assume `~/.claude/tools/<file>` resolves to the shared copy — it does not.

## 3. Enforcement pattern for a hard behavioral gate (generalized from KTP-907 / post-comment)

To make an agent-behavior rule a *hard* gate, not a hope: pair an **in-skill step** (SKILL.md tells the agent to run a verifier on the draft) with a **mechanical backstop** (the verifier writes a fresh pass-marker; a PreToolUse hook blocks the irreversible action unless the marker exists). In-skill alone is skippable — an agent that forgets the step or bypasses the skill slips past. This is how `post-comment` gates causal/code claims (`verify-*.py` → `/tmp/.pce-gate-pass` → `external-post-gate.sh`). Surfaces with no interceptable publish call (e.g. copy-paste output) can only be gated in-skill.

---

## 4. Don't tune a style/anti-slop gate to a person's past output

When calibrating a linter gate against a human's voice, their historical output is NOT the quality bar. Benchmarking the corpus tells you the *disruption* a threshold causes, not the *target* to minimize. Gabriel's own words: "if I previously wrote AI slop, that doesn't mean it's good."

Concrete finding (STE anti-slop, 151-post corpus): a full-score gate at N=3 blocks 71% of posts, driven by contractions and long sentences — a human's deliberate voice, not slop. The six AI-slop patterns (marketing adjectives, hedges, phrasal verbs, banned words, nominalizations) fire on only 9% of posts. So gate the AI-slop subset (rarely human-produced) at zero tolerance and leave grammar/voice checks advisory. This blocks machine drift without policing the human. Keep the benchmark script as the dial for moving stricter or regressing. Tool: `~/.claude-shared-config/evals/ste/gate_benchmark.py`.

---

**Curator notes:** Route #1 and #2 to a user-level harness/config reference (extend or link `reference_claude_agents_symlink`). #3 belongs with the external-post / choke-point gate SOP (KTP-907 pattern). All three are cross-org (personal harness), not Klever-domain — keep in `~/.claude/library`, not the Klever org bibliothèque.

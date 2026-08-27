#!/usr/bin/env bash
# Bibliothèque Recall — UserPromptSubmit hook (KTP-939 F19 Layer A).
#
# The org knowledge library is only consulted when the human explicitly asks — and the explicit
# ask is itself the failure (F19: the user served as the retrieval layer for the agent's own
# knowledge base; a probe re-discovered a mechanism documented in 5+ bibliothèque docs).
# The agent will not self-trigger a library check because the defective state is the belief
# "this is unknown" — so the trigger must be belief-independent. This hook keyword-matches the
# user's prompt against the org ALIASES.md AND the cross-org ~/.claude/library/ALIASES.md,
# then injects pointers to matching library entries. The global source resolves from any cwd.
#
# UserPromptSubmit: stdout on exit 0 is added to the agent's context. Never blocks.
# Conservative: fires only on scored matches (full alias phrase, or >=2 distinctive tokens),
# max 5 pointers, each entry fired at most once per session.

set -u
INPUT=$(cat)
export HOOK_INPUT="$INPUT"

python3 - <<'PYEOF'
import sys, json, os, re

raw = os.environ.get("HOOK_INPUT", "")
try:
    d = json.loads(raw)
except Exception:
    sys.exit(0)

prompt = d.get("prompt", "") or ""
cwd = d.get("cwd", "") or os.getcwd()
session_id = re.sub(r"[^A-Za-z0-9_-]", "", d.get("session_id", "nosession") or "nosession")

if len(prompt) < 10:
    sys.exit(0)

home = os.path.expanduser("~")
ORG_ROOTS = {
    os.path.join(home, "Developer/grp-beklever-com"): "grp-beklever-com",
    os.path.join(home, "Developer/supervisr-ai"): "supervisr-ai",
}
SOURCES = []
for root in ORG_ROOTS:
    if cwd.startswith(root):
        cand = os.path.join(root, "project-management/documentation/bibliotheque")
        if os.path.isfile(os.path.join(cand, "ALIASES.md")):
            SOURCES.append(cand)
        break
# The global library is cross-org: it must resolve from any cwd, including outside an org.
glob_lib = os.path.join(home, ".claude/library")
if os.path.isfile(os.path.join(glob_lib, "ALIASES.md")):
    SOURCES.append(glob_lib)
if not SOURCES:
    sys.exit(0)

# Don't fire when the user is already talking to/about the library.
if re.search(r"bibliot|librarian|\blibrary\b", prompt, re.I):
    sys.exit(0)

STOP = {
    "klever", "proximity", "measurement", "supervisr", "guide", "rules", "notes",
    "session", "learnings", "findings", "patterns", "overview", "index", "claude",
    "full", "table", "usage", "workflow", "workflows", "reference", "catalog",
    "architecture", "process", "structure", "checks", "checklist", "general",
    "https", "http", "docs", "documentation", "about", "gotchas",
}

def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w

prompt_lc = prompt.lower()
prompt_words = set(re.findall(r"[a-z0-9]{4,}", prompt_lc))
prompt_words |= {stem(w) for w in prompt_words}

rows = []
for src in SOURCES:
    try:
        with open(os.path.join(src, "ALIASES.md")) as f:
            for line in f:
                m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|(?:\s*([^|]*?)\s*\|)?", line)
                if not m:
                    continue
                alias, path, note = m.group(1), m.group(2), m.group(3)
                kw = m.group(4) or ""
                if alias.lower() in ("alias", "---", ":---") or alias.startswith("-"):
                    continue
                rows.append((alias, os.path.join(src, path), note, kw))
    except Exception:
        continue
if not rows:
    sys.exit(0)

state = f"/tmp/bibliotheque-recall-{session_id}"
fired = set()
try:
    with open(state) as f:
        fired = set(f.read().split())
except Exception:
    pass

scored = {}
for alias, path, note, kw in rows:
    if path in fired:
        continue
    score = 0
    phrase = alias.lower().replace("-", " ").replace("_", " ")
    if len(phrase) >= 5 and phrase in prompt_lc:
        score += 3
    basename = os.path.splitext(os.path.basename(path))[0]

    def toks(s):
        out = set(re.findall(r"[a-z0-9]{4,}", s.lower())) - STOP
        out = {x for x in out if not re.match(r"^(20\d\d|ktp\d*|spv\d*)$", x)}
        return out | {stem(x) for x in out}

    # Curated tokens (alias, hand-written trigger, filename) carry the signal.
    # Mined keywords are noisy, so they may only reinforce a curated hit, never create
    # one on their own. Without this an unrelated page matches on a single stray word.
    curated = toks(alias + " " + note + " " + basename)
    mined = toks(kw) - curated
    hit_curated = curated & prompt_words
    hit_mined = mined & prompt_words
    if not hit_curated and score == 0:
        continue
    score += len(hit_curated) + 0.5 * len(hit_mined)
    if score >= 2:
        prev = scored.get(path)
        if not prev or score > prev[0]:
            scored[path] = (score, alias, note)

if not scored:
    sys.exit(0)

top = sorted(scored.items(), key=lambda kv: -kv[1][0])[:5]

try:
    with open(state, "a") as f:
        for path, _ in top:
            f.write(path + "\n")
except Exception:
    pass

print("📚 BIBLIOTHÈQUE RECALL — the library has entries matching this prompt's topic:")
for path, (score, alias, note) in top:
    note_s = f" — {note}" if note else ""
    print(f"  - [[{alias}]] → ~/{os.path.relpath(path, home)}{note_s}")
print()
print("Before investigating, declaring any mechanism unknown/UNVERIFIED, or dispatching a")
print("discovery probe: read the relevant entries above (or dispatch bibliotheque-librarian in")
print('query mode). If they do not answer the question, note "library silent" and proceed.')
sys.exit(0)
PYEOF
exit 0

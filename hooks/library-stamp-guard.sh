#!/usr/bin/env bash
# Library-Stamp Guard — PreToolUse hook for Agent|Task dispatch (KTP-939 F19 Layer B).
#
# Retrieval-at-dispatch: a subagent sent to investigate how an org system works cannot consult
# the bibliothèque it was never told about, so it re-derives documented knowledge from primary
# sources (F19: an expensive probe rediscovered a mechanism documented in 5+ library docs,
# including the exact BQ Data Transfer config ID). This guard blocks investigation-shaped
# dispatches that carry no library stamp, and tells the orchestrator how to fix the dispatch:
# check the library, then attach what it says — or an explicit "Library: silent" line.
#
# Block condition (exit 2 = block, stderr shown to agent):
#   cwd is inside an org root that has a bibliothèque, AND
#   the subagent prompt is investigation-shaped (verb + system-noun), AND
#   the prompt contains no library stamp / library context, AND
#   the dispatch is not itself the librarian.
# Otherwise exit 0 (allow). Defense-in-depth; the prose rule is the primary discipline.

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

ti = d.get("tool_input", {}) or {}
prompt = (ti.get("prompt") or "") + " " + (ti.get("description") or "")
subagent = (ti.get("subagent_type") or "").lower()
cwd = d.get("cwd", "") or os.getcwd()

if not prompt.strip():
    sys.exit(0)

home = os.path.expanduser("~")
biblio = None
for root in ("Developer/grp-beklever-com", "Developer/supervisr-ai"):
    full = os.path.join(home, root)
    if cwd.startswith(full):
        cand = os.path.join(full, "project-management/documentation/bibliotheque")
        if os.path.isdir(cand):
            biblio = cand
        break
if not biblio:
    sys.exit(0)

# The librarian IS the library check; never block it.
if "librarian" in subagent or re.search(r"bibliot|librarian", prompt, re.I):
    sys.exit(0)

# Already stamped or already carrying library context.
if re.search(r"\blibrary\s*:|\blibrary silent\b|library checked", prompt, re.I):
    sys.exit(0)

VERB = re.compile(
    r"investigat|autopsy|diagnos|\btrace\b|\bprobe\b|discover|figure out|find out|map out"
    r"|how (does|do|is|are) \w+.{0,40}(work|ingest|load|flow|deploy|populate|sync|get)"
    r"|where (does|do) .{0,40}come from|what (feeds|populates|writes to)|topology|unverified",
    re.I,
)
NOUN = re.compile(
    r"pipeline|ingest|mechanism|dataset|schema|dataform|terraform|\bdac\b|infra|cloud run"
    r"|bigquery|\bbq\b|backend|deploy|endpoint|service|config|\bdns\b|bucket|scheduled"
    r"|data transfer|google sheet|environment|\benv\b",
    re.I,
)
if not (VERB.search(prompt) and NOUN.search(prompt)):
    sys.exit(0)

rel = os.path.relpath(biblio, home)
sys.stderr.write(f"""🛑 LIBRARY-STAMP GUARD — this dispatch is an investigation mission with no library stamp.

The bibliothèque may already document what this subagent is being sent to discover
(KTP-939 F19: a probe re-derived a mechanism already documented in 5+ library docs).
A subagent cannot consult a library it was never told about.

Fix, then re-dispatch:
1. Check ~/{rel}/INDEX.md + ALIASES.md for the mission's topic
   (or dispatch bibliotheque-librarian in query mode first).
2. Add ONE line to the subagent prompt:
   Library: <doc paths + what they establish>        (when the library speaks)
   Library: silent (checked INDEX/ALIASES for <topic>)  (when it does not)
Findings the library already establishes are context to hand over, not questions to re-probe.
""")
sys.exit(2)
PYEOF
exit $?

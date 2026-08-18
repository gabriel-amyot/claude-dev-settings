#!/usr/bin/env bash
# Recompute every number quoted in the harness deck.
# The deck hardcodes counts that go stale. Run this before re-presenting,
# then update slide 2 (the layer table) and slide 4's "676 indexed pages".
set -uo pipefail

PM="${PM:-$HOME/Developer/grp-beklever-com/project-management}"
CFG="${CFG:-$HOME/.claude}"

printf '%-24s %s\n' "LIBRARY docs"    "$(find "$PM/documentation/bibliotheque" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
MEM="$CFG/projects/-Users-gabrielamyot-Developer-grp-beklever-com-project-management/memory"
printf '%-24s %s\n' "LIBRARY rules"   "$(ls -1 "$MEM"/*.md 2>/dev/null | wc -l | tr -d ' ')"
printf '%-24s %s\n' "CREW agents"     "$(ls -1 "$CFG"/agents/*.md 2>/dev/null | wc -l | tr -d ' ')"
printf '%-24s %s\n' "LINES skills"    "$(ls -1 "$CFG"/skills 2>/dev/null | wc -l | tr -d ' ')"
printf '%-24s %s\n' "RAILS guardrails" "$(ls -1 "$CFG"/hooks/*.sh 2>/dev/null | wc -l | tr -d ' ')"
printf '%-24s %s\n' "WORK tickets"    "$(find "$PM/tickets" -maxdepth 3 -type d -name 'KTP-*' 2>/dev/null | wc -l | tr -d ' ')"
printf '%-24s %s\n' "sessions archived" "$(ls -1 "$PM/sessions/archive/done" 2>/dev/null | wc -l | tr -d ' ')"

echo
echo "Graph payload (slide 2, click LIBRARY):"
python3 - "$PM" <<'PY'
import json,sys,os
p=os.path.join(sys.argv[1],'documentation/bibliotheque/GRAPH_DATA.json')
try:
    d=json.load(open(p))
    print("  mapped pages: %d | links: %d" % (len(d['nodes']),len(d['links'])))
    print("  regenerate with: /bibliotheque-librarian graph")
except Exception as e:
    print("  could not read GRAPH_DATA.json:",e)
PY

cat <<'EOF'

To refresh the embedded graph in the deck:
  1. /bibliotheque-librarian graph        (regenerates GRAPH_DATA.json)
  2. Re-run the build in README.md §Rebuild — it strips labels and
     inlines the image so the deck stays self-contained and safe to share.
EOF

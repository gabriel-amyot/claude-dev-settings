#!/bin/bash
# PreToolUse Bash guard: audience gate on Jira ticket CREATION.
#
# Jira is the board colleagues read. Internal decisions, open questions, pivots and
# inbox items belong on GitHub Issues (gabriel-amyot/klever-project-management), not
# on the shared board. This guard makes that classification an explicit, auditable
# token on the command instead of an invisible judgement.
#
# Scope: `jira_skill.py create` ONLY. Comments, transitions and updates are already
# covered by JIRA_AGENT_RULES Rule 0 and the /post-comment pipeline; widening this
# guard to them would duplicate an existing gate and train reflex approval.
#
# Contract: a `create` must carry --audience team (or --audience=team). Anything else
# is blocked: absent means the classification was never made, `internal` means the
# item belongs on GitHub. The flag is stripped by jira_skill.py the same way --org is,
# so it never reaches the Jira API.
#
# Enforcement scope: Bash TOOL guard. A create issued through some other tool path is
# not seen and is NOT thereby approved.
#
# Kill-switch (either disables the guard):
#   export JIRA_AUDIENCE_GATE_OFF=1
#   touch /Users/gabrielamyot/.claude/.jira-audience-gate-off
# FAILS OPEN on any internal error — never wedge every session because the guard broke.

SENTINEL="/Users/gabrielamyot/.claude/.jira-audience-gate-off"
[ -n "$JIRA_AUDIENCE_GATE_OFF" ] && exit 0
[ -f "$SENTINEL" ] && exit 0

input="$(cat)"

# Decide in python (shlex tokenising mirrors jira_skill.py's own argv parsing).
# Prints "BLOCK_MISSING", "BLOCK_INTERNAL <value>", or nothing.
decision="$(printf '%s' "$input" | python3 -c '
import sys, json, shlex

try:
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if "jira_skill.py" not in cmd:
        sys.exit(0)

    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = cmd.split()

    # Locate every jira_skill.py invocation; a chained command may hold more than one.
    idxs = [i for i, t in enumerate(toks) if t.endswith("jira_skill.py")]
    if not idxs:
        sys.exit(0)

    for start in idxs:
        rest = toks[start + 1:]

        # Mirror jira_skill.py: --org and its value plus --skip-disclaimer are stripped
        # before `command = sys.argv[1]`, so skip them to find the real subcommand.
        sub = None
        i = 0
        while i < len(rest):
            t = rest[i]
            if t == "--org":
                i += 2
                continue
            if t == "--skip-disclaimer" or t.startswith("--org="):
                i += 1
                continue
            if t.startswith("-"):
                i += 1
                continue
            sub = t
            break
        if sub != "create":
            continue

        # Read --audience for THIS invocation only (stop at a shell operator).
        audience = None
        i = 0
        while i < len(rest):
            t = rest[i]
            if t in ("&&", "||", ";", "|"):
                break
            if t == "--audience" and i + 1 < len(rest):
                audience = rest[i + 1]
                break
            if t.startswith("--audience="):
                audience = t.split("=", 1)[1]
                break
            i += 1

        if audience is None:
            print("BLOCK_MISSING")
            sys.exit(0)
        if audience.strip().lower() != "team":
            print("BLOCK_INTERNAL " + audience.strip())
            sys.exit(0)

except Exception:
    sys.exit(0)  # fail open
' 2>/dev/null)"

[ -z "$decision" ] && exit 0

case "$decision" in
  BLOCK_INTERNAL*)
    got="${decision#BLOCK_INTERNAL }"
    cat >&2 <<MSG
Blocked: --audience "$got" is not a team-facing audience, so this does not go on the Jira board.

Internal work goes to GitHub Issues instead:

  gh issue create --repo gabriel-amyot/klever-project-management \\
    --title "<the question or decision>" --body "<detail>"

Jira is the board colleagues read. Decisions, open questions, pivots, spikes-for-yourself
and inbox items are internal; they belong on GitHub Issues where they cost no one else
attention. Only --audience team reaches Jira.
MSG
    exit 2
    ;;
  BLOCK_MISSING*)
    cat >&2 <<'MSG'
Blocked: a Jira `create` needs an explicit audience decision. It was never made.

Apply the audience test — WILL A COLLEAGUE NEED TO SEE THIS?

  NO  -> internal. File it on GitHub Issues, do NOT create a Jira ticket:
         gh issue create --repo gabriel-amyot/klever-project-management \
           --title "<the question or decision>" --body "<detail>"
         Covers: decisions, open questions, pivots, your own task decomposition,
         reading and approval items. Wayfinder decision tickets ALWAYS land here.

  YES -> team-facing delivery work. Re-run the create with the decision recorded:
         jira_skill.py --org klever create ... --audience team

  UNSURE -> ask Gabriel which board this belongs on. Do not guess, and do not
         default to Jira because Jira is habitual. GitHub is the default.

Explicit Jira intent looks like: "create a jira ticket for X", "break KTP-1234 into
smaller jira tickets", "file a bug on the board". Absent that, assume internal.

Rules: ~/.claude-shared-config/skills/jira/JIRA_AGENT_RULES.md (Rule 7)
Emergency disable (if this guard is wrong): touch ~/.claude/.jira-audience-gate-off
MSG
    exit 2
    ;;
  *)
    exit 0
    ;;
esac

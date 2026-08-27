#!/usr/bin/env python3
"""Hit-rate eval for bibliotheque-recall.sh.

The recall hook is the retrieval layer that replaced the On-Demand Context table in
CLAUDE.md. That table was a guaranteed lookup; the hook is best-effort. This measures
how good "best effort" actually is, so tuning is driven by a number rather than by
whichever prompt was tried last.

Each case is a realistic prompt plus the alias that SHOULD surface. Reported:
  HIT@1  expected alias is the top pointer
  HIT@5  expected alias appears at all (the hook emits at most 5)
  MISS   nothing relevant surfaced

Usage:
  recall-eval.py                # run all cases
  recall-eval.py --verbose      # show what surfaced for every case
"""
import re
import subprocess
import sys
import json
from pathlib import Path

HOOK = Path.home() / ".claude/hooks/bibliotheque-recall.sh"
KLEVER = str(Path.home() / "Developer/grp-beklever-com/project-management")

# (prompt, expected alias, cwd)
CASES = [
    # --- global library ---
    ("I need to wire a new bigquery adapter, how do I confirm column names and nullability", "schema-validation-gate", KLEVER),
    ("the shell prints startup errors twice, dotfiles seem to run twice", "zsh-dotfiles-double-sourcing-gotcha", "/tmp"),
    ("designing a side-effecting CLI that an agent will drive, what safety patterns apply", "llm-tool-design-safety-patterns", "/tmp"),
    ("claude code crashed and I lost a session, can I recover the transcript", "claude-code-session-crash-forensics", "/tmp"),
    ("merge request checklist before shipping to prod", "shipping-workflow", KLEVER),
    ("what is the java testing standard here, mockito strict stubs", "java-standards", KLEVER),
    ("I want to run a long job that outlives the tool timeout", "long-running-process-pattern", "/tmp"),
    ("writing a jira comment with the jira skill, what are the gotchas", "jira-skill-gotchas", KLEVER),
    ("which branch actually deploys, is this the deployed code", "deploy-identity-gate", KLEVER),
    ("starting an overnight unattended crawl, what rules apply", "autonomous-crawl-rules", KLEVER),
    ("my script will delete datastore entities, what do I do first", "data-mutation-safety", KLEVER),
    ("cloud run returns 403, how do I diagnose the IAM problem", "cloud-run-iam-diagnosis", KLEVER),
    ("how do I create a git worktree without the gitconfig lock error", "worktree-fleet-ops", KLEVER),
    ("writing an ADR, where do docs go", "documentation-standards-quick-ref", KLEVER),
    ("the context window is filling up, how should I manage a long agent run", "context-engineering", "/tmp"),
    ("scoping an mcp server to one project only", "mcp-server-scoping-and-isolation", "/tmp"),
    ("applescript keystroke injection into ghostty", "macos-terminal-automation-gotchas", "/tmp"),
    ("nextjs static export 404 on cloudflare pages, works locally", "nextjs-cloudflare-static-export", "/tmp"),
    # --- org library, incl. the pages Phase 3 now cites ---
    ("can I push this DAC change straight to uat", "dac-workflow", KLEVER),
    ("the CI pipeline failed with the same registry error three times, retry again?", "ci-cd-patterns", KLEVER),
    ("git clean wiped my untracked subagent files", "session-file-wipe", KLEVER),
    ("granting a new klever user access to bigquery", "klever-grant-user-resource-access", KLEVER),
    ("dev is returning 000, is the environment down", "dev-environment-nightly-schedule", KLEVER),
    ("I am creating a liquibase changeset", "liquibase-safety-rules", KLEVER),
]


def clear_state():
    """The hook fires each pointer at most once per session, tracked in /tmp. Reusing a
    session id across runs suppresses every pointer after the first run and makes the
    eval report a false 0%. Always start from clean state."""
    import glob, os
    for f in glob.glob("/tmp/bibliotheque-recall-eval*"):
        try:
            os.remove(f)
        except OSError:
            pass


def run(prompt, cwd, sid):
    payload = json.dumps({"prompt": prompt, "cwd": cwd, "session_id": sid})
    r = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True)
    return re.findall(r"\[\[([^\]]+)\]\]", r.stdout)


def main() -> int:
    verbose = "--verbose" in sys.argv
    clear_state()
    h1 = h5 = miss = 0
    misses = []
    for i, (prompt, expected, cwd) in enumerate(CASES):
        got = run(prompt, cwd, f"eval{i}")
        if got and got[0] == expected:
            h1 += 1; h5 += 1; mark = "HIT@1"
        elif expected in got:
            h5 += 1; mark = f"HIT@{got.index(expected)+1}"
        else:
            miss += 1; mark = "MISS "
            misses.append((prompt, expected, got))
        if verbose or mark.startswith("MISS"):
            print(f"{mark}  want={expected}")
            print(f"       {prompt[:78]}")
            if got:
                print(f"       got: {', '.join(got[:5])}")
            else:
                print("       got: (nothing)")
    n = len(CASES)
    print(f"\n{n} cases   HIT@1 {h1} ({h1/n*100:.0f}%)   HIT@5 {h5} ({h5/n*100:.0f}%)   MISS {miss}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

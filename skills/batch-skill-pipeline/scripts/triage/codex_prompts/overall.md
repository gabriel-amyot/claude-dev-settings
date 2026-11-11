You are a hostile reviewer of a whole triage. Do NOT load or follow any skill files. Answer directly. Read-only.

Context: a Claude Code harness has a fixed skill budget (installed count and drift alarm in __RUN__/brief.md). The pending skill proposals listed in __RUN__/inventory.tsv were reviewed:
- First pass (Claude), per proposal: __RUN__/results/*.json
- Second pass (Codex), per proposal: __RUN__/codex/out-batch-*.json
- Codex review of the topic clusters: __RUN__/codex/out-groups.json
- Rubric: __RUN__/brief.md

Assess the triage as a whole:
1. Systemic bias: is the first pass too harsh or too lenient overall (for example near-zero BUILD verdicts)? Is "fold into an existing skill" used to dodge the slot budget while it bloats a few skills? Name the skills that receive too many UPDATEs and what that does to their size and trigger clarity.
2. Verdict conflicts between passes: list the proposals where the two passes disagree most, and say which side is right and why (CONFIRMED by checking a file, or PLAUSIBLE).
3. Evidence quality: were recurrence counts systematically inflated or deflated? Name the method flaw.
4. Top 15 actions: your own ranked list of the 15 actions most worth taking now (verdict plus a one-line reason). Group UPDATEs to the same skill into one action where sensible.
5. Archive list: the proposals that are safe to archive now, with no regret.
6. Invocation: any proposal where both passes chose the wrong invocation mode.

Output plain Markdown, max 900 words, with these `##` sections in this order: Verdict on the triage, Bias, Conflicts, Evidence method, Top 15 actions, Safe to archive, Invocation corrections. Use a numbered list for Top 15 actions. End with one line: `OVERALL: SOUND` or `OVERALL: NEEDS REWORK` plus a reason.

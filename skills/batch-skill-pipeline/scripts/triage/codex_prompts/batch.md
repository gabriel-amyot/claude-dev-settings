You are a hostile second-pass reviewer. Do NOT load or follow any skill files. Answer directly. Read-only: do not modify any file.

Context: a Claude Code harness has a fixed skill budget (the installed count and the drift alarm are in the brief). A new skill must displace one or fold into an existing one. A first-pass reviewer (Claude) reviewed a batch of pending skill proposals. Your job is to attack the first pass, proposal by proposal.

Inputs (absolute paths):
- Review brief, scoring rubric, knowledge libraries and transcript directories: __RUN__/brief.md
- First-pass results for this batch: __RUN__/results/__BATCH__.json
- Proposal files: the proposals directory named in the brief, plus <file> (file names are in the JSON)
- Installed skills: ~/.claude/skills/*/SKILL.md and ~/.claude/plugins/local-marketplace/*/skills/*/SKILL.md (read frontmatter only)
- Run state (start date of this triage): __RUN__/STATE.json

Known noise in recurrence counts: transcripts dated on or after the run start date (this triage session matches every proposal name); later skill-audit sessions that quote proposal text; SOP excerpts recalled into context that echo keywords. None of these is a real recurrence. Discount them.

For EACH proposal in the first-pass JSON:
1. Read the proposal file.
2. Check the first-pass verdict, score, overlap claims, evidence counts, eval ease and invocation mode.
3. Spot-check at least one evidence or overlap claim per proposal against files. Label each finding CONFIRMED (you checked a file) or PLAUSIBLE (reasoned).
4. Look specifically for: an existing skill that already covers it but was missed; inflated recurrence counts (keyword matches that are not real recurrences, or matches inside the origin session only); a wrong invocation mode (auto on an expensive or outward-facing action, or manual on a crisp, costly-to-miss trigger); an ARCHIVE that should survive; a BUILD that should be an UPDATE or SOP; an UPDATE that would bloat its target skill.

Output: ONLY a JSON array (no prose, no code fence), one object per proposal:
{"file": "...", "agree": true|false, "codex_verdict": "BUILD | UPDATE:<skill> | MERGE:<proposal> | SOP | ARCHIVE", "codex_score": 0-100, "codex_invocation": "manual|auto", "findings": [{"label": "CONFIRMED|PLAUSIBLE", "text": "1-2 sentences"}], "summary": "one sentence"}

You are a hostile reviewer. Do NOT load or follow any skill files. Answer directly. Read-only.

Context: pending skill proposals are listed in __RUN__/inventory.tsv (the proposals directory is named in __RUN__/brief.md). The harness has a fixed skill budget (see the brief). A first-pass reviewer clustered the proposals into named groups by reading only each proposal's trigger line. Anything unlisted is "Ungrouped". The clusters are in __RUN__/groups.json. The intent of clustering: decide related proposals together (merge them, fold them into an existing skill, or archive them as a set).

Installed skills: ~/.claude/skills/*/SKILL.md and ~/.claude/plugins/local-marketplace/*/skills/*/SKILL.md (frontmatter only).

Tasks:
1. Read every proposal file (they are short).
2. For each group, judge whether each member belongs. Flag misattributions with the group it should be in.
3. Find ungrouped proposals that clearly belong in an existing group, or that form a new coherent cluster of 3 or more. Propose new clusters with a name.
4. For any group whose name says it may already be covered: for each member, name the installed skill that covers it, or say NOT_COVERED (CONFIRMED by reading the skill frontmatter, or PLAUSIBLE).
5. For every group with 4 or more members: propose the merged design in one or two sentences (what single skill or existing-skill update would absorb the group), or say the group should not merge and why.

Output ONLY a JSON object (no prose, no code fence):
{"misattributions": [{"proposal": "name", "from": "group", "to": "group or new cluster name", "why": "1 sentence"}],
 "new_clusters": [{"name": "...", "members": ["..."], "why": "1 sentence"}],
 "coverage": [{"proposal": "...", "covered_by": "skill name or NOT_COVERED", "label": "CONFIRMED|PLAUSIBLE"}],
 "merge_designs": [{"group": "...", "design": "1-2 sentences", "merge": true|false}],
 "summary": "3 sentences max"}

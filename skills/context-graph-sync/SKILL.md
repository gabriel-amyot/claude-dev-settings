---
name: context-graph-sync
description: "Connect Gabriel's private bibliothèque to Alpha's team Klever Context Graph (app-global-context-graph). Modes: status (freshness, STALE banner, drift, open promotions), down (downward sync: ff-only pull of the team graph clone, rebuild cards/index/drift, confirm merged promotions), view (local merged 3D viewer: team graph + private overlay), overlay (validate / add / commit private facts in graph shape), migrate (one-time gated migrations: scaffold, aliases, surfaces, pages, librarian), up (upward push: one team-shareable fact at a time, re-derived from code, scanned, previewed, human-approved, merged by Alpha). Klever only. Triggers: 'sync the context graph', 'pull the graph', 'context graph status', 'push this to the context graph', 'promote to the team graph', 'show my graph', 'context-graph-sync'."
user_invocable: true
nav:
  bay: know
  when: "Pull the team Context Graph into the bibliothèque view, look at the merged map, record private graph facts, or push one non-private fact upward."
  when_not: "Querying the team graph only (use klever-context-graph ask mode). Curating prose pages (use /bibliotheque-librarian). Tagging pages private/team (visibility.py, separate job)."
---

# context-graph-sync

Two directions, two different trust levels:

| Direction | What | Trust | Human |
|---|---|---|---|
| **Down** (team → me) | `git pull --ff-only` of the team clone, then rebuild derived cards / index / drift | Automatic and safe: the clone is read-only, Alpha's `main` only moves through merged MRs | Only when it fails |
| **Up** (me → team) | One fact, re-derived from code, scanned, previewed, pushed as a graph MR | Strict | Gabriel approves the exact preview; Alpha merges |

Design and rationale: `~/Developer/grp-beklever-com/project-management/general/initiatives/klever-context-merge/`
(`plan-v1-simple.html` for the picture, `DESIGN.md` §0 for "re-derive, never project").

## Setup (once)

```bash
CG="python3 ~/Developer/grp-beklever-com/project-management/tools/bibliotheque/context_graph/cg.py"
export KLEVER_CONTEXT_GRAPH_DIR=~/Developer/grp-beklever-com/grp-faas/grp-app/grp-global/app-global-context-graph
npm --prefix "$KLEVER_CONTEXT_GRAPH_DIR" install --no-package-lock   # never rewrite Alpha's lockfile
```

Never `cd` in Bash (the shell's cd override hangs). Always call `$CG` with absolute paths.

## Hard rules

1. **Never edit the team clone.** It stays on `main`, clean, read-only. `down` refuses a dirty or diverged clone. If it refuses, report it. Do not "fix" it by resetting.
2. **Down is dry-run unless `--apply`.** Sync is manual (Gabriel's choice): run `down`, show the summary, then `down --apply` when asked.
3. **Overlay writes go through `overlay add`** (locked, validated, atomic). Never Write/Edit atom files directly. Commit only with `overlay commit` (pathspec-only, refuses foreign staged files).
4. **Migrations are plan → read → apply.** Run `migrate <step>`, give Gabriel the report path, and apply only with `--approve <hash>` from that report after he says yes. A changed state changes the hash. Then re-plan.
5. **Up never copies private text.** The atom is a trigger. The team patch is written fresh from code at a pinned commit, by a subagent that sees only that code and the team graph (step U3 below).
6. **No push without a matching approval hash**, no rebase, no force-push, no `klever-context-graph` `contribute` mode (it rebases + force-pushes). Conflicts: `up update` merges `origin/main`.
7. **Graph describes prod.** Dev-only facts stay in the overlay (`meta.env: dev`). An MR for something not in prod says `In prod: no` and Alpha holds it.

## Mode: status

```bash
$CG status
```
Prints `✓ team graph @ <sha>, pulled Nh ago` or `⚠ STALE TEAM GRAPH …` (never pulled, >48h, or last pull failed), overlay validity, dangling references, open promotions. Exit 1 when stale or invalid. Print the banner verbatim to Gabriel. Never hide it.

## Mode: down (downward sync)

```bash
$CG down            # dry-run: fetch, show incoming commits, derived-views summary, promotions to confirm
$CG down --apply    # ff-only merge, rebuild context-graph/{cards,graph-index.yaml,drift-report.md}, confirm promotions
```
After `--apply`, read `documentation/bibliotheque/context-graph/drift-report.md`. A dangling id means a rename or removal upstream: list it for Gabriel, never delete the reference silently.
Fetch fails (IAP token, GitLab down, nightly Datasophia window): report it. Freshness records the failure and `status` shows STALE. Do not retry in a loop.

## Mode: view

```bash
$CG view                 # team graph + private overlay into ~/.cache/context-graph-sync/view
$CG view --team-only     # what a teammate sees
$CG view --build         # also prove the merged data builds
npm --prefix ~/.cache/context-graph-sync/view run dev     # http://localhost:5173 (run_in_background)
```
Private nodes show with a 🔒 label, private types, and a `private` domain. The view is never committed or pushed.

## Mode: overlay

Atom shape: `documentation/bibliotheque/context-graph/overlay/SCHEMA.private.md`. Draft the atom JSON in `/tmp`, then:
```bash
$CG overlay add /tmp/edge-<slug>.json     # refused with reasons if invalid or dangling
$CG overlay validate
$CG overlay commit -m "knowledge: overlay <what>"   # only when Gabriel asks to commit
```
`meta.visibility` defaults to `unclassified` (= private). Set `team` only when Gabriel says so for that atom.

## Mode: migrate (one-time, gated)

Order: `scaffold` → `down --apply` (builds cards) → `aliases` → `surfaces`. `pages` and `librarian` are report-only.

```bash
$CG migrate scaffold                         # report in /tmp/context-graph-sync/migrate-scaffold.md + hash
$CG migrate scaffold --apply --approve <hash>
```
| Step | Writes | Notes |
|---|---|---|
| scaffold | `context-graph/` folder (INDEX, .gitignore, overlay schema), one section in root `INDEX.md` | Derived files are gitignored. |
| aliases | One managed block at the end of `ALIASES.md` (team ids → cards) | Blocked until cards exist. Re-run replaces the block. Report includes a recall-noise estimate. |
| surfaces | `graph_id:` line under each uniquely matched `- id:` in `surfaces/*.yaml` | Ambiguous and unmatched surfaces are listed and left alone. |
| pages | nothing | Candidate ids per page. Pages adopt `graph: [ids]` gradually, never a mass edit. |
| librarian | nothing | Proposed text for the librarian query mode. Gabriel edits the agent file. |

Show Gabriel the report (open it or summarize the table). Apply only after an explicit yes.

## Mode: up (upward push, strict)

| Step | Who | Command / action |
|---|---|---|
| U1 | Gabriel | Marks the atom(s) `meta.visibility: team` (via `overlay add` of the edited atom). |
| U2 | agent | `$CG up new --atoms edge-x[,gap-y] --slug <system-fact-slug>` refuses non-team, private types, private-only, and private terms in the slug. |
| U3 | **fresh subagent** | Re-derive the patch. Dispatch a `general-purpose` agent whose prompt holds ONLY: the evidence repo path(s) and commit, the team node ids involved, and the team ontology rules. It must NOT receive the atom notes, page text, or session context. It reads the code at the pinned commit (`git -C <repo> show <sha>:<path>`) and writes `/tmp/promo-N.patch.json`: `{"edges":[…], "gaps":["TRAP: …"], "node_updates":[{"id":…, "set":{"x":…}}]}` with `confidence`, `verified`, `evidence: "<repo>:<path>"`. Existing team ids only. |
| U4 | agent | `$CG up stage --promotion N --patch /tmp/promo-N.patch.json --evidence <repo>:<path>@<sha> --title "graph: <what>" --in-prod no\|unproven\|"yes since <tag>"`: staging clone outside project-management, apply, team `npm run validate`, commit, smoke scan of patch + branch + commit + author + MR fields + push options. A hit means no preview. Fix the patch, or `--allow-term X --restage` for a reviewed false positive. |
| U5 | Gabriel | Reads the preview file (`~/.cache/context-graph-sync/staging/NNN-slug.preview.md`). Offer `/crit:crit` on it. It is exactly what GitLab will see. |
| U6 | agent | Only after an explicit yes: `$CG up push --promotion N --approve <hash>`. Refuses if anything changed since the preview. Creates the MR. Report the MR as a clickable link. |
| U7 | agent | Later: `$CG up mark --promotion N --state merged --merge-commit <sha>` (or `rejected --reason`, `withdrawn`, `superseded --by`). The next `down --apply` confirms and archives the private atom. |
| — | agent | Main moved, or a conflict: `$CG up update --promotion N` merges `origin/main`, re-validates, and re-previews. Approve again, then push. |

The MR description is three lines (Alpha's convention): `Source`, `In prod`, `Changed`. Ticket keys, people, clients, money, local paths, session slugs and harness names never appear. The scan enforces it as a backstop.

## Tests

```bash
python3 -m unittest discover -s ~/Developer/grp-beklever-com/project-management/tools/bibliotheque/tests -p "test_context_graph.py"
```

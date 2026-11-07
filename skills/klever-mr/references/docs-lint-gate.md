# klever-mr Gate 6: Docs lint (only when the MR changes markdown)

Skip condition: `git diff --name-only origin/dev..HEAD` contains no `.md` files. Report "Gate skipped: docs lint (no markdown changed)."

Markdown defects do not fail CI, so they land in `main` and are found by a reader weeks later. Two classes are invisible in a local preview and appear only in GitLab's web view:

- **Mermaid.** GitLab renders **9.1.1**. Any newer diagram syntax (`timeline`, `mindmap`, `block-beta`, `quadrantChart`, `sankey`, `xychart-beta`, `@{shape:}`, frontmatter `config:`) parses fine locally and on GitHub, then shows **"Syntax error in graph"** on GitLab.
- **Navigation.** GitLab renders a folder's `README.md` under its file listing and **ignores `INDEX.md`**. A folder with no README shows bare filenames. Repo-escaping `../../` links resolve on one developer's disk and never in a web view.

Run the linter against a clean export, not the working tree:

```bash
git -C <repo> archive HEAD | tar -x -C /tmp/docs-lint-$$ \
  && python3 ~/Developer/grp-beklever-com/project-management/tools/docs-repo-lint.py /tmp/docs-lint-$$
```

| Finding | Action |
|---|---|
| MERMAID too new | **Blocking.** Rewrite the diagram in 9.1.1 syntax (`flowchart`/`graph`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `erDiagram`, `gantt`, `pie` are all safe). |
| BROKEN relative links | **Blocking.** A dead link in merged docs is a defect. |
| REPO-ESCAPING links | **Blocking.** These can never resolve in the web view. |
| FOLDERS with no README | Report and offer to add one. Not blocking on its own. |
| MISSING frontmatter, ORPHANS | Informational. Report the count only. |

Report findings against the files **this MR touches** first. Pre-existing defects elsewhere in the repo are not this MR's job. List them separately and do not block on them.

# Jira Skill Gotchas

On-demand context: load when running `~/.claude/skills/jira/jira_skill.py` (directly, via subagent, or via the `jira` plugin skill).

## Org slug detection

Always pass `--org {slug}` when running `jira_skill.py` from outside the org path (main context when cwd doesn't match an org root, or any subagent that `cd`s into the skill directory).

**Valid org slugs** (as of 2026-04-13):
- `klever` — Klever Tech Platform (beklever.atlassian.net, cwd `/Users/gabrielamyot/Developer/grp-beklever-com`)
- `supervisrai` — Supervisr.AI (origin8cares.atlassian.net, cwd `/Users/gabrielamyot/Developer/supervisr-ai`)

**Invalid slugs that will error with "Available: klever, supervisrai":**
- `supervisr`
- `supervisr-ai`
- `supervisr.ai`
- `klever-ai`

Subagents `cd` to the skill directory (`~/.claude/skills/jira/`), which is outside every org auto-detection path. Without the flag, queries silently hit the wrong Jira instance or default org. Always pass it explicitly.

Verify the current slug list by running `~/.claude-shared-config/skills/jira/jira_config_setup.py list`.

## `search` command: JQL is positional

The `search` subcommand takes JQL as a positional argument, NOT with a `--jql` flag. The `--jql` text gets parsed as part of the query string and causes a Jira 400 error.

```bash
# WRONG — causes 400 "Expecting operator before the end of the query"
python3 jira_skill.py search --org supervisrai --jql "assignee = currentUser()"

# RIGHT
python3 jira_skill.py search --org supervisrai "assignee = currentUser()"
```

Learned from: 2026-05-03 ticket inventory session.

## Subcommand names

Always check `~/.claude/skills/jira/SKILL.md` for the exact subcommand name before guessing. Running an unknown subcommand errors with `{"error": "Unknown command: X"}`.

**Commonly-mistaken subcommand names:**
| Wrong | Right |
|-------|-------|
| `get-issue KEY` | `get KEY` |
| `comment KEY ...` | `add-comment KEY --comment "BODY"` |
| `add-comment KEY --body "X"` | `add-comment KEY --comment "X"` (flag is `--comment`, not `--body`) |
| `edit-issue KEY --description` | `update KEY --description "X"` |
| `status KEY NEW_STATUS` | `transition KEY STATUS` |
| `close KEY` | `transition KEY "Done"` (and only after evidence-backed closing comment) |

The skill does not support `--help` as an argument. Read `SKILL.md` for the full command list.

## `update` command reference

The `update` subcommand modifies ticket fields. Flags:
- `--description "text"` — replace description
- `--summary "text"` — replace title
- `--assignee "accountId"` — reassign. **Must be the raw accountId string**, NOT a display name. The skill does not auto-resolve names for `update`. See "assignee accountId lookup" below.
- `--labels "label1,label2"` — comma-separated
- `--estimate "value"` — set story points
- `--force` — bypass ownership gate (required when ticket was reported by someone else)

**`--parent` does NOT work (KTP project).** Passing `--parent "KTP-559"` returns `{"error": "No fields to update..."}` — the flag is a no-op for KTP (company-managed). To set the parent epic use the Jira REST API directly:
```bash
TOKEN=$(security find-generic-password -s "claude-jira" -a "jira_klever" -w)
curl -s -u "gamyot@beklever.com:$TOKEN" \
  -X PUT "https://beklever.atlassian.net/rest/api/3/issue/{KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fields":{"parent":{"key":"KTP-559"}}}'
# → HTTP 204
```
(Stale flag removed from docs 2026-06-02 based on lucid-badger session findings. Full REST workaround in `stack/jira-sprint-wiring-atlassian-mcp.md`.)

**Ownership gate:** By default, `update` blocks edits to tickets not reported by you. Error: `"BLOCKED: ticket KTP-XXX reported by {name}, not you."` Pass `--force` when Gabriel explicitly approves the edit.

## Jira wiki markup (not Markdown)

Jira comments use wiki markup, NOT Markdown. Agents drafting Jira content must use:
- `h2. Heading` (not `## Heading` or `# Heading`)
- `*bold*` (not `**bold**`)
- `_italic_` (not `*italic*`)
- `{{code}}` for inline code (not backticks)
- `{code}...{code}` for code blocks (not triple backticks)
- `[~accountid:ID]` for user mentions

Learned from: 2026-05-06 post-crawl review session (KTP-579 comment had `#` headers that needed fixing).

## Comment formatting rules

Comments carry NO visible attribution header (reversed 2026-07-08 on Gabriel's instruction, per `JIRA_AGENT_RULES.md` Rule 3). Do NOT prefix with `[automated]`, a persona name, or a model line. Comments post under Gabriel's account, in his voice; provenance is recorded in the on-disk audit log, not in the comment text.

Voice: fewest words that carry the point. Lead with the outcome or the ask, no chronological story, no filler, no em-dashes. Routine comments stay under ~120 words. A wall of text gets skipped unread, which defeats the purpose of commenting.

## Never do these without explicit user confirmation

Per `JIRA_AGENT_RULES.md`:
- Transition to Done / Closed / Won't Do (these need evidence-backed closing comments and human gate)
- Sprint add/remove (see `memory/feedback_sprint_ticket_moves.md`)
- Bulk edits across tickets
- Delete comments (use `delete-comment` only when the user explicitly asks)

## Deadline mode

Under tight deadline, skip Jira state transitions entirely and use only `add-comment` for status tracking. See `memory/feedback_skip_jira_transitions_on_deadline.md`.

---

## Direct Jira REST API: use ADF format

When posting comments via `curl` to Jira REST API v3 (bypassing `jira_skill.py`), the `body` field must use Atlassian Document Format (ADF), not a plain string. A plain string body returns HTTP 200 with empty `errorMessages` but the comment is silently malformed.

Correct format:
```json
{
  "body": {
    "version": 1,
    "type": "doc",
    "content": [
      {"type": "paragraph", "content": [{"type": "text", "text": "Your comment here"}]}
    ]
  }
}
```

Use `{"type": "text", "marks": [{"type": "strong"}]}` for bold, `[{"type": "em"}]` for italic.

---

## Issue linking (NOW SUPPORTED)

**As of 2026-05-06, the skill supports linking natively:**

```bash
# Create a link
jira_skill.py link KTP-XXX KTP-YYY --type "Relates"

# List available link types
jira_skill.py link-types
```

Available link types: Relates, Blocks, Work item split, Problem/Incident, Cloners, Duplicate.

**Fallback (raw API):** If the skill fails, use curl with keychain auth. Service = `claude-jira`, account = `jira_{org}`. Python `urllib` fails with SSL cert errors on macOS; use `curl`.

## Issue type changes (NOW SUPPORTED)

**As of 2026-05-06, the skill supports type changes:**

```bash
jira_skill.py retype KTP-XXX --type Story
```

Guards against same-type no-ops. If the Jira project doesn't allow the transition, the error message explains what went wrong.

## Hierarchy constraints (KTP project)

Company-managed KTP project enforces strict 3-level hierarchy:
- Epic → top-level only (no parent epic)
- Story/Bug/Spike → can parent under Epic only
- Sub-task → can parent under Story only

Attempting to nest Epic under Epic returns: `"Given parent work item does not belong to appropriate hierarchy."` Workaround: flat epic with label-based sub-grouping (e.g., `store-detail-panel`).

Learned from: 2026-05-06 KTP-130 epic reorganization. Confirmed with live API tests.

---

Learned from:
- 2026-03-31 sprint closure session (org slug requirement for subagents)
- 2026-04-13 SPV-92 consolidation session (add-comment vs comment, supervisrai slug, [automated] header)
- 2026-04-18 KTP-499 session (ADF format requirement for direct API calls)
- 2026-05-06 KTP-130 epic reorganization (issue linking, type changes, hierarchy constraints)
- 2026-05-06 post-crawl review session (get vs get-issue, --comment vs --body, update command, ownership gate, wiki markup)

## Story points, epic link, sprint — use the runtime skill, not the _meta fork (Learned 2026-06-08, KTP-791/792)

**Always run the canonical skill at `~/.claude/skills/jira/jira_skill.py`** (what SKILL.md prescribes). Do NOT invoke `project-management/_meta/skills/jira/jira_skill.py` — that is a stale, diverged fork (older field handling) and is read-only. Calling it, or hand-rolling `jira.issue().update()` python, is what caused the wrong-field mistakes below.

**Field IDs (Klever / beklever Jira):**
- Story points = `customfield_10028` (NOT `customfield_10016` — that's a legacy/empty field; the board reads 10028).
- Sprint = `customfield_10020`; Epic Link = `customfield_10014`.

**Use the flags, not raw field writes.** `create` and `update` now support:
- `--estimate N` (story points → 10028)
- `--epic KEY` (Epic Link → 10014; correct for company-managed projects like KTP, where `--parent` does NOT epic-link a Story)
- `--sprint SPRINT_ID` (numeric sprint id; get ids via the `sprints` command / board 248 for KTP)
- `--assignee "accountId"` — requires **raw accountId**, same as `update`. `create` does NOT auto-resolve display names. Pass the accountId directly.

Example one-shot: `create --project KTP --type Story --summary "..." --assignee "6054ad7681b825006868dcd3" --estimate 3 --epic KTP-748 --sprint 1713`

## `metadata` subcommand — full fields including labels and sprint

The slim `get` and `search` subcommands return only key/summary/status. To read labels, reporter, estimate, or sprint assignment, use the `metadata` subcommand:

```bash
python3 ~/.claude-shared-config/skills/jira/jira_skill.py --org klever metadata KTP-XXX
```

**`update --labels` REPLACES the entire label set**, it does not append. Always read the current labels via `metadata` first, then construct the full replacement list.

Field flags:
- Story points → `--estimate N` (writes to `customfield_10028`)
- Sprint → `--sprint <id>` (numeric sprint id; discover ids via `sprints --project KTP`)
- Comment body → `--comment "BODY"` (not `--file`, not `--body`)

**Source:** KTP-799 session (2026-06-10)

## Assignee accountId Lookup

Jira Cloud requires `{"assignee": {"accountId": "..."}}`. The skill's `update --assignee` passes the value as a raw string — no auto-resolution. If you pass a display name, the call fails silently or returns an error.

**To look up a user's accountId:**
```python
import keyring, json
from jira import JIRA

token = subprocess.check_output(
    ["security", "find-generic-password", "-s", "claude-jira", "-a", "jira_klever", "-w"]
).decode().strip()
j = JIRA("https://beklever.atlassian.net", basic_auth=("gamyot@beklever.com", token))
users = j.search_users("Amal")  # search by name fragment
print([(u.displayName, u.accountId) for u in users])
```

**Known accountIds (Klever):**
| Person | accountId |
|---|---|
| Amal Elena Yassin | `6054ad7681b825006868dcd3` |

Then: `j.issue("KTP-XXX").update(fields={"assignee": {"accountId": "6054ad7681b825006868dcd3"}})`

Source: vivid-ibis KTP-719/720/721 session (2026-06-10/11).

## Attachment download 403s via API token even though listing/upload work

`jira_skill.py attachments KEY` lists attachments fine, and `upload-attachment` works fine, but `download-attachment` (both `/rest/api/2/attachment/content/{id}` and `/secure/attachment/` URLs) returns HTTP 403 `"You do not have permission to view attachment"` when using the API token auth the skill uses. This is a Jira Cloud permission quirk on the *download* path specifically — the token has enough scope to list and upload, not to fetch attachment content.

**Workaround:** `open <attachment content URL>` in the user's authenticated Chrome (not `curl`/the skill). It downloads to `~/Downloads` using the browser's session cookies.

**How to apply:** When a `download-attachment` call 403s, do not assume the attachment is missing or that access is broken — list it via `attachments KEY` to get the content URL, then open that URL in Chrome for the human to save it locally.

Source: KTP-830 session (clever-otter, 2026-07-03).

## `create` may silently succeed while appearing to fail

`jira_skill.py create` can fail to parse its own output and report an error even when the ticket was created. Before retrying a create command, verify with:

```bash
jira_skill.py search --jql "parent=KTP-XXX ORDER BY created DESC" --org klever
```

If a duplicate exists, repurpose it — the skill has no delete command.

**Why:** KTP-793 and KTP-794 were both created when only one was intended (retry after a false failure). Learned from Jun 2026 session harvest.

## JQL named-sprint queries return nothing for closed sprints

After a sprint closes, `sprint = 'Q2-Sprint-X'` JQL returns zero results. Use ticket creation-window dates + cross-reference sprint membership captured before close.

**Why:** Sprint 5 post-close analysis couldn't identify injected tickets via JQL. Learned from Jun 2026 session harvest.

## `sprint-board` — active-sprint issues + owner + status + story points in ONE call

Every sprint skill (`klever-sprint-mgmt`, `klever-sprint-exit`, `sprint-dispatcher`, `klever-3ps`) needs "what's in the sprint, who owns it, what state is it in." Before, that meant dropping to the raw Agile REST API because slim `search` omits assignee and the `currentUser() AND openSprints()` JQL path is broken on Jira Cloud. Use the `sprint-board` subcommand instead:

```bash
python3 jira_skill.py sprint-board --org klever --project KTP      # discovers the board
python3 jira_skill.py sprint-board --org klever --board 248        # exact board id
python3 jira_skill.py sprint-board --org klever --project KTP --max 200
```

Returns `{board, project, activeSprint:{id,name}, count, issues:[{key, summary, status, assignee, storyPoints, epic}]}` in one call.

- **Board-id lookup:** `--project KTP` auto-discovers the board (Klever = **board 248**). Pass `--board <id>` to skip discovery. Discover other boards' sprints with `sprints --project <KEY>`.
- **How it avoids the broken path:** it resolves the active sprint via the Agile board API (`jira.sprints(board_id, state="active")`), then queries issues by explicit `sprint = <id>` — never `openSprints()`.
- **Story points** = `customfield_10028` (fallback `customfield_10016`); read via `getattr` because `search_issues` returns a restricted field set. **Default cap is 100 issues** — raise with `--max` for a large sprint.
- Canonical skill only (`~/.claude/skills/jira/jira_skill.py`); the `_meta` fork does not have this command. Added 2026-07-29 (P-2, bold-jackal harness triage).

## Story Points Cannot Be Set on a Sub-Task (Klever, KTP Project)

`jira_skill.py update <KEY> --estimate N` fails on a sub-task with `Field 'customfield_10028'
cannot be set. It is not on the appropriate screen, or unknown.` This is not a skill bug — the
story-point field is simply not on the sub-task edit screen in Jira's own configuration, which is
also why sub-tasks always show as unpointed in the board UI. Estimates live on the parent Story
only.

**How to apply:** Do not attempt to set `--estimate` on a `Sub-task` issue type. Any estimation or
reporting logic that walks sub-tasks looking for story points should read the parent Story's
estimate instead, or explicitly treat sub-tasks as unpointed by design.

**Source:** KTP-830 dusk-owl session (2026-08-07).

## A Ticket Folder's Cached `jira/comments/` Goes Stale — Re-Fetch Before Reasoning About History

`jira fetch` materializes a ticket's comments to disk under the ticket folder. That copy is a
snapshot as of the fetch time, not a live view. A review reading a weeks-old cache can conclude a
decision is "unsourced — no comment says this" when the supporting comment exists and simply
post-dates the cache; the conclusion is confidently wrong and can reopen an already-settled
decision.

This extends the existing fetch-before-read discipline (see the global CLAUDE.md "Fetch-before-read
gate") to a case it does not explicitly name: that gate calls out stale git checkouts, but a
materialized Jira comment cache is the same failure mode against a different kind of live system.

**How to apply:** Before drawing any conclusion from a ticket folder's cached `jira/comments/` (or
any other materialized Jira snapshot) about what was or was not discussed, re-run `jira fetch`
first. Treat the on-disk copy as dated evidence, never as the ticket itself.

**Source:** KTP-830 dusk-owl session (2026-08-07).

---

## `search <JQL> --full` throws on sprint-scoped JQL

`python3 jira_skill.py --org klever search "project = KTP AND sprint = 1781" --full` throws `'PropertyHolder' object has no attribute 'customfield_10028'`. This is reproducible, not a one-off, and affects any sprint-wide pull that wants full ticket data in one call.

**Workaround:** Fetch compact search results first (no `--full`) to get the keys. Then pull detail per issue, either with `jira.issue(key, expand='changelog')` or the plain `get --full` path, which works fine per issue.

**Source:** session amber-finch, sprint-skill consolidation work (2026-08-24).

# Unsent drafts: durable state and reconcile

A draft that is previewed but not approved in the same turn has no owner. When the session closes it becomes invisible. In one measured case a correct reply sat unsent for six days, and a later session wrote a worse reply from scratch. This procedure gives every held draft a record, a hard expiry, and a remote check before anyone resurfaces it.

The state lives in `draft-state.json` (`<ticket-dir>/reports/ship/` when a ticket folder exists, else the global file next to the script). Write it only with `draft-state.py`.

```bash
DS=~/.claude-shared-config/skills/post-comment/draft-state.py
```

## 1. The human does not approve in this turn

Record the draft before the turn ends:

```bash
python3 $DS [--ticket-dir <dir>] hold --draft <path> --target <url|key|channel> --platform <jira|github|gitlab|slack> \
  --expires <YYYY-MM-DD> --reason "<why it is held>" [--condition "<event> confirmed by <person>"]
```

The expiry date is required. "Hold until we decide" is refused: a record with no expiry still waits for someone to remember. If the org has a Gabriel inbox, also add a `pending/` item with `/inbox-writer` that names the draft path, the target and the expiry.

## 2. Close the record

- Posted through this pipeline: `python3 $DS posted --draft <path> --url <url>` (in addition to `post-log.py`).
- Human decides not to send: `python3 $DS discarded --draft <path> --reason "<why>"`.
- A newer draft replaces it: `python3 $DS superseded --draft <path> --by <new-path>`.

Move any matching inbox item to `resolved/`.

## 3. Before you resurface a held draft, reconcile the remote state

A missing local post-log entry does not prove the draft is unsent. A later session may have posted it by hand. Run `due` first:

```bash
python3 $DS due
```

For each row, follow `action`:

| action | Do this |
|---|---|
| `reconcile_first` | Read the remote thread (Jira comments, PR/MR notes, Slack thread). Then run `reconcile --remote posted|absent|unknown --evidence "<what you checked>"`. |
| `resurface` | The remote check is fresh and found nothing. Show the draft to the human: post, revise, or discard. |
| `ambiguous` | You could not read the remote state. Report it as ambiguous. Never call it unsent. |

A `reconcile --remote posted` closes the record. It never resurfaces.

## 4. Find drafts that never got a record

```bash
python3 $DS scan --drafts-dir <ticket>/reports/drafts --post-log <ticket>/reports/ship/post-log.yaml
```

Exit 1 lists drafts with no record, no post-log entry and no `.posted` file. For each one: reconcile the remote state first. If it was posted, `reconcile --remote posted --target <t>` records it. If not, `hold` it with an expiry, or ask the human to discard it.

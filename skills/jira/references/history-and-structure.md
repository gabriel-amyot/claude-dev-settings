# Description history, restore, and structure writes

## Read a field's history (auto, read-only)

```bash
uv run ~/.claude-shared-config/skills/jira/jira_skill.py --org klever history KTP-746 [--field description] [--back N]
```

- Lists the edits of the field, newest first: date, author, size before and after.
- `--back 1` adds `recovered_text`: the text before the last edit. `--back N` walks
  further back.
- `chain_complete: false` or a `warning` means the changelog has a gap. Read the text
  before you use it.
- `newest_matches_current: false` means the field changed outside the changelog.

This writes nothing. Use it freely.

## Restore a description (explicit and manual only)

Run only when the user asks to restore. A restore is a Jira write.

1. Dry run. It shows the recovered text, the reporter and any warning:
   ```bash
   uv run .../jira_skill.py --org klever restore-description KTP-718 --back 1
   ```
2. Show the text to the user. Wait for explicit approval.
3. Write. The current text is saved to the backup folder first, and the result
   reports `verified` after a re-read:
   ```bash
   uv run .../jira_skill.py --org klever restore-description KTP-718 --back 1 \
     --confirm --backup-dir <ticket folder>/data/backups [--force]
   ```

- `--force` is needed when the reporter is not you (ownership gate). Use it only when
  the user approved a restore of that person's ticket.
- Do not restore through `update --description`. It runs a markdown-to-wiki conversion
  that can change wiki text (a `#` list item becomes a heading).
- A rewritten spec that must not overwrite the reporter's text goes in `AC-LOCAL.md`.

## Structure writes (explicit and manual only)

`update --parent KEY`, `update --epic KEY` and `retype KEY --type T` change the shape
of a ticket. Run them only on an explicit request.

- `epic KEY` walks parent and epic link upward. A Sub-task's own epic link is empty,
  so do not read "not under an epic" from that field alone.
- A Sub-task to Story conversion (or the reverse) can be refused by the API. Then
  `retype` returns `ui_steps`. Relay those steps to the user. Do not report the
  conversion as done, and do not skip it.
- For more than one ticket: print the before and after tree for all of them, wait for
  explicit confirmation, then write one ticket at a time and re-read each one.

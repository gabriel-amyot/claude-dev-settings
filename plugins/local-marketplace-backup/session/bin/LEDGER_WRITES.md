# Writing to `sessions/ledger.yaml` — use the helper, never hand-edit

**A PreToolUse hook blocks Edit/Write on `sessions/ledger.yaml`.** All ledger
corruption (col-0 indentation, mis-filed records, fused/duplicate entries) came
from hand-editing it. The `ledger` helper is the only write path: it takes an
flock, journals a pre-image, validates + re-parses before an atomic replace, and
bumps `version`+`modified` for you. You never touch the file directly.

**The helper exists. Do not rebuild it.** It is on PATH as `ledger`:

```bash
ledger --org klever validate          # if this runs, you have it
```

Absolute path, if PATH is not set up: `~/.claude/plugins/local-marketplace/session/bin/ledger.py`
(shims: `~/.local/bin/ledger`, `~/.claude/bin/ledger`).

```bash
LEDGER=~/.claude/plugins/local-marketplace/session/bin/ledger.py
```

> A shallow `find ~/.claude -maxdepth 4` does NOT reach `ledger.py` (it sits at depth 5).
> On 2026-08-13 an agent ran exactly that search, concluded the helper was never built,
> wrote the ledger with `yaml.safe_dump` + `os.replace`, and reflowed the whole file:
> **8127 changed lines for a 6-line append.** Run `command -v ledger` before concluding
> anything is missing.

**Pick `--org` from the cwd** (do NOT pass a path):
`grp-beklever-com` → `klever` · `supervisr-ai` → `supervisr` · `gabriel-amyot` → `personal`

## Operations

**Append a session** (init, force-create, retroactive scaffold):
```bash
python3 $LEDGER --org <org> append --section sessions --json '{"slug":"...","intent":"...","org":"<org>","status":"active","started_from_handoff":false,"related_ticket":"KTP-x or none","theme":"...","created":"<ISO>"}'
```

**Append a handoff** (handoff, report-back close):
```bash
python3 $LEDGER --org <org> append --section handoffs --json '{"file":"<name>.md","ticket":"KTP-x or none","theme":"<tag>","status":"awaiting_initiation","source_session":"<slug/label>","target_session":null,"created":"<ISO>","modified":"<ISO>","version":1}'
# close report: add  "closes":"<original-handoff.md>"
```

**Update an entry in place** (status transitions, target_session, close fields, autopilot, notes):
```bash
python3 $LEDGER --org <org> update --section handoffs --key <file> --set status=initiated --set target_session=<slug>
python3 $LEDGER --org <org> update --section sessions --key <slug> --set status=closed --set closed=<ISO>
```
- `--set k=v` (repeatable). Values coerce: `null`→null, `true/false`→bool, digits→int, else string.
- `--append-list children=<slug>` appends to a list field. `--remove <key>` deletes a field.
- The identity key (`slug`/`file`) is immutable — the helper refuses to change it.

**Claim a handoff** (pickup / autopilot — CAS, asserts status before writing):
```bash
python3 $LEDGER --org <org> claim --key <file> --expect-status awaiting_initiation --set status=initiated --set target_session=<slug>
```
Exits non-zero (conflict) if another session already changed it — do not retry blindly.

**Batch** (pickup/autopilot triage — many entries, one header bump):
```bash
python3 $LEDGER --org <org> batch --ops '[{"section":"handoffs","op":"update","key":"<f>","set":["status=completed"]}, {"section":"handoffs","op":"append","entry":{...}}]'
```

**Rename an identity key** (deduplication only — the one command allowed to touch `slug`/`file`):
```bash
python3 $LEDGER --org <org> rekey --section sessions --old <slug> --new <slug> [--occurrence N]
```
- `update` refuses identity-key changes on purpose. `rekey` is the escape hatch for duplicates.
- A duplicate key is unreachable any other way: `find_entry` always returns the first match.
- `--occurrence` is 1-based in document order, and is **required** when `--old` matches more than one entry. Run it without `--occurrence` first — the error lists every match with its status and dates so you can pick.
- Refuses a `--new` that already exists.
- **Renaming a ledger slug does not rename its folder.** Prefer a `--new` that matches an existing archive folder (`sessions/archive/done/{slug}-{date}`) over inventing a suffix.

**Read one entry / health check** (read-only):
```bash
python3 $LEDGER --org <org> get --section handoffs --key <file>
python3 $LEDGER --org <org> validate     # parse + structural lint; nonzero on drift
```

## If the helper refuses
- **"mutation would introduce schema problems"** — your change adds a NEW invalid status / duplicate key. Fix the value. (Pre-existing debt does not block you.)
- **`validate` says INVALID** — this does NOT block your write. `commit()` blocks only problems your mutation *introduces*; pre-existing debt is tolerated. Fix duplicate identity keys with `rekey` when you have time; do not stop work over it.
- **"ledger is busy"** — another writer holds the lock; wait and re-run.
- **"claim conflict"** — someone else changed the entry; re-read with `get` and decide.
- Emergency only (guard is wrong): `touch ~/.claude/.ledger-guard-off` disables the block.

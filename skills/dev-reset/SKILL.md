---
name: dev-reset
description: "Reset Supervisr dev environment data. Supports multiple reset profiles (lead pipeline, compliance, etc). Use when the user says 'reset dev', 'clean dev', 'wipe dev data', 'fresh pipeline', 'dev cleanup', or needs a clean slate before re-ingesting data."
---

# Dev Reset Skill

Reset data in the Supervisr dev environment. This skill supports multiple **reset profiles**, each targeting a different pipeline or data domain.

## CRITICAL: Always Confirm the Profile First

**Never assume which profile the user wants.** Always ask:

> Which data do you want to reset?

Present the available profiles using `AskUserQuestion`. If the user describes something that doesn't match an existing profile, respond:

> That reset profile doesn't exist yet. I can help build it. We'll need:
> 1. Which Datastore project/database/namespace/kinds to clear
> 2. Which BQ tables (if any) the user needs to manually delete
> 3. Any post-cleanup verification steps
>
> Want to define it now?

If yes, walk through those questions, then add a new profile section to this skill file.

---

## Available Profiles

### `leads` — Lead Lifecycle Pipeline

Clears LLS leads, ERS lead event store, and ERS lead materialized view.

**Datastore targets:**

| Store | Project | Database | Namespace | Kinds |
|---|---|---|---|---|
| LLS leads | dev-core | lead-lifecycle-us-central1 | lead_lifecycle | Lead |
| ERS event store | dev-data | compliance-us-central1 | (default) | lead_events |
| ERS MV | dev-data | compliance-us-central1 | (default) | leads |

**BQ tables (manual):**
- `prj-sprvsr-d-data-fudybht2id:compliance.lead_events`

### `partner` — Partner Configuration Pipeline

Clears partner configuration events and MV.

**Datastore targets:**

| Store | Project | Database | Namespace | Kinds |
|---|---|---|---|---|
| ERS event store | dev-data | compliance-us-central1 | (default) | partner_configuration_events |
| ERS MV | dev-data | compliance-us-central1 | (default) | partner_configurations |

**BQ tables (manual):**
- `prj-sprvsr-d-data-fudybht2id:compliance.partner_configuration_events`

### `lead-source` — Lead Source Configuration Pipeline

**Datastore targets:**

| Store | Project | Database | Namespace | Kinds |
|---|---|---|---|---|
| ERS event store | dev-data | compliance-us-central1 | (default) | lead_source_configuration_events |
| ERS MV | dev-data | compliance-us-central1 | (default) | lead_source_configurations |

**BQ tables (manual):**
- `prj-sprvsr-d-data-fudybht2id:compliance.lead_source_configuration_events`

### `phone-pool` — Phone Pool Pipeline

**Datastore targets:**

| Store | Project | Database | Namespace | Kinds |
|---|---|---|---|---|
| ERS event store | dev-data | compliance-us-central1 | (default) | phone_pool_events |
| ERS MV | dev-data | compliance-us-central1 | (default) | phone_pool_entries |

**BQ tables (manual):**
- `prj-sprvsr-d-data-fudybht2id:compliance.phone_pool_events`

### `all` — Full Pipeline Reset

Runs all profiles above in sequence.

---

## Execution

### Step 0: Ask which profile

Use `AskUserQuestion` with the profile names listed above plus an "Other (describe what you need)" option. If the user picks "Other", follow the new-profile flow described at the top.

### Step 1: Dry-run counts

Run `nuke_entities.py` without `--execute` to show entity counts for the selected profile's targets:

```bash
NUKE_SCRIPT="$(find ~/Developer/supervisr-ai/project-management/tools/datastore-ops -name 'nuke_entities.py' -print -quit)"

# Example for leads profile:
python3 "$NUKE_SCRIPT" --project dev-core --database lead-lifecycle-us-central1 --namespace lead_lifecycle --kinds Lead
python3 "$NUKE_SCRIPT" --project dev-data --database compliance-us-central1 --kinds lead_events
python3 "$NUKE_SCRIPT" --project dev-data --database compliance-us-central1 --kinds leads
```

### Step 2: Confirm with user

Present the entity counts per target. Show which BQ tables they'll need to delete manually. Ask for explicit confirmation before proceeding.

### Step 3: Execute deletion

Run the same commands with `--execute --yes`:

```bash
python3 "$NUKE_SCRIPT" --project dev-core --database lead-lifecycle-us-central1 --namespace lead_lifecycle --kinds Lead --execute --yes
python3 "$NUKE_SCRIPT" --project dev-data --database compliance-us-central1 --kinds lead_events --execute --yes
python3 "$NUKE_SCRIPT" --project dev-data --database compliance-us-central1 --kinds leads --execute --yes
```

### Step 4: BQ reminder

After Datastore cleanup, list the BQ tables the user needs to delete manually in the BQ console. ERF auto-provisions tables with correct schemas on the next event.

### Step 5: Verification

1. Re-run dry-run, expect 0 counts
2. User confirms BQ tables deleted
3. Pipeline ready for fresh data

---

## Adding a New Profile

When a user needs a reset profile that doesn't exist:

1. Ask them for: project, database, namespace, kinds, and any BQ tables
2. Add a new `### profile-name` section under "Available Profiles" following the same table format
3. The skill is immediately usable with the new profile on next invocation

---

## Safety

- `nuke_entities.py` has a hardcoded DEV allowlist. It refuses UAT/PROD project IDs.
- `nuke_entities.py` backs up entities to JSON before deleting.
- BQ tables are NEVER deleted programmatically. User does it manually in the console.
- Always show counts and confirm before executing.
- Never assume which profile the user wants. Always ask first.

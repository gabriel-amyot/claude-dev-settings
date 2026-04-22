---
name: gcloud
description: "Query GCP resources for Supervisr.AI and Klever. Check Cloud Run logs, query Datastore, debug deployments, inspect service errors. Project aliases: dev-core, dev-data, uat-core, uat-data, prod-core, prod-data (Supervisr); dev-frontend, dev-proximity, dev-pbmod, dev-insights, dev-pipeline, dev-vpc (Klever). Triggers on: 'check logs', 'what is failing in dev', 'query datastore', or any known project alias. Does NOT manage infrastructure (use Terraform/DAC repos for that). Does NOT run terraform plan/apply. Input: project alias or service name. Returns: logs, entity data, service status."
---

# GCloud Skill

Multi-org aware. Org is auto-detected from `$PWD`. Override with `--org <name>`.

## Project Aliases

### Supervisr.AI (account: gabriel@origin8cares.com)

| Alias | Project ID |
|-------|-----------|
| `dev-core` | `prj-sprvsr-d-core-kkomv80zrg` |
| `dev-data` | `prj-sprvsr-d-data-fudybht2id` |
| `uat-core` | `prj-sprvsr-u-core-d1et2qoxtw` |
| `uat-data` | `prj-sprvsr-u-data-mjn3pfrtey` |
| `prod-core` | `prj-sprvsr-p-core-6of3dwjpzt` |
| `prod-data` | `prj-sprvsr-p-data-n2s076aw4z` |

### Klever (account: gamyot@beklever.com)

| Alias | Project ID |
|-------|-----------|
| `dev-frontend` | `prj-d-global-front-6kpke3wn54` |
| `dev-proximity` | `prj-d-grid-proxim-fe0wn470yh` |
| `dev-pbmod` | `prj-d-grid-pbmod-nb9x844rqk` |
| `dev-insights` | `prj-d-grid-insigt-3vm2fcstbw` |
| `dev-pipeline` | `prj-d-biz-report-im9q1fvvc7` |
| `dev-vpc` | `prj-d-env-main-bmuvo1wgpu` |

Config lives at: `~/.claude-shared-config/skills/gcloud/gcloud_config.json`

## Logs

Check GCP Cloud Logging for errors, warnings, and service issues.

### When to Use

User asks about errors, failures, or issues in a GCP environment. Examples: "check dev-core logs", "what's failing", "any errors in the last 2 hours", "Cloud Run errors", "dev-frontend errors".

### Script

```bash
# Basic: last 1h of ERROR+ logs (org auto-detected from $PWD)
python3 ~/.claude-shared-config/skills/gcloud/scripts/logs.py <project>

# Explicit org override
python3 ~/.claude-shared-config/skills/gcloud/scripts/logs.py dev-frontend --org klever

# Custom time window
python3 ~/.claude-shared-config/skills/gcloud/scripts/logs.py <project> --hours 2

# Filter by service/text
python3 ~/.claude-shared-config/skills/gcloud/scripts/logs.py <project> --filter "lead-lifecycle"

# Include WARNING severity
python3 ~/.claude-shared-config/skills/gcloud/scripts/logs.py <project> --severity WARNING

# Custom limit
python3 ~/.claude-shared-config/skills/gcloud/scripts/logs.py <project> --limit 1000

# Resource type filter
python3 ~/.claude-shared-config/skills/gcloud/scripts/logs.py <project> --resource-type cloud_run_revision
```

### Workflow

1. Run `scripts/logs.py` with appropriate args
2. Read the `_summary.yaml` file first (concise, ~20-30 lines)
3. If the summary doesn't explain the issue, use Grep on the raw JSON file for specific patterns
4. **Never read the full raw JSON into context**

### Output

Files are saved to `/tmp/gcloud-logs/`:
- `{project}_{timestamp}.json` (raw log entries)
- `{project}_{timestamp}_summary.yaml` (structured summary with top errors, severity breakdown, stack trace heads)

## Config Management

```bash
# List all orgs, accounts, aliases
python3 ~/.claude-shared-config/skills/gcloud/scripts/gcloud_config_setup.py list

# Verify gcloud auth for all accounts
python3 ~/.claude-shared-config/skills/gcloud/scripts/gcloud_config_setup.py check-auth

# Add a new alias
python3 ~/.claude-shared-config/skills/gcloud/scripts/gcloud_config_setup.py add-alias klever dev-analytics prj-d-analytics-xyz123

# Remove an alias
python3 ~/.claude-shared-config/skills/gcloud/scripts/gcloud_config_setup.py remove-alias klever dev-analytics

# Set default org
python3 ~/.claude-shared-config/skills/gcloud/scripts/gcloud_config_setup.py default klever
```

## Datastore Operations

**Supervisr-only.** The nuke script operates on Supervisr dev environments only.

### WARNING: Destructive Operations

The nuke script (`tools/datastore-ops/nuke_entities.py`) is DEV-ONLY by design.
It will refuse to run against UAT or PROD project IDs. This is not configurable.

### When to Use
- User asks to delete/clear/nuke Datastore entities in dev
- User asks to extract/backup Datastore data from dev
- User asks to count entities in a Datastore kind

### Scripts
- **Bulk delete:** `python3 tools/datastore-ops/nuke_entities.py`
- **Extract/backup:** `python3 tools/datastore-extract/extract_dev_data.py`

### Bulk Delete Examples

```bash
# Dry run (default) - counts entities, no deletion
python3 tools/datastore-ops/nuke_entities.py \
  --project dev-data \
  --database compliance-us-central1 \
  --kinds leads,lead_events

# Execute with confirmation prompt
python3 tools/datastore-ops/nuke_entities.py \
  --project dev-data \
  --database compliance-us-central1 \
  --kinds leads,lead_events \
  --execute

# Execute without prompt (scripted use)
python3 tools/datastore-ops/nuke_entities.py \
  --project dev-core \
  --database lead-lifecycle-us-central1 \
  --kinds leads \
  --execute --yes
```

### Safety Layers (5 deep)
1. Config-driven DEV allowlist (dev-core, dev-data, rnd-bac1 only)
2. Config-driven UAT/PROD blocklist with abort
3. Dry-run by default (--execute required)
4. Backup to JSON before any deletion (aborts if backup fails)
5. Interactive confirmation (type DELETE, or --yes to bypass)

---
name: gcloud
description: "Use when the user asks about GCP resources: checking logs, querying Datastore, debugging deployments, Cloud Run errors, service issues. Triggers on 'check logs', 'what\\'s failing in dev', 'any errors in dev-core', 'query datastore', 'gcloud'. Even if they don't say 'GCP' explicitly but mention a known project alias (dev-core, uat-data, prod-core, etc.) or service debugging."
---

# GCloud Skill

## Project Aliases

| Alias | Project ID |
|-------|-----------|
| `dev-core` | `prj-sprvsr-d-core-kkomv80zrg` |
| `dev-data` | `prj-sprvsr-d-data-fudybht2id` |
| `uat-core` | `prj-sprvsr-u-core-d1et2qoxtw` |
| `uat-data` | `prj-sprvsr-u-data-mjn3pfrtey` |
| `prod-core` | `prj-sprvsr-p-core-6of3dwjpzt` |
| `prod-data` | `prj-sprvsr-p-data-n2s076aw4z` |

## Logs

Check GCP Cloud Logging for errors, warnings, and service issues.

### When to Use

User asks about errors, failures, or issues in a GCP environment. Examples: "check dev-core logs", "what's failing", "any errors in the last 2 hours", "Cloud Run errors".

### Script

```bash
# Basic: last 1h of ERROR+ logs
python3 ~/.claude-shared-config/skills/gcloud/scripts/logs.py <project>

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

## Datastore (Future)

Placeholder for Datastore query support. Not yet implemented.

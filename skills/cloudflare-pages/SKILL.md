---
name: cloudflare-pages
description: Query Cloudflare Pages deployments, build logs, and D1 database for the Compostela Guide project. Use this skill whenever the user mentions Cloudflare, deployment status, build logs, "is the site deployed", "check the deploy", "why isn't my site updating", subscriber count, D1 database, or anything related to the compostelaguide.com hosting and deployment pipeline. Also triggers on "check deployments", "deploy status", "build failed", "site not updating", "Danielle's changes not showing".
---

# Cloudflare Pages Skill

Query Cloudflare Pages and D1 for the compostelaguide.com project. This skill reads deployment history, build logs, and subscriber data without making any changes.

## Setup

Credentials live in the project's `.env.local` (git-ignored). The skill reads them at runtime:

```
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...   # Token: compostelaguide-claude-readonly (Pages Read, D1 Read, Workers Scripts Read)
```

If either variable is missing, tell the user to add them to `.env.local` in the compostelaguide project root. The account ID is in the Cloudflare Dashboard URL. The token is created at dash.cloudflare.com/profile/api-tokens with Cloudflare Pages Read + D1 Read permissions.

The project name is `compostelaguide`. The D1 database ID is in `wrangler.toml`.

## Modes

### `/cloudflare status`

Quick health check. Show the latest deployment: status, timestamp, trigger type, branch, and commit message.

```bash
source .env.local 2>/dev/null
curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/pages/projects/compostelaguide/deployments?per_page=1" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
d = data['result'][0]
stage = d.get('latest_stage', {})
trigger = d.get('deployment_trigger', {})
meta = trigger.get('metadata', {})
print(f\"Status:  {stage.get('status', '?')}\")
print(f\"Stage:   {stage.get('name', '?')}\")
print(f\"Time:    {d.get('created_on', '?')[:19]}\")
print(f\"Trigger: {trigger.get('type', '?')}\")
print(f\"Branch:  {meta.get('branch', '?')}\")
print(f\"Commit:  {meta.get('commit_message', '?')[:80]}\")
print(f\"URL:     {d.get('url', '?')}\")
"
```

Present the output as a clean table. If status is not "success", flag it and suggest checking logs.

### `/cloudflare deployments`

List the 10 most recent deployments in a table: status, timestamp, trigger type, branch, commit message (truncated).

```bash
source .env.local 2>/dev/null
curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/pages/projects/compostelaguide/deployments?per_page=10" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"{'Status':10} {'Time':20} {'Trigger':12} {'Branch':25} {'Commit'}\")
print('-' * 100)
for d in data['result']:
    s = d.get('latest_stage', {}).get('status', '?')
    t = d.get('created_on', '?')[:19]
    tr = d.get('deployment_trigger', {}).get('type', '?')
    br = d.get('deployment_trigger', {}).get('metadata', {}).get('branch', '?')
    cm = d.get('deployment_trigger', {}).get('metadata', {}).get('commit_message', '?')[:50]
    print(f'{s:10} {t:20} {tr:12} {br:25} {cm}')
"
```

After showing the table, note any patterns: all failures, excessive webhook triggers, stale deploys.

### `/cloudflare logs {deployment-id}`

Fetch build logs for a specific deployment. The deployment ID comes from the deployments list.

```bash
source .env.local 2>/dev/null
DEPLOY_ID="$1"
curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/pages/projects/compostelaguide/deployments/$DEPLOY_ID/history/logs" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
for entry in data.get('result', []):
    ts = entry.get('ts', '')[:19]
    line = entry.get('line', '')
    print(f'{ts}  {line}')
"
```

If the user doesn't provide a deployment ID, fetch the latest failed deployment's logs automatically:

```bash
# Find latest non-success deployment
curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/pages/projects/compostelaguide/deployments?per_page=20" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
for d in data['result']:
    if d.get('latest_stage', {}).get('status') != 'success':
        print(d['id'])
        sys.exit(0)
print('ALL_SUCCESS')
"
```

If all deployments are successful, say so. If there's a failure, fetch its logs and summarize the error.

### `/cloudflare subscribers`

Query the D1 subscribers table. Read the database ID from `wrangler.toml` in the project root.

```bash
source .env.local 2>/dev/null
DB_ID=$(grep database_id wrangler.toml | head -1 | sed 's/.*= *"//' | sed 's/".*//')
curl -s -X POST \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) as total FROM subscribers"}' \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/d1/database/$DB_ID/query"
```

Show the total count. If the user asks for the full list:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT email, subscribed_at FROM subscribers ORDER BY subscribed_at DESC LIMIT 50"}' \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/d1/database/$DB_ID/query"
```

## Error Handling

- **401/403:** Token expired or insufficient permissions. Tell the user to check their API token at dash.cloudflare.com/profile/api-tokens.
- **404 on project:** Project name might have changed. Check `wrangler.toml` for the correct project name.
- **Empty .env.local:** Guide the user through setup (account ID from dashboard URL, token creation with Pages Read + D1 Read).
- **D1 query fails:** The database might not have the subscribers table yet. Tell the user to run the migration: `npx wrangler d1 migrations apply compostelaguide-subscribers`.

## When to Use Which Mode

| User says | Mode |
|-----------|------|
| "is the site deployed?" / "check the deploy" / "deploy status" | `status` |
| "show me recent deployments" / "deployment history" | `deployments` |
| "why did the build fail?" / "build logs" / "deploy failed" | `logs` |
| "how many subscribers?" / "check the newsletter db" | `subscribers` |
| "Danielle's changes aren't showing" / "site not updating" | `status` first, then `logs` if there's a failure |

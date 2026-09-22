# Klever Mech Suit — Installation Guide

## Per-Person Setup Checklist

### 1. Plugin (one-time, already done if you're reading this)
The plugin lives at `~/.claude/plugins/klever-mech-suit/`. It's shared across all workspaces.

### 2. Create their workspace folder
Pick a location that makes sense for the person. Example: `~/Documents/klever-workspace/`

```bash
WORKSPACE=~/Documents/klever-workspace
cp -r <path-to>/workspace-template/* "$WORKSPACE/"
cp <path-to>/workspace-template/.mcp.json "$WORKSPACE/"
```

### 3. Personalize CLAUDE.md
Open `$WORKSPACE/CLAUDE.md` and replace:
- `{name}` with their first name
- `{role}` with their role (e.g., "Campaign Manager", "Account Executive")
- `{team}` with their team (e.g., "Programmatic", "Sales", "Operations")
- Fill in the Role-Specific Section based on interview notes

### 4. Configure .mcp.json
Open `$WORKSPACE/.mcp.json`. For each connector:
- Uncomment the ones relevant to their role
- Add auth tokens (they'll need to generate these)
- Most people need: Gmail, Drive, Calendar, Slack
- Notion only if they use the Klever Wiki directly

### 5. Seed references (optional but recommended)
Pull 2-3 role-relevant documents into `references/`:
- A template they use often (proposal, report, media plan)
- An SOP they follow regularly
- Any quick-reference guide for their DSP

### 6. Open CoWork
- Set the workspace folder to `$WORKSPACE`
- Start a session

### 7. Run the Hivemind wizard
Say: **"Help me set up my hivemind"**

The wizard will:
1. Scan their connected tools
2. Ask who they are and what they do
3. Build their MY_CONTEXT.md from real data

### 8. Verify
Start a new session and check:
- [ ] Hook outputs their name and branch count
- [ ] Ask "who am I?" and Claude answers from MY_CONTEXT.md
- [ ] Ask a Klever question and Claude checks references/ first
- [ ] Complete a task and check notes/session-log.md for an entry
- [ ] Complete a repeated workflow and Claude suggests saving it

## Troubleshooting

**Hook doesn't fire**: Check `~/.claude/plugins/klever-mech-suit/hooks/hooks.json` exists and the script is executable (`chmod +x hooks/scripts/session-orient.sh`).

**Hivemind skill not found**: Verify the plugin is in `~/.claude/plugins/` and restart CoWork.

**MCP tools not connecting**: Check `.mcp.json` tokens are valid. Each connector has its own auth flow.

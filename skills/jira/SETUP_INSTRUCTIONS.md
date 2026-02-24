# Jira Multi-Organization Setup - Quick Reference

## What Was Implemented

✅ Path-based auto-detection of Jira organizations
✅ Secure token storage in macOS Keychain
✅ Organization info displayed when switching between orgs
✅ Manual override with `--org` flag
✅ Backward compatible with environment variables

---

## One-Time Setup

### Step 1: Store API Tokens

```bash
# Configure Klever Jira token
~/.claude-shared-config/skills/jira/jira_config_setup.py configure klever
# When prompted, paste your Klever Jira API token

# Configure Supervisr AI Jira token
~/.claude-shared-config/skills/jira/jira_config_setup.py configure supervisrai
# When prompted, paste your Supervisr AI Jira API token
```

### Step 2: Verify Setup

```bash
~/.claude-shared-config/skills/jira/jira_config_setup.py list
```

You should see:
```
=== Configured Jira Organizations ===

klever
  URL: https://beklever.atlassian.net
  Username: gamyot@beklever.com
  Path: /Users/gabrielamyot/Developer/grp-beklever-com
  Default Project: INS
  Token: ✓ Token stored

supervisrai [DEFAULT]
  URL: https://origin8cares.atlassian.net
  Username: gamyot@origin8cares.com
  Path: /Users/gabrielamyot/Developer/supervisr-ai
  Token: ✓ Token stored
```

---

## Daily Usage

### Auto-Detection (Recommended)

Just use the skill normally from any directory:

```bash
# From Klever directory → automatically uses Klever Jira
cd ~/Developer/grp-beklever-com
python3 ~/.claude-shared-config/skills/jira/jira_skill.py list

# From Supervisr AI directory → automatically uses Supervisr AI Jira
cd ~/Developer/supervisr-ai
python3 ~/.claude-shared-config/skills/jira/jira_skill.py list

# From anywhere else → uses Supervisr AI (default)
cd /tmp
python3 ~/.claude-shared-config/skills/jira/jira_skill.py list
```

The skill displays which organization is being used:
```
ℹ️  Using organization: klever
   Jira: https://beklever.atlassian.net (gamyot@beklever.com)
   Path: /Users/gabrielamyot/Developer/grp-beklever-com
```

### Manual Override

Use `--org` flag to override auto-detection:

```bash
# Use Klever even if you're in Supervisr AI directory
python3 ~/.claude-shared-config/skills/jira/jira_skill.py list --org klever
```

### Suppress Organization Info

Use `--skip-disclaimer` to hide the organization message:

```bash
python3 ~/.claude-shared-config/skills/jira/jira_skill.py list --skip-disclaimer
```

---

## Configuration

### View Configured Organizations

```bash
~/.claude-shared-config/skills/jira/jira_config_setup.py list
```

### Change Default Organization

```bash
~/.claude-shared-config/skills/jira/jira_config_setup.py default klever
```

### Update Token for an Organization

```bash
~/.claude-shared-config/skills/jira/jira_config_setup.py configure supervisrai
```

### Debug: Show Token (First 20 chars)

```bash
~/.claude-shared-config/skills/jira/jira_config_setup.py get-token klever
```

---

## File Locations

- **Configuration**: `~/.claude-shared-config/skills/jira/jira_config.json`
- **Setup Script**: `~/.claude-shared-config/skills/jira/jira_config_setup.py`
- **Jira Skill**: `~/.claude-shared-config/skills/jira/jira_skill.py`
- **Tokens**: Stored securely in macOS Keychain (service: `claude-jira`)

---

## Troubleshooting

### "No token for 'klever'"

Run:
```bash
~/.claude-shared-config/skills/jira/jira_config_setup.py configure klever
```

### "Organization 'invalid' not found"

Check available organizations:
```bash
~/.claude-shared-config/skills/jira/jira_config_setup.py list
```

### "Connection failed"

- Verify token is correct: `~/.claude-shared-config/skills/jira/jira_config_setup.py get-token klever`
- Verify Jira URL is reachable
- Check token hasn't expired

---

## How It Works

1. **Path Detection**: Detects your organization by matching your current directory against configured paths
2. **Token Retrieval**: Gets your API token from macOS Keychain
3. **Info Display**: Shows which organization is being used (to stderr, not stdout)
4. **Jira Connection**: Connects using the organization's URL, username, and token
5. **JSON Output**: Returns results in JSON format (clean, no info mixed in)

---

## Security

- ✅ API tokens stored in encrypted macOS Keychain
- ✅ Configuration file permissions: `600` (user read/write only)
- ✅ Tokens never printed in full (only first 20 chars for debugging)
- ✅ Tokens not stored in shell history (uses `getpass()`)

---

**Setup Status**: Ready to use!
**Last Updated**: 2026-02-07

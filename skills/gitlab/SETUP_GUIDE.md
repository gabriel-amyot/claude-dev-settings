# GitLab Skill - Setup Guide

## Overview

Your GitLab skill is now configured to support 3 organizations with secure token management:

- **klever** → `/Users/gabrielamyot/Developer/grp-beklever-com`
- **origin8** → `/Users/gabrielamyot/Developer/origin8`
- **supervisrai** → `/Users/gabrielamyot/Developer/supervisr-ai`

All tokens are stored securely in macOS Keychain and never exposed in configuration files.

## Step 1: Get Your GitLab Personal Access Token

For each organization (they all use the same GitLab instance), generate a personal access token:

1. Go to: https://gitlab.prod.origin8cares.com/-/user_settings/personal_access_tokens
2. Click "Add new token"
3. Name it: `claude-gitlab-{orgname}` (e.g., `claude-gitlab-supervisrai`)
4. Select scopes: `api`, `read_repository`
5. Click "Create personal access token"
6. **Copy the token immediately** (you won't see it again)

## Step 2: Configure Your Organizations

### Option A: Automated Setup (Recommended)

Run the setup script to configure all 3 organizations at once:

```bash
bash ~/.claude-shared-config/skills/gitlab/setup-all.sh
```

You'll be prompted to enter your GitLab token for each organization.

### Option B: Manual Setup

Configure each organization individually:

```bash
# Configure supervisrai
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure supervisrai
# Enter token when prompted

# Configure origin8
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure origin8
# Enter token when prompted

# Configure klever
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure klever
# Enter token when prompted

# View all configurations
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py list
```

## Step 3: Verify Setup

Test that everything is working:

```bash
# List all groups in your default organization
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-groups

# You should see output like:
# [
#   {
#     "id": 123,
#     "name": "group-name",
#     "path": "group-path",
#     "full_path": "group-path"
#   },
#   ...
# ]
```

## Token Security

Your GitLab tokens are stored in **macOS Keychain** under service `claude-gitlab` with accounts like `gitlab_supervisrai`, `gitlab_origin8`, etc.

Benefits:
- Tokens are encrypted and never stored in plain text
- Only accessible to authorized processes
- Easy to manage through macOS Keychain
- Can be deleted/regenerated without touching configuration files

To view a token (for debugging):
```bash
security find-generic-password -s claude-gitlab -a gitlab_supervisrai -w
```

To delete a token (to reconfigure):
```bash
security delete-generic-password -s claude-gitlab -a gitlab_supervisrai
```

## Now You're Ready!

Use the skill with Claude Code or directly:

```bash
# List repositories in a group
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-repos --group f-r-r-s --full

# Clone all repos from a group (to organization's local path)
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s

# Clone specific repos only
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s --repos repo1,repo2

# Use different organization
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever list-groups

# Create merge request
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py mr --project 123 \
  --action create --title "My feature" --source feature-branch --target main
```

## File Structure

```
~/.claude-shared-config/skills/gitlab/
├── gitlab_skill.py              # Main skill implementation
├── gitlab_config_setup.py        # Configuration utility
├── gitlab_config.json            # Organization configuration
├── SKILL.md                      # Documentation for Claude
├── README.md                     # Detailed reference
├── SETUP_GUIDE.md               # This file
└── setup-all.sh                 # Quick setup script
```

## Troubleshooting

### "No token found for 'orgname'"

Solution: Configure the token
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure orgname
```

### "Config file not found"

Solution: The config file should be at `~/.claude-shared-config/skills/gitlab/gitlab_config.json`. If it's missing, run setup again.

### Git clone fails with SSH error

Solution: Ensure SSH is set up for GitLab
```bash
# Test SSH connection
ssh -T git@gitlab.prod.origin8cares.com

# If that fails, add your SSH key to GitLab:
# https://gitlab.prod.origin8cares.com/-/user_settings/ssh_keys
```

### Keychain permission denied

If macOS asks for Keychain password, allow the `security` tool. The password is your Mac login password.

## Advanced Configuration

### Change Organization Local Path

Edit `~/.claude-shared-config/skills/gitlab/gitlab_config.json`:

```json
{
  "organizations": {
    "supervisrai": {
      "gitlab_url": "https://gitlab.prod.origin8cares.com",
      "local_path": "/Users/gabrielamyot/Developer/supervisr-ai",  // ← Change this
      "gitlab_group": "supervisr"
    }
  }
}
```

Then reload the configuration (it will be picked up automatically).

### Add New Organization

```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py add \
  new-org \
  "https://gitlab.example.com" \
  "/path/to/local/folder" \
  "gitlab-group-path"
```

### Set Different Default Organization

```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py default klever
```

## Next Steps

- Review `README.md` for detailed command reference
- Try listing repositories: `python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-groups`
- Clone your first batch of repos: `python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s`
- Use with Claude Code: Invoke the skill directly in the Claude interface

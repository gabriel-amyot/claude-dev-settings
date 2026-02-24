# GitLab Skill for Claude Code

Multi-organization GitLab management with secure macOS Keychain token storage.

## Quick Start

### 1. Initial Setup (One-time)

Configure your GitLab credentials for all 3 organizations:

```bash
# Configure each organization (you'll be prompted for your GitLab token)
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure klever
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure origin8
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure supervisrai

# View all configurations
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py list

# (Optional) Set default organization
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py default supervisrai
```

### 2. List Repositories

```bash
# List all groups in default organization
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-groups

# List repos in a specific group
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-repos --group f-r-r-s --full
```

### 3. Clone Repositories

```bash
# Clone all repos from f-r-r-s group to org's configured local path
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s

# Clone specific repos only
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s --repos repo1,repo2,repo3

# Clone to custom directory
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s --output /custom/path
```

## Organization Configuration

### Configured Organizations

- **klever**: `https://gitlab.prod.origin8cares.com`
  - Local path: `/Users/gabrielamyot/Developer/grp-beklever-com`
  - Group: `klever`

- **origin8**: `https://gitlab.prod.origin8cares.com`
  - Local path: `/Users/gabrielamyot/Developer/origin8`
  - Group: `origin8`

- **supervisrai**: `https://gitlab.prod.origin8cares.com`
  - Local path: `/Users/gabrielamyot/Developer/supervisr-ai`
  - Group: `supervisr`

### Token Storage

Tokens are stored securely in **macOS Keychain** under the service `claude-gitlab`. They are never exposed in configuration files or environment variables.

To view/modify a token:
```bash
security find-generic-password -s claude-gitlab -a gitlab_<orgname> -w
```

To delete a token (to reconfigure):
```bash
security delete-generic-password -s claude-gitlab -a gitlab_<orgname>
```

## Available Commands

### List Operations

```bash
# List all groups and subgroups
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-groups

# List projects in a group
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-repos --group GROUP_ID

# Get full details for a repository
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py get-repo PROJECT_PATH --full

# Search for repositories
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py search "query" --max 20
```

### Clone Operations

```bash
# Clone all repos from a group (uses org's local_path)
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group GROUP_ID

# Clone specific repos
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group GROUP_ID --repos repo1,repo2,repo3

# Clone to custom directory
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group GROUP_ID --output /path/to/dir
```

### Merge Request Operations

```bash
# Create a merge request
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py mr --project PROJECT_ID \
  --action create --title "Title" --source feature-branch --target main

# List merge requests
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py mr --project PROJECT_ID --action list

# Approve a merge request
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py mr --project PROJECT_ID \
  --action approve --mr-iid MR_IID
```

## Using with Specific Organization

Add `--org ORGNAME` flag to any command:

```bash
# List repos in Klever organization
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever list-repos --group klever-group

# Clone repos in Origin8 organization
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org origin8 clone --group origin8-group

# Use Supervisr by default (as set in config)
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-groups
```

## Configuration File

Location: `~/.claude-shared-config/skills/gitlab/gitlab_config.json`

```json
{
  "organizations": {
    "klever": {
      "gitlab_url": "https://gitlab.prod.origin8cares.com",
      "local_path": "/Users/gabrielamyot/Developer/grp-beklever-com",
      "gitlab_group": "klever"
    },
    ...
  },
  "default_org": "supervisrai"
}
```

You can edit this file to add new organizations or update paths.

## Setup Utility Commands

### View Configuration

```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py list
```

### Configure Organization Token

```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure ORGNAME
```

### Add New Organization

```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py add ORGNAME URL LOCAL_PATH GITLAB_GROUP
```

### Set Default Organization

```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py default ORGNAME
```

### Get Token (For Debugging)

```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py get-token ORGNAME
```

## Troubleshooting

### Token Not Found

If you get "No token found for 'orgname'":
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure orgname
```

### Keychain Access Issues

The script needs access to your Keychain. If prompted, allow access to `security` in Keychain.

### Git Clone Failures

Ensure you have SSH keys configured for GitLab:
- Generate key: `ssh-keygen -t ed25519 -C "your@email.com"`
- Add to GitLab: Settings → SSH Keys
- Test: `ssh -T git@gitlab.prod.origin8cares.com`

## Files

- `gitlab_skill.py` - Main skill implementation
- `gitlab_config_setup.py` - Configuration setup utility
- `gitlab_config.json` - Organization configuration
- `SKILL.md` - Skill documentation for Claude
- `README.md` - This file

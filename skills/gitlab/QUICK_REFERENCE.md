# GitLab Skill - Quick Reference Card

## ⚡ Quick Commands

### Setup (One-time)
```bash
bash ~/.claude-shared-config/skills/gitlab/setup-all.sh
# OR manually:
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure supervisrai
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure origin8
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure klever
```

### List & Browse
```bash
# All groups in default org
gitlab_skill.py list-groups

# Repos in group
gitlab_skill.py list-repos --group f-r-r-s --full

# Repo details
gitlab_skill.py get-repo f-r-r-s/repo-name --full

# Search repos
gitlab_skill.py search "keyword" --max 20
```

### Clone Repos
```bash
# All repos in group (to org's local_path)
gitlab_skill.py clone --group f-r-r-s

# Specific repos only
gitlab_skill.py clone --group f-r-r-s --repos repo1,repo2,repo3

# Custom output directory
gitlab_skill.py clone --group f-r-r-s --output /custom/path
```

### Merge Requests
```bash
# Create MR
gitlab_skill.py mr --project 123 --action create \
  --title "Feature title" --source feature-branch --target main

# List MRs
gitlab_skill.py mr --project 123 --action list

# Approve MR
gitlab_skill.py mr --project 123 --action approve --mr-iid 45
```

### Organization Switching
```bash
# Use specific org (prefix any command with --org)
gitlab_skill.py --org klever list-groups
gitlab_skill.py --org origin8 list-repos --group origin8-group
gitlab_skill.py --org supervisrai clone --group f-r-r-s
```

## 📋 Organization Reference

| Org | Default Path | Group | URL |
|-----|--------------|-------|-----|
| **supervisrai** | `~/Developer/supervisr-ai` | `supervisr` | `gitlab.prod.origin8cares.com` |
| **origin8** | `~/Developer/origin8` | `origin8` | `gitlab.prod.origin8cares.com` |
| **klever** | `~/Developer/grp-beklever-com` | `klever` | `gitlab.prod.origin8cares.com` |

## 🔐 Token Management

```bash
# Configure token
python3 gitlab_config_setup.py configure ORG

# List all configured orgs
python3 gitlab_config_setup.py list

# Set default org
python3 gitlab_config_setup.py default ORG

# Get token (for debugging)
python3 gitlab_config_setup.py get-token ORG

# Manually view token in Keychain
security find-generic-password -s claude-gitlab -a gitlab_ORG -w

# Delete token (to reconfigure)
security delete-generic-password -s claude-gitlab -a gitlab_ORG
```

## 📁 Directory Structure After Clone

```
~/Developer/supervisr-ai/
├── f-r-r-s/
│   ├── repo1/
│   │   ├── .git/
│   │   └── ...
│   ├── repo2/
│   │   ├── .git/
│   │   └── ...
│   └── repo3/
│       ├── .git/
│       └── ...
└── other-group/
    └── ...
```

## 🚀 Skill Flags

| Flag | Usage | Example |
|------|-------|---------|
| `--org` | Select organization | `--org klever` |
| `--group` | Select group/project | `--group f-r-r-s` |
| `--repos` | Filter repos (comma-sep) | `--repos repo1,repo2` |
| `--output` | Override clone path | `--output /tmp` |
| `--full` | Get full details | `list-repos --full` |
| `--max` | Limit results | `search "api" --max 5` |
| `--all` | Include all (for repos) | `list-repos --all` |

## 📝 Configuration File

Location: `~/.claude-shared-config/skills/gitlab/gitlab_config.json`

```json
{
  "organizations": {
    "supervisrai": {
      "gitlab_url": "https://gitlab.prod.origin8cares.com",
      "local_path": "/Users/gabrielamyot/Developer/supervisr-ai",
      "gitlab_group": "supervisr"
    },
    ...
  },
  "default_org": "supervisrai"
}
```

Edit directly to change paths or add organizations.

## 🆘 Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "No token found" | `python3 gitlab_config_setup.py configure ORG` |
| "Organization not found" | Check `gitlab_config_setup.py list` |
| "SSH permission denied" | Add key: `gitlab.prod.origin8cares.com/-/user_settings/ssh_keys` |
| "Clone timeout" | Try single repo: `--repos repo-name` |
| Keychain error | Use `security` commands directly or reconfigure |

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Claude documentation |
| `README.md` | Detailed reference guide |
| `SETUP_GUIDE.md` | Setup instructions |
| `QUICK_REFERENCE.md` | This quick reference |
| `IMPLEMENTATION_SUMMARY.md` | Technical details |

## 🔗 Useful Links

- GitLab Tokens: https://gitlab.prod.origin8cares.com/-/user_settings/personal_access_tokens
- SSH Keys: https://gitlab.prod.origin8cares.com/-/user_settings/ssh_keys
- Projects: https://gitlab.prod.origin8cares.com/explore/projects

## 💡 Pro Tips

1. **Default to supervisrai**: It's set as default, no `--org` needed
2. **Batch clone**: Clone 10+ repos at once
3. **Update clones**: Auto-pulls if already cloned
4. **Full details**: Use `--full` for more info, but saves tokens (use sparingly)
5. **Custom paths**: Override with `--output` for one-off clones

## 🎯 Common Workflows

### Clone All Project Repos
```bash
gitlab_skill.py clone --group f-r-r-s
```

### List & Filter Repos
```bash
# See what's available
gitlab_skill.py list-repos --group f-r-r-s --full

# Then clone what you want
gitlab_skill.py clone --group f-r-r-s --repos repo1,repo2
```

### Switch Between Orgs
```bash
# Klever work
gitlab_skill.py --org klever clone --group klever-group

# Origin8 work
gitlab_skill.py --org origin8 clone --group origin8-group

# Back to supervisrai (default)
gitlab_skill.py clone --group f-r-r-s
```

### Create & Approve MR
```bash
# Create
gitlab_skill.py mr --project 123 --action create \
  --title "My feature" --source feature-branch --target main

# Review & Approve (get the iid from list)
gitlab_skill.py mr --project 123 --action list
gitlab_skill.py mr --project 123 --action approve --mr-iid 42
```

## ✅ Verification

Test your setup:
```bash
# Should show groups
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-groups

# Should show repos
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-repos --group f-r-r-s

# Should clone successfully
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s --repos test-repo
```

---

**For detailed info**: See `README.md` or `SETUP_GUIDE.md`

---
name: pre-flight
description: "Universal infrastructure pre-flight checks. Validates repo cleanliness, Docker health, credential freshness, disk space, network reachability, and agent definition well-formedness. Severity levels can be overridden by crawl profiles."
---

# /pre-flight

Universal pre-flight checks before any crawl or autonomous session. Catches infrastructure issues before tokens are consumed.

## Usage

```
/pre-flight [--profile <crawl-profile-name>]
```

If `--profile` is provided, read `~/.claude/crawl-profiles/{profile}.yaml` for severity overrides and environment context. Otherwise use defaults.

## Environment-Aware Checks

Each crawl profile declares an `environment` field (`local`, `rnd`, `dev`) that drives which infrastructure is critical:

| Harness Profile | Docker | GCP | GitLab | Verification |
|-----------------|--------|-----|--------|--------------|
| `local-harness` | FATAL  | WARN | WARN  | `supervisr-test.sh --env local` |
| `rnd-harness`   | WARN   | FATAL | WARN | `supervisr-test.sh --env rnd` |
| `dev-harness`   | WARN   | FATAL | FATAL | `supervisr-test.sh --env dev` |

The profile's `severity_overrides` section encodes these. When no profile is given, all checks default to WARN except Docker (FATAL).

## Checks

Run ALL checks. Collect all results before presenting. Do NOT stop at first failure.

### Check 1: Repo Cleanliness
For each repo in scope (from REPO_MAPPING.yaml or explicit list):
1. `git status` for uncommitted changes
2. `git stash list` for stale stashes
- **Default severity:** WARN
- **Action:** List dirty files. Suggest: stash, commit, or continue.

### Check 2: Docker Health
1. `docker info` — is daemon running?
2. `docker compose ps` (if compose file exists) — stale containers?
3. Check common ports (4010, 8080, 8081, 5432) for conflicts: `lsof -i :{port} -t`
- **Default severity:** FATAL
- **Action on FATAL:** Show error. Suggest: `docker compose down -v` or `kill {pid}`.

### Check 3: Credential Freshness
1. GCP: `gcloud auth print-identity-token --quiet` — valid token?
2. GitLab: Credentials are stored in macOS Keychain (via `git config credential.helper` = `osxkeychain`) and the `/gitlab` skill's Python Keychain config. Test with: `python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py list` (shows configured orgs). For push access, `git ls-remote` against a known repo is the real test.
3. Jira: Managed by the `/jira` skill. Check with: `python3 ~/.claude-shared-config/skills/jira/*.py` or just attempt a Jira API call.
- **Default severity:** WARN
- **Action:** List stale/missing credentials. For GCP: `gcloud auth login`. For GitLab: `python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure {org}`. For Jira: re-run `/jira` setup.

### Check 4: Disk Space
1. `df -h .` — available space on current volume
- **Default severity:** WARN if < 5GB, FATAL if < 1GB
- **Action:** Show available space. Suggest: `docker system prune`, clear build caches.

### Check 5: Network Reachability
1. GitLab: check the org-appropriate instance (read `~/.claude-shared-config/skills/gitlab/gitlab_config.json` for the `gitlab_url` of the detected org):
   - Supervisr/Origin8: `curl -sf -o /dev/null -w "%{http_code}" --max-time 5 https://gitlab.prod.origin8cares.com`
   - Klever: `curl -sf -o /dev/null -w "%{http_code}" --max-time 5 https://cicd.prod.datasophia.com` (IAP-protected — a 302 or 200 both mean reachable; 000/timeout means unreachable)
2. Jira: `curl -sf -o /dev/null -w "%{http_code}" --max-time 5 https://{jira-domain}/rest/api/2/serverInfo`
3. GCP APIs: `curl -sf -o /dev/null -w "%{http_code}" --max-time 5 https://run.googleapis.com/`
- **Default severity:** WARN (feeds into fallback matrix)
- **Action:** List unreachable services. Note these for the fallback matrix.

### Check 6: Agent Definition Well-formedness
If a specific agent is named:
1. File exists at `~/.claude/agents/{name}.md` or `~/.claude-shared-config/agents/{name}.md`
2. Has valid YAML frontmatter with: name, description, tools, model
3. Has a "Responsibility Boundary" section (if orchestrator)
- **Default severity:** FAIL if agent file missing, WARN if frontmatter incomplete

## Severity Override System

When `--profile` is provided, read the profile's `severity_overrides` section:
```yaml
severity_overrides:
  docker_health: FATAL
  gitlab_reachable: WARN
  gcp_reachable: WARN
```
Profile overrides take precedence over defaults.

## Output Format

```
Pre-Flight Report
Date: {YYYY-MM-DD HH:MM}
Profile: {profile-name or "default"}

| # | Check              | Status    | Severity | Notes |
|---|--------------------|-----------|----------|-------|
| 1 | Repo cleanliness   | PASS/WARN | ...      | ...   |
| 2 | Docker health      | PASS/FAIL | ...      | ...   |
| 3 | Credentials        | PASS/WARN | ...      | ...   |
| 4 | Disk space         | PASS/WARN | ...      | ...   |
| 5 | Network            | PASS/WARN | ...      | ...   |
| 6 | Agent definitions  | PASS/WARN | ...      | ...   |

Overall: READY / READY WITH WARNINGS / NOT READY

Network status (feeds into fallback matrix):
- GitLab: reachable/unreachable
- Jira: reachable/unreachable
- GCP: reachable/unreachable
```

## Decision Gate

- **Any FATAL:** Do NOT proceed. Show what needs fixing.
- **WARN only:** Proceed. Unreachable services trigger fallback matrix entries.
- **All PASS:** Green light.

## Integration Points

- `ralph-loop-preflight` delegates universal checks here, adds profile-specific validation
- Crawl profiles declare which checks are FATAL vs WARN for their goals
- Fallback matrix (failure-catalog.yaml) receives network reachability results

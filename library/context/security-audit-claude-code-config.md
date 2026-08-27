# Security Audit: Claude Code Configuration

**Date:** 2026-04-01
**Scope:** User-level (`~/.claude/`) and org-level (`~/Developer/grp-beklever-com/`) Claude Code configuration
**Status:** Findings documented. Fixes deferred until after sprint (ends 2026-04-02).

---

## Reconciled Priority List (Critical first, then ease)

| Priority | Problem | Severity | Ease | Action |
|----------|---------|----------|------|--------|
| **P0** | Enable file protection flag | CRITICAL | 30 sec | `touch ~/.claude/hooks/.protection-enabled` |
| **P0** | Change default from `bypassPermissions` | CRITICAL | 30 sec | Edit `~/.claude/settings.json`: `"defaultMode": "default"` |
| **P0** | Disable `skipDangerousModePermissionPrompt` | CRITICAL | 30 sec | Set to `false` in settings.json |
| **P1** | Fix `~/.zshenv` permissions | CRITICAL | 10 sec | `chmod 600 ~/.zshenv` |
| **P1** | Rotate Jira API token | CRITICAL | 5 min | Token was world-readable. Must rotate even after chmod. |
| **P1** | Fix `~/.ssh/key_sftp.pem` permissions | HIGH | 10 sec | `chmod 600 ~/.ssh/key_sftp.pem` |
| **P2** | Move tokens from `.zshenv` to macOS Keychain | CRITICAL | 30 min | Eliminates plaintext credential storage. Update jira_skill.py to read from keychain. |
| **P2** | Pin status line package version | MEDIUM | 1 min | Replace `ccstatusline@latest` with pinned version in settings.json |
| **P2** | Reduce GitHub token scope (remove `workflow`) | HIGH | 5 min | Regenerate PAT without `workflow` scope |
| **P3** | Add hard gate for outbound MCP calls | HIGH | Hours | Build hook/wrapper to gate `slack_send_message`, `gmail_create_draft`, etc. |
| **P3** | Add Jira content sanitization for agents | HIGH | Hours | Pre-processing layer between Jira fetch and agent context |
| **P3** | Audit all CLAUDE.md files across repos | HIGH | 1-2 hrs | Scripted review to establish clean baseline |

---

## Top 10 Worst Problems (by severity)

### 1. PLAINTEXT API TOKENS IN WORLD-READABLE FILE
- **File:** `~/.zshenv` (permissions: `-rw-r--r--`)
- **Exposed:** Jira API token (full access to beklever.atlassian.net), Mapbox secret key
- **Impact:** Any process or user on the machine can read these tokens

### 2. `bypassPermissions` IS THE GLOBAL DEFAULT
- **File:** `~/.claude/settings.json`
- **Combined with:** `skipDangerousModePermissionPrompt: true`
- **Impact:** Any agent or prompt injection executes ANY command without human gates

### 3. CLAUDE.md PROMPT INJECTION VIA MALICIOUS PR
- **Mechanism:** All `CLAUDE.md` files auto-loaded as system context
- **Impact:** A malicious PR modifying a repo's CLAUDE.md injects instructions that execute automatically. Combined with bypassPermissions, no gate stops it.

### 4. FILE PROTECTION IS DISABLED
- **File:** `~/.claude-shared-config/hooks/file-guard.sh` exists but flag `~/.claude/hooks/.protection-enabled` DOES NOT EXIST
- **Impact:** Agents can autonomously modify CLAUDE.md, settings.json, agent-os/sbe/ specs

### 5. AUTONOMOUS AGENTS HAVE UNRESTRICTED ACCESS
- **Agents:** night-crawl, dev-crawl, supervisr-autopilot, ralph-loop
- **Impact:** Overnight crawl hits prompt injection in Jira ticket, autonomously commits malicious code, deploys it, posts "success" to Jira

### 6. DIRECT DATA EXFILTRATION PATHS (NO HARD GATE)
- **Tools:** `slack_send_message`, `gmail_create_draft`, Jira API, GitHub PR comments
- **Guard:** `/post-comment` is soft convention. Direct MCP calls bypass it.
- **Impact:** Prompt-injected agent sends credentials or source code externally

### 7. JIRA TICKET DESCRIPTION INJECTION
- **Mechanism:** Agents fetch Jira descriptions and process as context/instructions
- **Impact:** Malicious ticket description triggers destructive agent actions

### 8. STATUS LINE RUNS `npx -y ccstatusline@latest`
- **File:** `~/.claude/settings.json`
- **Impact:** npm package takeover executes arbitrary code on every session. No pinning, no checksum.

### 9. SSH KEY WORLD-READABLE
- **File:** `~/.ssh/key_sftp.pem` (permissions: `-rwxr--r--`)
- **Impact:** Any process reads the key, gains SFTP infrastructure access

### 10. GITHUB TOKEN HAS `workflow` SCOPE
- **Impact:** Compromised agent can modify GitHub Actions workflows, inject CI/CD attacks with repo secrets access

---

## Top 10 Easiest Fixes

1. **Enable file protection** (30 sec): `touch ~/.claude/hooks/.protection-enabled`
2. **Fix SSH key permissions** (10 sec): `chmod 600 ~/.ssh/key_sftp.pem`
3. **Fix `.zshenv` permissions** (10 sec): `chmod 600 ~/.zshenv`
4. **Pin status line package** (1 min): Replace `@latest` with pinned version
5. **Disable `skipDangerousModePermissionPrompt`** (30 sec): Set `false` in settings.json
6. **Move tokens to Keychain** (15-30 min): `security add-generic-password` + update skill scripts
7. **Reduce GitHub token scope** (5 min): Regenerate PAT without `workflow`
8. **Change default permission mode** (30 sec): `"defaultMode": "default"` in settings.json
9. **Rotate Jira API token** (5 min): Generate new one at Atlassian
10. **Add credential patterns to global gitignore** (2 min): `.zshenv`, `*.token`, `*.secret`, `*.pem`

---

## Key Insight

The single most dangerous combination: **`bypassPermissions` + disabled file protection + CLAUDE.md auto-loading**. This creates a complete attack chain where a malicious PR can inject system-level instructions that execute with zero human gates. The P0 fixes (3 commands, under 2 minutes) break this chain.

## Out of Scope
- Individual repo `.env` files and secrets
- GCP IAM policies and service account keys
- Network-level security
- macOS system security settings
- Individual MCP server OAuth token scopes

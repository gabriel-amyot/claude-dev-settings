# Git IAP Push Troubleshooting

## Issue: `Device not configured` when pushing to IAP-protected GitLab

**Error:**
```
fatal: could not read Password for 'https://user@cicd.prod.datasophia.com': Device not configured
```

**Root cause:** The remote uses `https+iap://` (Identity-Aware Proxy) authentication. Git is configured to use IAP cookies for authentication, but the credential helper cannot prompt for a TTY in a headless/subprocess context (e.g., when invoked from Claude Code or a script).

## Solution

Push manually from your local terminal (which has a TTY):
```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-user-management
git push origin KTP-182
```

Or whichever branch you're on.

## Why This Happens

- The remote is configured with `protocol.https+iap` and cookie-based auth via `~/.config/git-gcp-iap/`
- The git config references credentials stored in macOS Keychain
- When git tries to authenticate, it attempts to use the credential helper (`osxkeychain`)
- The credential helper needs a TTY to interact with the keychain or prompt for a password
- Claude Code (and subprocess contexts generally) don't provide a TTY
- Git fails with "Device not configured"

## Verification

Check if the IAP cookie file exists and is fresh:
```bash
ls -la ~/.config/git-gcp-iap/gamyot-beklever@cicd.prod.datasophia.com.cookie
cat ~/.config/git-gcp-iap/gamyot-beklever@cicd.prod.datasophia.com.cookie | head -1
```

The cookie file is a Netscape-format cookie file. The last column of each line is the expiration timestamp (seconds since epoch). If it's in the past, the cookie has expired and you need to re-authenticate.

## Prevention

This is a known limitation of IAP-based git auth. There is no automated fix from Claude Code. The workaround is always to push manually from a terminal with a TTY.

## Related

- Applies to all repos under `grp-cst/grp-beklever-com/` on `cicd.prod.datasophia.com`
- Does not affect `gitlab.prod.origin8cares.com` (Supervisr repos)

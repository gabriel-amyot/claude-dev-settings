# Failure Patterns Reference

Known infrastructure failure patterns for BLOCKED_EXTERNAL detection. Each entry includes: error signatures, classification, typical duration, and recommended action.

Classifications:
- `transient` — Usually resolves within minutes. Allow up to 3 retries before escalating.
- `persistent-session` — Lasts the session. Requires human action but may be fixable today.
- `persistent-nightly` — Predictable window, resolves on its own. Wait it out.
- `persistent-indefinite` — No known self-resolution. Requires human intervention.

---

## Pattern: Registry Outage (Datasophia)

**Pattern name:** `REGISTRY_OUTAGE`
**Classification:** `persistent-nightly`

**Error signatures (any of these):**
```
Error accessing remote module registry: cicd.prod.datasophia.com
Failed to query available provider packages: cicd.prod.datasophia.com
Error: Failed to install provider: registry cicd.prod.datasophia.com is unavailable
dial tcp: lookup cicd.prod.datasophia.com: no such host
connection refused: cicd.prod.datasophia.com
```

**Detection regex:**
```
cicd\.prod\.datasophia\.com.*(unavailable|refused|no such host|Error accessing)
```

**Typical duration:** 11 PM to 5 AM ET (approximately 6 hours, nightly)

**When it appears:** DAC Terraform pipeline runs that reference remote module registry. Affects all DAC repos (grp-dac/* path).

**Recommended action:**
- If current time is between 11 PM and 5 AM ET: exit immediately. Schedule retry after 5 AM ET.
- If current time is outside that window: check https://cicd.prod.datasophia.com (if accessible) for status. May be an unplanned outage.

**Never do:** Retry in a loop. Each pipeline trigger pollutes history and burns tokens with zero chance of success during the outage window.

---

## Pattern: Network Timeout (Generic)

**Pattern name:** `NETWORK_TIMEOUT`
**Classification:** `transient` (if <3 failures) or `persistent-session` (if 3+ consecutive)

**Error signatures (any of these):**
```
connect: connection timed out
i/o timeout
context deadline exceeded
net/http: request canceled
EOF
TLS handshake timeout
dial tcp ... connect: connection timed out
```

**Detection regex:**
```
(connection timed out|i/o timeout|deadline exceeded|request canceled|TLS handshake timeout)
```

**Typical duration:** Seconds to minutes if transient. Hours if persistent (network partition, DNS issue).

**Transient vs persistent:**
- First or second occurrence on different operations: likely transient. Continue.
- Third consecutive occurrence on the same operation: likely persistent. Declare BLOCKED_EXTERNAL.
- Occurrence on multiple different endpoints simultaneously: network partition. Declare immediately.

**Recommended action:**
- Transient: wait 30 seconds, retry once.
- Persistent: check if other network operations succeed. If nothing reaches external services, network is down. Exit.

---

## Pattern: Build Infrastructure (Docker, Maven, npm)

**Pattern name:** `BUILD_INFRA`
**Classification:** `persistent-session` (typically)

### Docker Daemon

**Error signatures:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
Error response from daemon: driver failed programming external connectivity
docker: Error response from daemon
Error: No such container
```

**Detection regex:**
```
(Cannot connect to the Docker daemon|Error response from daemon|docker.*Error)
```

**Recommended action:** Docker daemon is not running or crashed. Requires human restart (`sudo systemctl restart docker` or Docker Desktop restart). Cannot be fixed from within an agent session.

### Maven Repository

**Error signatures:**
```
Could not resolve dependencies for project
Could not transfer artifact
ArtifactTransferException
Could not GET https://repo1.maven.org
```

**Detection regex:**
```
(Could not resolve dependencies|Could not transfer artifact|ArtifactTransferException)
```

**Recommended action:** Central Maven repo may be unavailable, or the artifact version does not exist. Check version number first (agent error vs infra error). If version is correct and central is reachable manually, wait and retry once. If 3 consecutive failures: declare BLOCKED_EXTERNAL.

### npm Registry

**Error signatures:**
```
npm ERR! network request to https://registry.npmjs.org failed
npm ERR! code ENOTFOUND
npm ERR! errno ECONNREFUSED
```

**Detection regex:**
```
npm ERR!.*(network request|ENOTFOUND|ECONNREFUSED|registry)
```

**Recommended action:** npmjs.org outage or network issue. Check https://status.npmjs.org. If npmjs is up and failures persist, may be a local DNS or proxy issue. Declare BLOCKED_EXTERNAL after 3 consecutive failures.

---

## Pattern: Auth / Credential Expiry

**Pattern name:** `AUTH_EXPIRY`
**Classification:** `persistent-session`

### Auth0 M2M Token

**Error signatures:**
```
401 Unauthorized
{"error":"unauthorized","error_description":"..."}
invalid_token
token is expired
JWT expired at
```

**Detection regex:**
```
(401 Unauthorized|invalid_token|token is expired|JWT expired)
```

**Transient handling:** On a first 401, attempt to clear the M2M token cache and re-fetch. If the re-fetched token also produces 401 on the next call, this is a credential issue, not a cache issue.

**Recommended action (after cache-clear retry fails):**
- Rotate the Auth0 M2M client secret via the Auth0 Management Console.
- Update the relevant CI/CD variable (e.g., `TF_VAR_m2m_secret` in the DAC repo, or the service's local `.env`).
- This requires human action. Declare BLOCKED_EXTERNAL with blocker type `AUTH_EXPIRY`.

### GitLab Personal Access Token

**Error signatures:**
```
remote: HTTP Basic: Access denied
fatal: Authentication failed for
403 Forbidden
{"message":"401 Unauthorized"}
```

**Detection regex:**
```
(HTTP Basic: Access denied|Authentication failed for|401 Unauthorized.*gitlab)
```

**Recommended action:** GitLab PAT has expired or been revoked. Requires human to rotate the token in GitLab User Settings and update the keychain entry (`claude-gitlab` service) or environment variable. Declare BLOCKED_EXTERNAL.

---

## Pattern: Cloud Run Deployment Failures

**Pattern name:** `CLOUD_RUN_DEPLOY`
**Classification:** `transient` (quota) or `persistent-indefinite` (image missing)

### Image Pull Failure

**Error signatures:**
```
Failed to create pod sandbox
Failed to pull image
ImagePullBackOff
ErrImagePull
manifest unknown: manifest unknown
```

**Detection regex:**
```
(Failed to pull image|ImagePullBackOff|ErrImagePull|manifest unknown)
```

**Cause:** The image tag referenced in the deployment does not exist in the registry. Common when a CI/CD build failed upstream but the deployment was triggered anyway.

**Recommended action:** Verify the image tag exists in the GCR registry before retrying the deployment. If the tag is missing, the upstream build must succeed first. Check the build pipeline for the service, not the deploy pipeline.

### Cloud Run Quota

**Error signatures:**
```
RESOURCE_EXHAUSTED
Quota exceeded for quota metric
googleapi: Error 429
```

**Detection regex:**
```
(RESOURCE_EXHAUSTED|Quota exceeded|Error 429.*google)
```

**Recommended action:** GCP quota limit hit. Escalate to human. Quotas reset on a billing cycle or can be increased via GCP Console > IAM & Admin > Quotas. Agent cannot fix quota limits.

### IAM / Permission Denied on Deploy

**Error signatures:**
```
PERMISSION_DENIED: Permission denied on resource
403
caller does not have permission
```

**Detection regex:**
```
(PERMISSION_DENIED|caller does not have permission|403.*gcp|403.*google)
```

**Important:** IAM changes require human gate per CLAUDE.md. Do NOT attempt to fix permission errors by modifying IAM bindings autonomously. Declare BLOCKED_EXTERNAL and escalate.

**Recommended action:** Surface the exact permission error and the service account involved to the user. Do not attempt any `gcloud iam` commands to resolve it.

---

## Pattern: Terraform State Lock

**Pattern name:** `TF_STATE_LOCK`
**Classification:** `persistent-session`

**Error signatures:**
```
Error locking state: Error acquiring the state lock
state file is locked
Lock Info:
  ID: ...
  Operation: OperationTypePlan
```

**Detection regex:**
```
(Error locking state|state file is locked|Error acquiring the state lock)
```

**Cause:** A previous Terraform run was interrupted without releasing the state lock. The lock persists in GCS.

**Recommended action:** Requires human to run `terraform force-unlock {LOCK-ID}` after verifying no other Terraform process is actively running. Agent must NOT run `force-unlock` autonomously. Declare BLOCKED_EXTERNAL and provide the Lock ID from the error message.

---

## Quick Classification Lookup

| Error contains | Pattern | Classification | Declare at |
|----------------|---------|---------------|------------|
| `cicd.prod.datasophia.com` | `REGISTRY_OUTAGE` | persistent-nightly | Immediately if 11PM-5AM ET, else 3rd failure |
| `connection timed out` | `NETWORK_TIMEOUT` | transient/persistent | 3rd consecutive identical |
| `Cannot connect to the Docker daemon` | `BUILD_INFRA` | persistent-session | Immediately |
| `Could not resolve dependencies` | `BUILD_INFRA` | transient/persistent | 3rd consecutive |
| `npm ERR! network` | `BUILD_INFRA` | transient/persistent | 3rd consecutive |
| `401 Unauthorized` + re-fetch failed | `AUTH_EXPIRY` | persistent-session | After 1 re-fetch attempt |
| `Authentication failed` + GitLab | `AUTH_EXPIRY` | persistent-session | Immediately |
| `ImagePullBackOff` | `CLOUD_RUN_DEPLOY` | persistent-indefinite | Immediately |
| `RESOURCE_EXHAUSTED` | `CLOUD_RUN_DEPLOY` | persistent-indefinite | Immediately |
| `PERMISSION_DENIED` | `CLOUD_RUN_DEPLOY` | persistent-indefinite | Immediately |
| `Error locking state` | `TF_STATE_LOCK` | persistent-session | Immediately |

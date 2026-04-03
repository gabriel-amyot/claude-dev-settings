# Supervisr Service Graph and Deployment

Service topology, DAC mappings, and deployment workflow reference.

## Service Graph

```
                    ┌──────────────┐
                    │ web-dashboard│
                    │  (Angular)   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
          ┌────────│   gateway     │────────┐
          │        │(Apollo Router)│        │
          │        └──────┬───────┘        │
          │               │                │
    ┌─────▼─────┐  ┌──────▼──────┐  ┌─────▼─────┐
    │    LLS    │  │    EQS      │  │    PEW    │
    │lead-life- │  │ query-svc   │  │ pipeline  │
    │  cycle    │  │ (read-only) │  │ event wtr │
    └─┬───┬───┬─┘  └─────────────┘  └─────┬────┘
      │   │   │                            │
      │   │   └────────────┐               │
      │   │                │               │
    ┌─▼───▼──┐    ┌────────▼───────┐  ┌────▼────┐
    │retell- │    │ compliance-ers │  │complianc│
    │service │    │  (event bus)   │  │e-engine │
    └────────┘    └────────────────┘  └─────────┘
```

### Service Responsibilities

| Service | Role | GCP Project |
|---------|------|-------------|
| `lead-lifecycle-service` (LLS) | Lead state machine, call orchestration, tick scheduling | core |
| `retell-service` | Retell AI integration, webhook receiver, availability check | core |
| `compliance-ers` (ERS) | Event bus, Datastore persistence, materialized view sync | core |
| `supervisor-query-service` (EQS) | Read-only GraphQL queries over compliance MV store | core |
| `supervisor-compliance-engine` | Transcript analysis, disposition tagging (Python/FastAPI) | core |
| `gateway-service` | Apollo Router federated GraphQL gateway | core |
| `pew` | Pipeline Event Writer, compliance pipeline orchestrator | core |
| `auth0-manager` | Auth0 tenant management, M2M token cache (Firestore) | core |
| `web-dashboard` | Angular SPA served by nginx | core |
| `web-site` | Static marketing site | core |

### Data Flow: Lead Pipeline

```
Lead Ingestion → LLS → Retell AI (call) → retell-service (webhook)
  → LLS (disposition) → ERS (event + MV write) → EQS (read)
```

### Ownership

LLS owns the lead entity contract end-to-end. ERS and EQS serve it. Pipeline type mismatches or data contract issues are the responsibility of whoever owns the pipeline (currently SPV-3 scope), not separate tickets for Dan.

## DAC Repo Mappings

Infrastructure-as-code repos that deploy each service via Terraform to Cloud Run.

| Service | DAC Repo |
|---------|----------|
| `lead-lifecycle-service` | `dac-sprvsr-core-lead-lifecycle` |
| `retell-service` | `dac-sprvsr-core-retell-service` |
| `supervisor-compliance-engine` | `dac-sprvsr-core-compliance-engine` |
| `auth0-manager` | `dac-sprvsr-core-auth0-manager` |
| `supervisor-query-service` | `dac-sprvsr-core-eqs` |
| `gateway-service` | `dac-sprvsr-core-gateway-service` |
| `pew` | `dac-sprvsr-core-pew` |
| `web-dashboard` | `dac-sprvsr-core-web-dashboard` |
| `compliance-ers` | `dac-sprvsr-core-web-ers` |
| `web-site` | `dac-sprvsr-core-web-site` |

**DAC base path:** `faas/grp-dac/grp-dac-sprvsr/grp-dac-sprvsr-core/`
**IAC shared:** `faas/grp-iac/grp-iac-sprvsr/iac-sprvsr-core`

## Deployment Workflow

### Full Deploy Sequence (per service)

1. Commit and tag the service repo (e.g., `0.0.27-dev`)
2. Push commit + tag to GitHub
3. JIB builds and pushes image to Artifact Registry (GitLab CI/CD)
4. Update DAC CI/CD variable:
   ```bash
   python3 ~/.claude/skills/gitlab/gitlab_skill.py vars <DAC_PROJECT> \
     --action set --key TF_VAR_image_tag --value 0.0.27-dev --scope dev
   ```
5. Trigger DAC pipeline:
   ```bash
   python3 ~/.claude/skills/gitlab/gitlab_skill.py pipeline <DAC_PROJECT> --ref dev
   ```

### Tag Versioning

- Format: `x.y.z-dev` (dev/untested) or `x.y.z` (prod-ready)
- Default: always tag `-dev`. Increment patch from last tag.
- Prod promotion: drop `-dev` suffix. Same patch number. Rare.
- No tags yet: start at `0.0.1-dev`

### Key Details

- **CI/CD variable name:** `TF_VAR_image_tag` (not `image_tag`). Terraform `TF_VAR_` prefix convention.
- **GitLab token:** keychain service `claude-gitlab`, account `gitlab_supervisrai`. Resolved automatically by `gitlab_skill.py`.
- **DAC project IDs:** `~/.claude/skills/gitlab/dac_index.json`
- **Image build:** JIB Maven plugin. Command: `mvn compile jib:build -Djib.to.tags=X.Y.Z-dev -DskipTests`
- **Git tag and image tag must match.** e.g., git tag `0.0.6-dev` → image `service-name:0.0.6-dev`

### Pre-tag Checklist (mandatory)

1. Detect primary branch: `git symbolic-ref refs/remotes/origin/HEAD`
2. `git fetch origin`
3. `git rebase origin/{primary-branch}` (abort on conflicts)
4. Get latest tag: `git tag --sort=-v:refname | head -1`
5. Create new tag

## Partner Context

### Clarifying (First Real Partner)

- **organizationId:** `clarifying`
- **Historical calls:** ~35,860 outbound via Retell AI agent `agent_5260f09ec36fa37fe039c02f91`
- **Lead grouping key:** phone number
- **Processing rule:** Same phone → sequential (chronological). Different phones → parallel.
- **3 lead seller apps** in Auth0 (see auth0-topology doc)

# Identity contract: image, reach, receipt

`probe.sh` proves the **branch**. It does not prove which **image** serves, whether a **route**
is reachable, or whether a **rollout** landed. A correct branch stamp still let a wrong prod
diagnosis through: a `*-prod.properties` file on `origin/dev` declared a setting that the prod
image (built from an older `main`) did not contain.

Use this contract when the claim rests on more than the branch:

| Claim shape | Section to fill |
|---|---|
| "prod does X", and X lives in a file inside the image (Spring profile, bundled config, constant, resource) | `image` |
| "this route is live / not live in <env>", "why 404 in prod but not dev" | `image` + `reach` |
| "the snapshot / fix is deployed in <env>", a readiness claim after a rollout | `image` + `receipt` |

Do not run `reach` for every code citation. The branch probe stays the default.

## Procedure

1. Collect read-only evidence. Every item carries the exact command you ran in `evidence`.
2. Write it to one JSON file in the ticket folder (never in a service repo).
3. Run `python3 ~/.claude/skills/deploy-identity/scripts/identity_contract.py <file>`.
4. Obey the output. Attach the `image.stamp` to every claim that leaves your context.

The script never reads a live system. It applies fixed rules, so the verdict is an output of the
evidence. An item with no `evidence` command is UNVERIFIED, whatever state you wrote.

## Evidence schema

```json
{
  "service": "<service>", "env": "prod",
  "image": {
    "intended":      {"version": "0.11.0", "evidence": "<DAC CI variable read, env-scoped>"},
    "serving":       {"version": "0.11.0", "revision": "<rev>", "digest": "sha256:…",
                      "traffic_percent": 100, "evidence": "<runtime describe command>"},
    "source_commit": {"ref": "main@2e38022", "evidence": "<git rev-parse <tag>>"},
    "branch_tip":    {"ref": "dev@abc1234"}
  },
  "reach": {
    "layers": [
      {"name": "gateway", "state": "ARMED|GAP", "kind": "live|config", "evidence": "…", "detail": "…"}
    ],
    "request": {"result": "PASS|FAIL", "evidence": "<bounded authenticated request + log line>"}
  },
  "receipt": {
    "expected": {"image": "0.21.3"},
    "stages": [{"name": "source_review|build|dac_validate|dac_plan|dac_apply",
                "result": "success|failed|running|manual|…", "config_dir": "<for dac_validate>",
                "evidence": "<job id / URL>"}],
    "undeployed_fixes": ["<reviewed change not in the serving image>"],
    "acceptance": [{"name": "browser", "result": "PASS", "evidence": "…"}]
  }
}
```

## Rules the script enforces

**Image.**
- A DAC variable is intended configuration, not runtime truth. With no serving read, the result is
  `INTENDED_ONLY` and the stamp says so.
- Read the variable per environment scope. The default scope is not meaningful.
- A tag can move. `VERIFIED` needs a serving revision or digest, plus a mapped source commit.
- A traffic split is `SPLIT`. Name every serving revision in the claim.
- Intended differs from serving: `MISMATCH`. Name both. The gap is usually the finding.
- When the branch tip differs from the deployed commit, read files at the deployed commit
  (`git show <tag>:<path>`), never at the tip or in the working tree.

**Reach.** One row per layer. Typical layers: gateway contract, caller admission, scope grant,
environment config, deployed handler, DAC branch currency, apply state.
- `kind: config` (terraform, a contract file) gives `CONFIGURED`, not `ARMED`. Terraform grants
  are not proof of live entitlement.
- A handler present at the deployed tag does not prove it executes. Only a bounded authenticated
  `request` with a matching service log line gives `REACHABLE`.
- Any unreadable layer gives `UNPROVEN`. The script refuses a verdict rather than assume ARMED.
- A `GAP` row with a passing request gives `CONFLICT`. Re-read both.

**Apply state.** Do not assume a manual apply gate. A bridge-triggered DAC pipeline can run its
`apply` job unattended (observed 2026-10-22). Read the apply job's status directly and record it as
a stage. Merged is not applied, and planned is not applied.

**Receipt.** Source review, build, DAC plan and DAC apply are separate stages. A missing stage is
reported, not assumed. A `dac_validate` with an empty configuration directory is not a PASS.
Identity is not acceptance: browser, vendor and Slack checks stay `UNRUN` until their own evidence
passes. List reviewed fixes that are not in the serving image separately.

## Read-only collection hints

- Cloud Run env vars: read through the v2 REST API. `gcloud run services describe` (v1) omits
  empty-string values, so a variable set to `""` looks absent.
- A terraform plan's env-block diff becomes unreadable once one block is sensitive. Compare the
  variable names the module produces with the live service, not the diff text.
- An app pipeline's `deploy in <env>` job is often a bridge. Follow it into the downstream DAC
  pipeline and read that pipeline's apply job.
- After an apply, check readiness on every service the apply touched, not only the target.

This contract never triggers a deploy, cancels a pipeline, or presses a job. Those stay under the
user's explicit authority.

## Org knowledge (cite, do not copy)

Klever repo IDs, DAC variable names, hosts and per-service topology live in the Klever
bibliothèque, not here:
- `documentation/bibliotheque/sops/dac-workflow-patterns.md` (apply jobs, the multi-press pattern
  and its collapse)
- `documentation/bibliotheque/stack/ci-cd/gitlab-ci-patterns.md` (a prod env var is inert without
  the code path)
- `documentation/bibliotheque/stack/dac-cos-mig-deployment-conventions.md` (COS-MIG image identity)

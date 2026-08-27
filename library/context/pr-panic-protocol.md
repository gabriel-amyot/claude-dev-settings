# PR Panic Protocol — When Gabriel Freaks Out About a PR

On-demand context: load when user expresses concern, alarm, or PTSD about a pull request, commit, or branch (contamination fears, security, data loss, harness pollution, etc.).

## Trigger phrases
- "I got the chills", "PTSD from last session", "what the fuck is that"
- "Did you adversely review it", "is this safe", "I'm worried about X"
- Any emotional language attached to a specific PR name, branch name, or file name

## The Three-Lookup Rule

**Never declare verdict from PR diff alone.** Every PR-panic investigation requires THREE lookups, in parallel:

1. **What the PR changes** — `git diff origin/main...origin/{branch} --stat` + targeted file diffs for suspect keywords
2. **What main already looks like** — `git grep -n "{keyword}" origin/main -- 'src/main/**'` to find pre-existing state
3. **When the pre-existing state landed** — `git log --oneline origin/main -- {suspect_file}` to find historical context (often predates the panic)

Only after all three: report ground truth to the user with evidence (file paths, commit hashes, line references).

## Branch Names Lie

Branch names are not truth. Examples from 2026-04-13 SPV-92 batch:
- `SPV-99-pubsub-emulator-harness` → actual change was PubSub emulator push subscriptions. The emulator works in both `local` and `harness` profiles, it is NOT harness-specific. Branch name was misleading.
- `SPV-100-gatewayauth-profile-split` → actual change was a refactor of pre-existing SPV-3 harness coupling into cleaner Spring `@Profile` idioms. Did NOT introduce new harness coupling, only made existing coupling more visible.

**Rule:** Read the diff, not the branch name. Report what the code actually does.

## Pre-existing Contamination is Not This PR's Fault

When investigating contamination fears, always check main's current state FIRST before accusing a PR. If the contamination already exists in main:
- Report it as pre-existing (with the originating commit hash if findable)
- Distinguish "this PR introduces X" from "this PR makes X more visible but doesn't add new coupling"
- Propose a SEPARATE ticket to clean up pre-existing contamination rather than blocking the current batch
- The current PR batch deserves to ship or be blocked on its own merits, not on inherited debt

Example: SPV-3's `8b9dae3 SPV-3: harness mode support + disposition bridge + adversarial fixes` landed `HarnessSecurityConfiguration.java`, `application-harness.yml`, and harness mode branches in `GatewayAuthClient` into retell-service main. The SPV-92 batch PRs did not introduce this — they inherited it. Report this distinction clearly.

## Invariant-Assumption Flagging in PR Bodies

When a PR's correctness depends on a guarantee from a prior ticket that you can't fully verify (e.g. SPV-146's `orgId` validation relies on SPV-85 having completed the organizationId rename at the webhook entry point), handle it as follows:

1. **Do NOT block the ship on uncertainty** — under deadline, blocking is wrong when the assumption is probably correct.
2. **Do NOT silently proceed** — that hides risk from the reviewer.
3. **DO flag the assumption explicitly in the PR body.** Example:

   > **Invariant assumption:** SPV-85 (completed organizationId rename) guarantees that the webhook path (`RetellAIWebhooks → processAnalysis(ctx, orgId)`) always populates `orgId`. If any webhook caller still passes null in prod, that caller's request will now error. **This is a correctness upgrade, not a regression.** Please eyeball the webhook path before merging if you want extra assurance.

Visibility is the middle path. The reviewer can accept/reject the assumption with eyes open.

## Parallel Investigation for Panic

When the user is emotional AND asks for two things (e.g. "investigate the PR AND update Jira"), spawn the lower-priority task as a background agent and drive the investigation yourself in the main context. Keeps the main context focused on the urgent question; both answers arrive without interleaving.

Example from 2026-04-13: User was panicking about harness contamination AND asked for Jira status sync. Spawned a background `general-purpose` agent for read-only Jira audit while investigating PR diffs in the main context. Both results landed in ~30 seconds.

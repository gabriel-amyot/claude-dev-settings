---
name: deploy-identity
description: "Verify which branch/commit ACTUALLY deploys before reasoning about, citing, or externalizing any claim about deployed code. Computes a confidence label as an OUTPUT of a deterministic probe (never a self-rating). Modes: probe (default — resolve deploy branch vs checked-out branch, emit citation stamp + capped confidence) and falsify (dispatch a fresh-context subagent to disprove a disputed claim). Fired automatically by the deploy-identity-guard and challenge-detect hooks; also invokable directly. Use when: 'which branch deploys', 'is this the deployed code', 'verify the deploy branch', after a deploy-identity-guard block, or when a code owner pushes back on a diagnosis. Built for KTP-688 (the wrong-branch catastrophe)."
nav:
  bay: fix
  when: "Before citing/externalizing a claim about deployed code, or after an owner challenges a diagnosis. Resolves deploy branch and caps confidence from a real probe."
  when_not: "Pure local feature work with no claim about what runs in dev/prod. Not a general debugger (use systematic-debugging / investigate for that)."
---

# /deploy-identity

The **body** of the KTP-688 investigate-handle. It is fired *by hooks* (it is not a self-starter),
and it is the single place that answers one question deterministically:

> **Is the code I am about to read / cite / send to someone the code that actually deploys?**

Confidence is an **OUTPUT** of this probe, never something you assert from feeling. The catastrophe
this prevents was *miscalibrated HIGH confidence* — so HIGH is something the probe *grants*, not
something you claim.

## Why this exists (read once)

On 2026-06-29 a diagnosis was built by reading `main` of `app-agent-hub` and asserting about
deployed code that actually runs `dev` (93 commits apart, opposite architecture). Wrong line-refs
were handed to the code owner. Prevention, containment, and detection all failed open. This skill +
its two hooks are the backstop. Full RCA: `project-management/tickets/KTP/KTP-374/KTP-688/reports/reviews/2026-06-29-dexter-meta-rca-wrong-branch.md`.

---

## Mode: `probe` (default)

Run the deterministic probe on the repo/file in question:

```bash
~/.claude/skills/deploy-identity/probe.sh <path-inside-repo>
# or: ~/.claude/skills/deploy-identity/probe.sh --repo <repo-root>
```

It reads the deploy-identity registry (`~/.claude/deploy-identity/<repo>.yaml`, falling back to a
repo-local `.deploy-identity.yaml`), resolves the deployed commit, runs `git branch -r --contains`,
and prints a verification record ending in a machine line `DEPLOY_IDENTITY_JSON={...}`.

**The output you must obey:**

| `status` | `confidence` | What it means | What you may say |
|---|---|---|---|
| `VERIFIED` | `HIGH-ALLOWED` | You are on the deploy branch and it contains the deployed commit. | HIGH confidence permitted. |
| `MISMATCH` | `HYPOTHESIS` | You are NOT on the deploy branch. | **Cap at HYPOTHESIS.** Read the deploy branch before any deployed-code claim. |
| `CANT_VERIFY` | `CANT_VERIFY` | Deployed commit unresolved (infra down / no cached sha). | **Cap at HYPOTHESIS.** State the identity is unverified. |
| `NO_REGISTRY` | `UNKNOWN` | Repo hasn't opted in. | No deployed-branch claim is verifiable; say so, or add a registry entry. |

**The confidence-as-output contract (Problem D):** you may attach HIGH confidence to a claim about
deployed code **only if** the probe returned `VERIFIED`. If it returned `MISMATCH`/`CANT_VERIFY`,
your confidence on that claim is mechanically capped to HYPOTHESIS regardless of how coherent your
story feels. Coherence is not verification.

### Reading the deploy branch when you're on the wrong one

```bash
git -C <repo> show <deploy_branch>:<relative/path>     # read deployed file content
git -C <repo> grep <pattern> <deploy_branch>           # search deployed code
```

### Citation stamps (Problem B — the human-relay vector)

The probe emits a `stamp`. **Attach it to every code citation that leaves your context** (a message
to the user, a drafted post, a relayed line-ref) so the caveat travels with the claim into a human's
hands:

- `bigquery.py:46 [VERIFIED against dev@bae8f58]`
- `bigquery.py:46 [UNVERIFIED — read on main, deploy=dev]`

A claim about another engineer's code with no stamp is not ready to send. (The `/post-comment`
pipeline enforces this on drafted external posts; the stamp is how you carry it through verbal relay,
which no hook can block.)

### WP-13 — snapshot / unconfirmed provenance

If the probe flags the deployed artifact as a `-SNAPSHOT-` tag or `ci_unconfirmed`, the running code
is NOT pinned to a CI build — treat the resolved commit as best-effort and say so. A snapshot tag is
itself a cue that "which commit is this?" was never nailed down.

### Refreshing the registry cache

`app-agent-hub` runs on a COS instance and is unreachable during nightly shutdown, so its registry
entry uses `artifact_source: cache` with a known `deployed_sha`. When infra is reachable, resolve the
live image tag from the instance startup-script, `git rev-parse` it, and update `deployed_sha` /
`deployed_tag` in `~/.claude/deploy-identity/app-agent-hub.yaml`. The cache is a fallback, not truth.

---

## Mode: `falsify` (the fresh-context deep path — Problem C)

Triggered when a credible party (often the code owner) challenges a factual claim, or before
externalizing a HIGH-stakes diagnosis. **Self-red-team under the original anchor rubber-stamps; only
fresh context breaks the frame.** So this mode dispatches a *new* subagent.

Dispatch a fresh-context falsifier via the Agent tool (general-purpose), handing it ONLY:
1. **The disputed claim**, stated plainly.
2. **The challenger's specific evidence** (verbatim — e.g. "Sisi: the schemas folder is missing, same model works on my branch").
3. **The deploy-identity fact** from the probe (`status`, `deploy_branch`, `deployed_sha`).
4. **Its sole task:** *"Prove this claim is WRONG against the DEPLOYED branch. Read `<deploy_branch>` directly via `git show`/`git grep`. Do not gather evidence FOR the claim. Return CONFIRMED / REFUTED / CANT-VERIFY with the deployed-code evidence you found."*

Do **not** pass your prior reasoning or your confidence — that is the anchor you are trying to escape.
Treat the falsifier's REFUTED as decisive: stop defending, converge on its finding.

> The honest limit (from the design): falsification before output is a *disposition*, not an
> enforceable action. The real backstop is mechanical — the hooks that fire this skill, and the
> `/post-comment` token gate on the external edge. This mode is what you run once fired.

---

## Where the triggers live (you don't call this skill cold)

| Trigger | Hook | Fires this skill because |
|---|---|---|
| About to **read** source in a deploy-aware repo while off the deploy branch + deployed intent | `~/.claude/hooks/deploy-identity-guard.sh` (PreToolUse Read\|Grep) | breaks the wrong-branch frame before a claim forms |
| A credible **challenge** to a prior factual claim | `~/.claude/hooks/challenge-detect.sh` (UserPromptSubmit) | routes you into `falsify` mode with fresh context |
| Drafting an **external post** citing another owner's code | `/post-comment` verification gate | requires a stamp/token before the claim can be approved |

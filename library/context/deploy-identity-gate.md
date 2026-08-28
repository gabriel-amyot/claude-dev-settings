# Deploy-Identity Gate

Load when: reasoning about, citing, comparing, or externalizing any claim about **deployed** code.

Learned from KTP-688 (2026-06-29). An agent read `main` of `app-agent-hub` and asserted about deployed code that runs `dev` (93 commits apart, opposite architecture). It handed the code owner wrong line references.

## The core distinction

`git rev-list HEAD..origin/main = 0` proves "my main is current". It does **not** prove "main is what deploys."

Some repos invert the DAC norm. `app-agent-hub` has `main` as default but `dev` deploys.

## Procedure

1. Before any claim about deployed code, confirm which branch deploys. Run `/deploy-identity`, or `~/.claude/skills/deploy-identity/probe.sh <path>`.
2. To reason about deployed behaviour while on the wrong branch, read it directly: `git -C <repo> show <deploy_branch>:<path>`.
3. Deploy facts live in `~/.claude/deploy-identity/<repo>.yaml`.

## Confidence is an output, never self-asserted

HIGH confidence on a deployed-code claim is permitted only when the probe returns `VERIFIED`.

`MISMATCH` and `CANT_VERIFY` cap you at HYPOTHESIS, no matter how coherent the story feels. Coherence is not verification.

## Citation stamps

Code-location claims that leave your context carry the stamp:

- `path:line [VERIFIED against dev@<sha>]`
- `path:line [UNVERIFIED — read on main, deploy=dev]`

`/post-comment` blocks unstamped code references. The caveat must survive a human relay.

## Challenge handling

A challenge is a falsification trigger, not a prompt to gather more confirming evidence.

When a code owner pushes back, dispatch a fresh-context falsifier (deploy-identity `falsify` mode) tasked with disproving your claim against the deploy branch. Self-red-teaming under the original anchor rubber-stamps the error.

## Fetch-before-read gate

Before reasoning about local repo code that reflects a deployed environment, run `git fetch` (sequential, never piped), then `git rev-list --count HEAD..origin/<default-branch>`. If the count is greater than 0, the local checkout is stale. Sync or read `origin/<branch>:path` before concluding.

This applies to reads, not just edits.

Learned from KTP-781 (2026-06-04): a 4-commits-behind checkout produced a false adversarial "COALESCE doesn't exist, no template" conclusion when `origin/dev` had the fix all along.

## Derived knowledge documents are hypotheses

The same skepticism applies to bibliothèque pages, ADRs, and handoffs that assert what deployed code or data does. Treat their claims as hypotheses to verify against live code or BigQuery, not as ground truth. The risk is highest when the document came from unreviewed agent work.

In the same KTP-781 case, a bibliothèque page claimed "the backend county query uses COALESCE" when the deployed adapter did not.

A confident-sounding sibling RCA or status document in the **same ticket** is the prior agent's hypothesis, not settled fact. Re-verify its load-bearing claim before building on it.

**Writing convention.** An unverified diagnosis files under an "Open Questions / Unverified" heading, never "Verdict." A `Verdict:` line is permitted only with a `verified_against: <commit>` stamp.

## The gate generalizes beyond deployed code: a design document is not evidence a control runs

Learned from session `rare-ibis` (2026-08-26). Reviewing Amal's Buying Agent architecture doc twice produced the same error class: a design document described a control, and the review wrote about it as though it already operated. The source said a bid-adjustment safeguard was "in build"; the review wrote "your document already gets this right, it is already yours." The source said v1 covers most failure triggers via a read-back and a delivery-absence alert; the review wrote that reconciliation was scheduled after the first buy, with the ordering itself framed as the defect. Both would have led the reader to treat a planned control as an existing asset, and to make staffing or scope decisions on that basis.

This is the same failure as "derived knowledge documents are hypotheses" above, one level earlier: that section covers a bibliothèque page, ADR, or handoff asserting what deployed code or data *does*. This extends it to any claim sourced from a spec, an ADR, a plan, or an architecture doc asserting that a control *exists* or *runs*, deployed or not.

**How to apply:** When a review says something is missing, absent, or unowned, state it as "the document does not show it" and ask the reader to confirm before treating it as an operational fact. Reserve the assertive form for things verified against a running system, a test, or a person. Write the conditional form by default when the only source is a document.

## A file whose name asserts an environment is not proof the environment reads it

Learned from session `ttd-mcp-prod-path-plan`, KTP-1066 (2026-08-26). `app-klever-media-api` carries `application-prod.properties` with a live prod seat entry (`klever.ttd.seats.jl2ngzy=prod`) on `origin/dev`. The same file on `origin/main`, the branch that actually deploys prod, has no seat entry at all — `main` was 87 commits behind. The filename says prod. The branch decides reality. Reading a `-prod` profile on a feature or integration branch tells you what prod **will** do after promotion, never what prod does now.

This is the deploy-identity gate applied to configuration rather than to code, and it is easier to miss, because the word "prod" in the filename reads as authoritative on its own — there is no branch-comparison step that a code diff naturally invites.

**How to apply:** Read any `application-{env}.properties`, `terraform` env local, or environment overlay on the branch that deploys that environment, not on whichever branch happens to have the newest edit. `git show origin/main:path` costs one command. A profile file's name is not evidence of where it is live.

## A warning is a dated claim, not a fact — re-verify before acting on it

Learned from session `crisp-pike` (2026-08-27). A memory entry carried a prominent warning
banner: local checkout is stale, verified 2026-08-06, naming an abandoned branch 21 commits
behind. Checked on 2026-08-27: `main`, 0 behind. Someone fixed the checkout in the intervening
three weeks and the warning stayed.

This inverts the usual failure. The entry was not wrong about a mechanism — it was wrong that a
problem still existed, and its confident formatting made it read as current state. A warning is
the most costly kind of stale claim, because acting on it means doing unnecessary remediation work
and distrusting a source that is actually fine.

A documented resource location is the same class of claim. Three artifacts said a vendor API key
lived at a specific env-file path. That file held a different key entirely, and it was gitignored,
so the claim was never checkable by reading the repo — only by looking at the actual file on the
actual machine. Two scripts guarded on the documented variable and exited before making a single
call.

**How to apply:** treat any "X is broken/stale" or "the key is at path Y" claim in a memory file
or doc as a dated observation needing the same re-verification as a code claim, before acting on
it. State what a reader should re-run to confirm it still holds when writing such a claim, so the
check is cheap enough that nobody skips it.

## Mechanical backstops

- `deploy-identity-guard.sh` (PreToolUse Read/Grep) blocks reading a non-deploy branch's source during deployed-system reasoning.
- `challenge-detect.sh` (UserPromptSubmit) injects the falsification directive on owner pushback.

Follow the discipline proactively. The hooks only catch what slips.

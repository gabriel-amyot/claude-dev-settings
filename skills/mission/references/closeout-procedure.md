# Close-out procedure (`/mission check --close`)

The main feature shipped. Now find every small thing that is still open, and give each one an outcome or a home. Nothing leaves the mission without one of these.

The script gathers facts. You make the judgements. The human approves before anything visible changes.

## Rules

- **Facts are not verdicts.** `closeout-facts.json` holds what the trackers say. An `UNKNOWN` fact is a gap to check by hand. It is never a pass.
- **The claim is coverage, not completeness.** The report says which sources were searched fully and which gaps remain. It never says that nothing was dropped.
- **No silent closes.** Never close a Jira ticket, never transition it, and never post on Jira or Slack yourself. Draft the text, then use `/post-comment`. You can post GitHub closing comments and close GitHub issues, but only for manifest actions that a named human approved by hash (see Step 5).
- **Approval binds to an exact list.** "Fix all that" is not an approval. The human approves a batch of manifest entries by its hash. An edit to an entry after approval makes the approval void for that entry.
- **Wayfinder maps close through the wayfinder tool.** If an issue has the label `wayfinder:map`, close its children through the `wayfinder` skill, not with `gh issue close`. A raw close leaves gaps in the wayfinder telemetry.
- **No orphans, and a home is not completion.** Every item that stays open gets a successor home that **accepted** it: `successor.accepted: {by: <name>, link}`. A link alone is not coverage. A successor that lists the item as out of scope does not cover it (`excludes: true`).
- **Risk is a human decision.** Every live security, access, safety or contract item needs a residual-risk decision by a named person, or a successor with a named owner. An agent never accepts risk.
- **One report.** `closeout.html` is overwritten on each run. Never write a dated copy.

## Step 1. Gather the facts

```bash
mission closeout gather <slug> [--repo /abs/path/to/member-repo ...] [--exclude "term,term"] [--sweep-cap 50]
```

The scope has no mission record (for example, a component that shipped without one)? Give seeds:

```bash
mission closeout gather --scope <name> --seed-jira KEY1,KEY2 --seed-gh N1,N2 --aliases "alias one,alias two" --since YYYY-MM-DD
```

Pass every member repo with `--repo`: the git and MR sweep reads only those. Without a start date (`mission.created` or `--since`), the GitHub and git sweeps are UNKNOWN.

The output goes to the mission folder, or to `missions/_closeout/<name>/`. It holds:

| Section | Facts |
|---|---|
| `jira.tickets` | Members, seeds and their children (2 levels): status, resolution, the full description and every comment body (within a 40,000-character budget; over budget is `text_truncated` and UNKNOWN), `ac_items`, `ac_evidence` (links per AC), `ac_without_evidence`, `done_without_evidence`, `security`, `closed_without_comments`, `comment_after_close`. A failed or capped `parent in (...)` query, or children left past depth 2, makes the source `PARTIAL` or `UNKNOWN`. |
| `github` | The sub-issue tree under the root issue, the parent issue and the seeds, with every page of sub-issues and comments: state, state reason, labels, tracker parent, `blocked_by`, `blocking`, the body and every comment. `unread_children` lists issues past `--depth`: the source is then `PARTIAL`, never OK. Also `wayfinder_maps`, `reflections` (with `parent_is_map`), `reflections_off_map` (open reflections not under their map), `wayfinder_untraced_closes` (map children closed without the wayfinder tool, from the run telemetry; `UNKNOWN` when the map has no telemetry file) and `blocking_mentions_without_edge` (open and closed issues whose text states an ordering with no `blockedBy` edge). |
| `handoffs` | Pending ledger handoffs (`awaiting_initiation`, `initiated`) whose metadata or text matches a key or alias. Read-only. |
| `drafts` | `no_posted_marker`: `*.md` files under `reports/ship/posts/` in member ticket folders with no sibling `.posted` file and no `posted-as:` line. Each one has `remote_state: UNKNOWN`. The script never confirms a draft as unsent. |
| `branches` | Local branches named after member keys in each `--repo`. Open MRs are always `UNKNOWN` when the forge needs extra auth. |
| `sweep` | Search outside the tree. `jira`: `text ~ "<term>"` for every alias and every member key, all states. `github`: issue search since the mission start. `git`: `git log --all --since` in each `--repo`, commits that name a term. `mrs`: out-of-scope lines in the PR bodies of a GitHub-hosted repo; UNKNOWN elsewhere. Hits already in the tree are dropped. Hits that match a `scope_constraints` entry written `exclude: <term>` (or `--exclude`) go to `excluded`. A search that hits `--sweep-cap` is truncated: UNKNOWN. |
| `twins` | Jira tickets and GitHub issues that cite each other (keys in issue text, issue refs in ticket text), with both states and `states_differ`. A side outside the tree is UNKNOWN. |
| `obligations` | Sweep hits deduplicated by obligation: a ticket and the issue that cites it count once. |
| `security_obligations` | Security, access or auth tickets and issues, in any state, with an AC that has no evidence link, no AC list, or no comment at all (a probe that never ran). |
| `record` | `unratified_decisions` (proposed decisions in the mission), `maps_closed_without_decision`, `maps_decision_unknown`, `orderings_without_edge`. |
| `unknown` | Every source the script could not read, at any depth, with the reason. Also closed tickets whose `comment_after_close` is `UNKNOWN`, drafts whose remote state is not checked, and maps with no wayfinder telemetry. |

Read the `unknown` list first. Check each gap by hand, or carry it into the report as `unknown`.

## Step 2. Review, one reviewer per tracker

Fan out subagents. Give each one the facts file and the mission record, and ask for a bucket list in return (1 to 2k tokens):

- **Pair reviewers**: one per twin pair in `twins`, not one per tracker. The reviewer reads both sides together. A Done twin is never evidence for the open side: each side needs its own evidence, or the open side stays open.
- **Jira reviewer**: the `jira` tickets that have no twin.
- **GitHub reviewer**: the `github` issues that have no twin, one subagent per root if the tree is large.
- **Sweep reviewer**: `sweep` and `obligations`. Each hit outside the tree is in scope, out of scope (say why), or a new item.
- **Security reviewer**: every entry in `security_obligations`, always, including Done tickets and probes that never ran. A security obligation that is live without proof is a big miss until evidence or a named risk decision exists.
- **Local reviewer**: `handoffs`, `drafts`, `branches`, `record`, plus the mission's `parked`, `needs_you`, `messages` and `asks`.

Each reviewer reads the evidence (closing comments, linked MRs, the mission's `decisions` and `disproven`), not only the status. Pass the mission's ratified decisions and disproven claims to every reviewer. They win over any ticket text.

## Step 3. Apply the checklist

Each step gets a status in `closeout.yaml`: `done`, `na`, `open` or `unknown`.

1. **tracker-status.** Compare the live status of every ticket with the evidence. Typical finds: a ticket still in review that the evidence satisfies; a To-do ticket that is done in fact.
2. **parent-closing-comments.** Every closed parent needs a closing comment that links the evidence (what shipped, where it was verified, by whom). A parent closed by a human with no comment still needs one.
3. **description-vs-reality.** On each closed parent, read the description and summary. If they assert the opposite of what shipped (for example "X stays disabled" when X is live), list a `FALSE-PREMISE` item with the exact text to correct.
4. **done-without-evidence.** "Done without evidence" means one AC item with no evidence link (`ac_without_evidence`), not a low comment count. A Done ticket with no AC list (`ac_items: UNKNOWN`) is unchecked, not clean. Check `security_obligations` first. A risky capability that went live without AC evidence is a `HUMAN-ONLY` item with `control`, `live` and `evidence_state` set.
5. **obsolete-items.** A later removal or a scope change can make tickets obsolete. Propose Won't Do, or a rescope with the new text.
6. **github-tree.** Review every open sub-issue. Bucket it: satisfied, superseded, still needed, or premise now false.
7. **false-premises.** Collect every record text (ticket descriptions, issue bodies, library pages, the mission record) that is no longer true. One `FALSE-PREMISE` item each, with the text and the correction.
8. **orphans.** Anything open that has no ticket and no successor issue is an `ORPHAN`. Propose a home. It stays an orphan until the successor accepts it. Then run `mission closeout coverage <slug>`: it reads each successor in full and its explicit out-of-scope lines. A successor that excludes the item does not cover it; the gate refuses until another home accepts it or the successor owner takes it back in (`exclusion_resolved: <link>`).
9. **wayfinder-closes.** For each map in `wayfinder_maps`, close its children through the `wayfinder` skill. If children were already closed with raw `gh issue close`, record a finding.
10. **dependencies.** A stated ordering ("map B blocks the final step of map A") must exist as a `blockedBy` edge. Check `blocking_mentions_without_edge` and the text of the maps. Each missing edge is a finding: add the edge, or record why the ordering is gone.
11. **reflections.** Write every reflection the work requires (for wayfinder maps, the map's reflection ticket). A reflection stays under its map until it is written. Do not move a reflection ticket to a carry-forward issue first: the reflect tool then reports "no reflection ticket". Write it, then move the survivors. Check `reflections[].parent_is_map`.
12. **risk-acceptance.** For each capability that went live with a known gap, a named human decider records the acceptance in a durable place (a ticket comment or a decision record). An agent never accepts risk. Without a record, it is a `HUMAN-ONLY` item.
13. **handoffs.** A pending handoff whose intent is already complete gets closed through the session tools (`session:pickup` triage, or the `ledger` helper). Never edit `sessions/ledger.yaml` by hand. Before you call work lost (a branch gone from git), search the session transcripts: a transcript can still hold the diffs.
14. **drafts.** For each draft in `no_posted_marker`, check its target first (the issue body, the ticket description or the comments). Published already: add a `posted-as: <where> (<date>)` record next to it (a `.posted` file). Not published: it is unsent; post it through `/post-comment`, mark it superseded, or delete it with the human's agreement.
15. **infra-tails.** Cleanup MRs left as draft, unapplied infrastructure changes, stale branches, and temporary access grants. Each one is finished or gets an owner and a date.

Also check a stale tracking issue: an open umbrella issue whose sub-issues all shipped long ago is a `CLOSE-WITH-EVIDENCE` item.

## Step 4. Write `closeout.yaml`

```yaml
schema: mission-closeout/v2
scope: {mission: <slug or null>, name: <name>}
checklist:
  - {id: tracker-status, status: done, note: "2 tickets moved after evidence"}
  # one entry per step id in CHECK_REGISTRY (the 15 steps of Step 3)
items:
  - id: CO-1
    bucket: CLOSE-WITH-EVIDENCE    # CLOSE-WITH-EVIDENCE | SUPERSEDE | KEEP | ORPHAN | FALSE-PREMISE | HUMAN-ONLY
    ref: {kind: jira, ref: KEY-1, url: ..., title: ...}   # or title: for an item with no tracker
    finding: "One sentence: what the facts show."
    evidence: [{kind: url, url: ..., title: ...}]
    action: "One sentence: the proposed action."
    found_by: tracker-status       # the check id that found it, or human (see self-improvement.md)
    # big-miss fields (SYNTHESIS section 3), set them when they apply:
    control: security              # security | access | safety | contract
    live: true                     # true | false | UNKNOWN. Only false proves not-live.
    evidence_state: missing        # present | missing | UNKNOWN
    residual_risk: {decision: accepted, by: Gabriel, link: {...}}   # a named person, never an agent
    affects: [authorization]       # for FALSE-PREMISE: production | authorization | scope | prerequisite
    control_failure: approval-exceeded   # prerequisite-bypassed | unrelated-swept | approval-exceeded | repeat-failure
    decision: {question: "...", options: [{label: ..., consequence: ...}], answer: null}
    successor: {kind: gh, ref: "#N", url: ..., title: ..., owner: Gabriel,
                accepted: {by: Gabriel, link: {...}}, excludes: false}
    parked_by: Gabriel             # required to park an ORPHAN
    owner: Gabriel                 # required on a HUMAN-ONLY item that is not done (or give a successor)
    state: proposed                # proposed | approved | done
manifest:                          # the exact actions, one entry each
  - id: A-1
    item: CO-1
    target: {kind: jira, ref: KEY-1, url: ..., title: ...}
    expected_state: "In review"    # what the target must show before the action runs
    kind: comment                  # comment | close | transition | supersede | edit | move | link | create
    action: "Exact action text, for example the comment body or the transition name."
    evidence: [{kind: url, url: ..., title: ...}]
    successor: {...}               # when the action hands the item to a successor
    class: routine                 # routine | security | cancellation | changed-commitment
    state: proposed                # proposed | approved | done | skipped | unverified (set by the scripts)
approvals: []                      # written by `mission closeout approve`, never by hand
unknowns:                          # one disposition per UNKNOWN source key in closeout-facts.json
  - {source: mrs, consequential: true, disposition: accepted, by: Gabriel, link: {...}}
  - {source: drafts, consequential: true, disposition: tracked, successor: {url: ..., title: ...}}
  - {source: handoffs, consequential: false, reason: "no ledger in this scope holds an obligation"}
human_guide:
  - {step: "Move KEY-1 to Done after the comment is posted.", command: "<exact command, if scriptable>"}
```

Bucket meanings:

| Bucket | Meaning | Who acts |
|---|---|---|
| `CLOSE-WITH-EVIDENCE` | Done in fact. Close it with a comment that links the evidence. | Agent drafts. Jira goes through `/post-comment`. GitHub after approval. |
| `SUPERSEDE` | Obsolete or replaced. Won't Do, or close with a pointer to the replacement. | Same as above. |
| `KEEP` | Still needed. It has a successor home that accepted it. | The successor owner. |
| `ORPHAN` | Still needed, no home. Blocks the close until a successor accepts it. | The human picks the home. |
| `FALSE-PREMISE` | Record text that is now false. Give the text and the correction. | Agent drafts the correction. |
| `HUMAN-ONLY` | Decisions, approvals, risk acceptance, production actions. Needs a named `owner` or a successor until it is done. | The named human. |

### Big miss or routine

A finding is a **big miss** if one of these is true (`big_miss_reasons()` in the script):
- **Live assurance gap.** A live capability (`live` not `false`) has a `control` (security, access, safety, contract) without evidence, or without a residual-risk decision by a named person. An `UNKNOWN` on such a control counts.
- **Valid obligation uncovered.** An `ORPHAN`, a `KEEP` whose successor has not accepted it, a successor that excludes it, or work that may be lost.
- **Consequential false record.** A `FALSE-PREMISE` that `affects` production behavior, authorization, scope or a prerequisite.
- **Control failure.** A prerequisite was bypassed, unrelated work was swept into a write, an action exceeded its approval, or a known process failure happened again.

Everything else is routine. A big miss goes to "Needs you" with a `decision` (the question and the options). Routine work goes into the manifest.

### UNKNOWN dispositions

Every UNKNOWN source key in `closeout-facts.json` (the text before the first colon) needs one `unknowns` entry. A missing `consequential` field counts as `true`. A consequential UNKNOWN is `accepted` by a named human with a link, or `tracked` with a successor. `consequential: false` needs a `reason`, and is refused when an item with a `control` lists the key in its `unknowns`.

## Step 5. Render, approve, act

1. `mission closeout render <slug> --open` (or `--scope <name>`). The report is decision-first:
   1. **Needs you**: the big misses only, each with the decision asked and the options.
   2. **Coverage**: the sources searched fully, and the UNKNOWNs that remain with their disposition.
   3. **Proposed batch**: the exact routine actions, with the batch hash to approve.
   4. **Appendix**: bucket counts, every action taken with its read-back, the items, the checklist, the human guide.
   In the terminal give the `file://` link, the "Needs you" count and the batch hashes.
2. The human answers each "Needs you" decision, and approves a batch by its hash. Record it:
   `mission closeout approve <slug> --items A-1,A-2 --hash <hash they saw> --by <name> --link <where they said yes>`.
   The script refuses an agent as the approver, a batch with more than 15 closes, and a security, cancellation or changed-commitment action in a batch of more than one. Those are approved per item. A changed entry makes `--hash` fail: show the new batch and ask again.
3. Act on each approved action, one at a time:
   1. Re-fetch the target. If it does not show `expected_state`, stop and report. Do not act on a target that moved.
   2. Act: GitHub directly (maps through `wayfinder`), Jira and Slack through `/post-comment`.
   3. Re-fetch the target and record the read-back: `mission closeout record <slug> --action A-1 --before "<state before>" --after "<state after>"`.
   4. A mutation that printed nothing, or a read-back you cannot get: record it with an empty `--after`. The action becomes `unverified` and the script stops you. Check the remote state by hand before any retry. A retry on a silent mutation makes duplicates.
   5. An action you do not run: `mission closeout record <slug> --action A-1 --skip "<reason>"`.
4. Write the human-only guide. If a human step is scriptable (several Jira transitions, a batch of comments), write a small wizard script into the mission folder that runs each step after a confirmation prompt. The human runs it. You do not.
5. Re-run `mission closeout gather` and `render`. The report shows what is left.
6. `mission closeout gate <slug>`. It opens only when:
   - every checklist step has a status;
   - every manifest action is approved by hash (an edited entry voids its approval) and is `done` with a read-back, or `skipped` with a reason;
   - every consequential UNKNOWN has a human disposition;
   - every live security, access, safety or contract item has a residual-risk decision by a named person, or a successor with a named owner;
   - every ORPHAN and KEEP has a successor that accepted it;
   - every human-found big miss names its `new_check` and `eval_case`;
   - every open HUMAN-ONLY item has a named owner or successor.
   When the gate is open, `/mission close` can run. `mission sync` refuses `status: done` while it is closed.
7. Log the close-out: `mission closeout log <slug>` (see `self-improvement.md`).

## Read-only health check (`/mission check`)

Run Step 1 and a short Step 2 at any time, without `closeout.yaml`. Report in the terminal: tracker drift against the record (`mission fetch`), orphans, false premises, drafts with no posted record (remote not checked), dangling handoffs and `UNKNOWN` sources. Change nothing. Record findings in the mission with `/mission update` only if the human asks.

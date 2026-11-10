# mission.yaml schema (mission/v1)

`missions/<slug>/mission.yaml` is the main record of a mission. It is committed and pushed in the project-management repo (`gabriel-amyot/klever-project-management`). The GitHub root issue links to it. Everything else (README.md, report.html, computed.json) is generated from it.

`scripts/mission_lint.py` enforces this schema. Run it after every edit.

## Field classes

- **STABLE**: rarely changes (destination, why, aliases).
- **LOG**: append-only. Never rewrite an old entry. Supersede it with a new entry that points back (`supersedes:`).
- **LIVE**: overwrite in place. Only the current value matters (`next_milestone`, `needs_you`, `status`).
- **COMPUTED**: never written by hand. `mission_fetch.py` writes it to `computed.json` (tracker status from Jira and GitHub, with `fetched_at`).

Tracker status is never stored by hand. Jira and GitHub are read at fetch time, because local status claims rot: 12 of 13 lagged Jira in the 2026-11-09 audit.

## IDs

Every item that Gabriel may refer to gets a stable short ID when it is created. Never renumber.

| Prefix | Item |
|---|---|
| `D-` | deliverable |
| `DEC-` | decision |
| `X-` | disproven claim |
| `N-` | needs you (blocker or decision only Gabriel can clear) |
| `A-` | ask (a question or request from Gabriel or a stakeholder) |
| `P-` | parked track |
| `M-` | message draft (to a person) |
| `ART-` | artifact (kit, file, SHA) |
| `J-` | journey entry (one session or run) |
| `C-` | change (latest-changes log) |

## Links

A link is always typed and titled, never a bare number:

```yaml
- {kind: jira, ref: KTP-1398, url: https://beklever.atlassian.net/browse/KTP-1398, title: "Part 2 - Powers MCP: deploy read and write to prod"}
```

`kind` is one of `jira`, `gh`, `mr`, `file`, `folder`, `session`, `url`, `slack`.

## Full shape

```yaml
schema: mission/v1
slug: ttd-ot-feedback                 # STABLE, folder name
title: "TTD MCP: address OT feedback" # STABLE
status: active                        # LIVE: active | parked | done | abandoned
created: 2026-11-10T22:30:00Z         # from `date -u`, never guessed
updated: 2026-11-10T22:30:00Z         # set by mission_sync.py
last_report_at: null                  # set by mission_render.py; start of the "Latest changes" window

root_issue: {number: 671, url: https://github.com/gabriel-amyot/klever-project-management/issues/671}
parent_issue: {number: 594, url: ..., title: "Component: TTD trading MCP"}   # optional

destination: >                        # STABLE: what done looks like, 1-2 lines
  OT reads her live Powers book and writes bids from Claude Desktop on Windows, in production.
why: >                                # STABLE: 2-5 lines
  OT feedback (KTP-1289) said reads were poor and writes did not work.
scope_constraints:                    # STABLE: agreed boundaries ("build the flow, wait on execution")
  - "Write stays closed until DEC-2 is ratified."

verdict: "One sentence, max 20 words: where the mission stands now."   # LIVE, top of the report

next_milestone:                       # LIVE
  title: "Writes verified on prod by OT"
  done_when: "OT places one bid from Windows and it shows in the Powers book."
  owner: Gabriel
  deliverable: D-B

aliases: ["Powers MCP", "TTD trading MCP", "KTP-1289", "app-ttd-trading-mcp"]   # STABLE

members:                              # STABLE list, role is LIVE
  - {kind: jira, ref: KTP-1398, url: ..., title: ..., role: current, note: "Part 2 deploy"}
  - {kind: gh, ref: "#659", url: ..., title: ..., role: current}
  - {kind: folder, ref: tickets/KTP/KTP-3/KTP-1398, url: "file:///Users/...", title: "KTP-1398 ticket folder", role: current}
  - {kind: session, ref: clear-wren, url: "https://github.com/gabriel-amyot/klever-project-management/tree/main/sessions/active/clear-wren", title: ..., role: done}
  # role: current | done | superseded | parked

deliverables:                         # LIVE status_line
  - {id: D-A, title: "Story A: read path", members: [KTP-1289], status_line: "Done, verified by Gabriel 2026-11-09"}
  - {id: D-B, title: "Story B: write path", members: [KTP-1398], status_line: "Shipped to prod, not verified live"}

decisions:                            # LOG
  - id: DEC-1
    date: 2026-11-09
    statement: "Seat-wide discovery replaces name guessing for OT's campaign list."
    state: ratified                   # proposed | ratified | superseded | reversed
    ratified_by: {who: Gabriel, link: {kind: url, url: "...", title: "terminal turn 2026-11-09"}}
    supersedes: null                  # DEC-id this one replaces
    licenses: ["app-ttd-trading-mcp:src/discovery.py#list_campaigns"]   # code built on it = unwind checklist
    session: brave-otter

disproven:                            # LOG
  - id: X-1
    date: 2026-11-07
    claim: "Prod today has none of the surface the MCP calls."
    evidence: {kind: jira, ref: KTP-1398, url: ..., title: "prod-prep README: live since 2026-09-16"}
    signature: "none of the surface the MCP calls"      # literal grep string that finds stale copies

parked:                               # LIVE
  - {id: P-1, title: "Advertiser-level authorization", bucket: horizon, owner: Gabriel, since: 2026-11-09, recheck: null, reentry: "After writes are verified", links: [...]}
  # bucket: horizon | tomorrow | blocked_on_person

needs_you:                            # LIVE: delete the item when it is resolved and add a journey/changes entry
  - id: N-1
    since: 2026-11-09
    question: "Send the 0.15.7 kit to OT?"
    why: "She cannot test native Windows without it."
    options:
      - {label: "Send now", consequence: "OT tests tonight", source: drafted}
      - {label: "Wait for writes fix", consequence: "One message instead of two", source: drafted}
    recommendation: "Send now"
    after_answer: "I mark M-1 sent and watch for her reply."
    links: [...]
    blocking: true                    # false = FYI row, not in the Needs you count

asks:                                 # LOG with LIVE state
  - {id: A-1, asker: Gabriel, date: 2026-11-10, text: "What is missing to close story A?", state: answered, answer: "Nothing: done 2026-11-09.", link: null}
  # state: open | answered | done | deferred | superseded | blocked

journey:                              # LOG: one entry per session, night run, or commit-only span
  - id: J-1
    kind: session                     # session | night_run | commit_only | gap
    session: brave-otter
    start: 2026-11-09T14:00:00Z
    end: 2026-11-09T23:00:00Z
    summary: "Shipped 0.15.7, verified 5 of 9 OT asks on prod."
    milestones: ["0.15.7 on prod"]
    blockers: ["Native Windows untested"]
    confusion: ["Which kit file was sent"]       # moments where Gabriel or the agent lost the thread
    findings: ["Seat-wide discovery works for all of OT's campaigns"]
    decisions: [DEC-1]
    links: [...]

artifacts:                            # LOG
  - {id: ART-1, title: "Windows test kit 0.15.7", path: "/Users/gamyot/Desktop/ttd-production-windows-test-kit-0.15.7-0a08771.zip", sha256: "dffc92...", date: 2026-11-09}

messages:                             # LIVE state
  - {id: M-1, to: OT, channel: slack-dm, state: draft, draft: "Salut Othalia! ...", sent_text: null, date: 2026-11-09}
  # state: draft | sent | answered

graph:                                # STABLE-ish: the mission's context graph
  nodes: [{id: mcp, label: "TTD trading MCP", kind: system}, {id: ot, label: "OT", kind: person}]
  edges: [{from: ot, to: mcp, label: "uses from Claude Desktop"}]
  # kind: system | person | concept | decision | ticket | repo | env

terms:                                # STABLE: terms Gabriel confirmed he knows in this mission
  - {term: "seat", meaning: "a TTD partner account", confirmed: true}

changes:                              # LOG: feeds the "Latest changes" view
  - {id: C-1, at: 2026-11-10T22:30:00Z, session: clear-wren, summary: "Mission created.", refs: []}
```

## Rules the lint enforces

1. Required: `schema`, `slug`, `title`, `status`, `created`, `destination`, `root_issue`.
2. Enums are valid. IDs are unique and carry the right prefix.
3. A `ratified` decision has `ratified_by.who` and `ratified_by.link`. Without them it is shown as PROPOSED.
4. "Re-litigate" wording appears only on a ratified decision.
5. A decision that `supersedes` another must point at an existing ID.
6. Every link has `kind`, `url` and `title`. Jira and GitHub members have a `url`.
7. Every `needs_you` item has a question and either options or `free: true`.
8. An `answered` or `done` ask has an `answer`.
9. `journey` entries are in time order.
10. Warnings (not errors): a body text over 400 characters in a list item, a `needs_you` item older than 14 days, a parked `tomorrow` item past its `recheck` date.

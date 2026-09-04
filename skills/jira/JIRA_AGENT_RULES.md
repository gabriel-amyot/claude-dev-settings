# Jira Agent Interaction Rules

These rules apply to all AI agent interactions with Jira, regardless of project or organization.

---

## Rule 0: HUMAN GATE on All Public Writes

**STOP. Before executing ANY write operation (create ticket, update description, add comment, transition), you MUST:**

1. Show the user exactly what you intend to write (full text, not a summary)
2. Get explicit confirmation in the SAME conversation turn ("go ahead", "post it", "yes")
3. Only then execute

This applies even if a plan was previously approved. Plans go stale. Gab's reputation is on every Jira comment and every PR reply. Draft locally first, show it, get the green light.

**Write operations that require this gate:**
- `create` (new tickets)
- `update --description` (ticket descriptions)
- `add-comment` (Jira comments)
- `transition` to Done/Closed (also covered by Rule 1)

**Read operations that do NOT require this gate:** `list`, `get`, `description`, `metadata`, `search`, `subtasks`, `epic`, `comments`, `attachments`, `fetch`

---

## Rule 1: Never Close Tickets Without Human Confirmation

Agent CAN transition tickets to:
- In Progress
- In Review
- Ready to Deploy

Agent CANNOT transition tickets to:
- Done
- Closed

Done/Closed requires explicit human confirmation via:
- A Jira comment from a human confirming acceptance criteria are validated
- A direct instruction in the Claude Code session (e.g., "close SPV-8, ACs are validated")

---

## Rule 2: Comment Tone - Honest, Not Overconfident

- Say "code implementation complete" not "integration complete"
- Say "deployed to dev" not "deployed and working"
- Say "service starts successfully" not "all tests passing" (unless tests were actually run)
- Always mention what has NOT been validated
- No emojis in Jira comments

---

## Rule 3: No Attribution Header — Write as Gabriel

Comments carry NO visible attribution. No `[automated]` tag, no `<tool> | <model> | session` line,
no persona name, no "Message from {persona}", no "Posted via Claude Code". They read as if Gabriel
typed them, because he is the account posting them.

Reason: the visible AI tag caused teammates to skip the comments unread ("I don't read AI"). The
whole point of a comment is that it gets read. Provenance still exists, just not in the reader's
face: the on-disk audit log (post-log) records tool, model, and session for every post.

(Was: a mandatory `[automated] <tool> | <model> | session` header. Reversed 2026-07-08 on Gabriel's
instruction after backlash.)

---

## Rule 4: Comment Structure — Fewest Words That Carry the Point

Short and readable beats complete and skipped. A wall of text disrespects the reader's time; long
AND wrong never gets read again.

- Lead with the point (the outcome or the ask) in the first line. No preamble, no attribution line.
- No story. Do not narrate what happened, why, what was tried, or in what order.
- Short sentences, plain words, few adjectives, precise technical terms.
- No filler ("I dug into", "happy to hop on a call", "let me know if you have questions").
- No em-dashes. Structure (headers, groups) only when the content genuinely needs it, never as default.
- Routine comment target: under ~120 words. Longer only when the content truly requires it.

---

## Rule 5: No Emojis

Jira comments written by agents must not contain emojis. Use plain text formatting only.

---

## Rule 6: AC Quality Gate on Ticket Creation

Before executing any `create` command:

1. **Load `~/.claude/library/context/ticket-quality-standards.md`** for reference
2. **Check for AC section.** If the description has no acceptance criteria, warn the user and ask them to define AC before creating. Do not silently create AC-less tickets.
3. **Apply the litmus test to each AC:** Does it describe WHAT the result looks like (spec-based) or HOW to do it (task-based)? Flag task-list ACs with a suggested rewrite using the anti-patterns table from the standards doc.
4. **Check minimum bar:** At least 2 testable ACs per ticket. Warn if fewer.
5. **Mandatory gate (soft block).** The agent must run this check and present findings. User can override with explicit "create it anyway." Respect their decision without re-asking.

This gate does not apply to spike tickets (where AC define questions to answer, not outcomes).

---

## Rule 7: Audience Gate on Ticket Creation — GitHub Is the Default, Jira Is Explicit-Only

**Runs BEFORE Rule 6.** No point checking AC quality on a ticket that should not exist on the board.

Jira is the board colleagues read. Every ticket on it costs other people attention. Internal
work does not belong there, and a `create` is mechanically blocked until the audience decision
is recorded on the command.

**The audience test — will a colleague need to see this?**

| Answer | Destination |
|---|---|
| **No** | GitHub Issues, `gabriel-amyot/klever-project-management`. Decisions, open questions, pivots, your own task decomposition, reading and approval items. Wayfinder decision tickets always land here. |
| **Yes** | Jira, re-run with `--audience team` |
| **Unsure** | Ask Gabriel. Do not guess, and do not pick Jira because Jira is habitual. |

```bash
# internal — the default
gh issue create --repo gabriel-amyot/klever-project-management \
  --title "<the question or decision>" --body "<detail>"

# team-facing — requires the recorded decision
python3 jira_skill.py --org klever create ... --audience team
```

**What counts as explicit Jira intent.** The user names Jira or the board: "create a jira ticket
for X", "break KTP-1234 into smaller jira tickets", "file a bug on the board". Note that a
breakdown request into *subtasks* is team-facing, because the PO wants breakdowns as Jira
subtasks. Absent an explicit signal, assume internal.

**Enforcement.** `hooks/jira-create-gate.sh` (PreToolUse, Bash) blocks any `jira_skill.py create`
without `--audience team`. `--audience internal` is blocked with the GitHub command. The flag is
stripped in `jira_skill.py` next to `--org` and never reaches the API. Regressions:
`hooks/evals/fixtures/jira-create-gate.yaml` (21 cases, includes reword-past-the-gate).

The hook sees the Bash tool only. A create through another tool path is unseen and is **not**
thereby approved. Kill-switch: `touch ~/.claude/.jira-audience-gate-off`.

---

## Future Improvement: Dedicated Agent Account

A dedicated Jira account (e.g., `ai-agent@origin8cares.com`) would make agent comments visually distinct (different avatar and name) without putting an AI tag in the reader's face. Until then, comments post under Gabriel's account with no visible attribution, and traceability lives in the on-disk audit log (post-log), not in the comment text.

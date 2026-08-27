# Ticket Quality Standards

On-demand reference for ticket creation, AC writing, ticket closure, and bug fix protocols.

## Klever Jira Ticket Rules (Raj, 2026-07-03)

Klever's ticket-structure convention, from Raj's shared email. Apply whenever generating tickets for a Klever epic. Learned the hard way: on 2026-07-03 an agent created 14 flat sibling Stories under epic KTP-853, which is a task list masquerading as stories and broke this convention.

### Who creates what
- **Epics and Stories are PM-owned.** An agent drafts them; the PM approves and owns them on the board. Future-scope Stories are created by the PM at the sprint boundary, not pre-seeded by an agent.
- **Sub-tasks and Tasks are the engineering breakdown** and may be drafted for approval.

### Create / don't-create
- **DO** consolidate aggressively. Many small work items collapse into one Task or a handful of sub-tasks.
- **DON'T** fan out many sibling Stories under an epic.
- **DON'T** put placeholder future tickets (v1/v2/"later") on the board. Future increments live in the PRD / roadmap doc and get promoted to Stories at their sprint boundary.
- **DON'T** create ≥5 tickets at once without staging them as a reviewed batch for approval first. Never a Story fan-out.

### Ticket-type model (Raj's rules, reconciled by the BMAD Scrum Master)
| Type | Definition | AC style |
|---|---|---|
| **Epic** | The whole arc of work. PM-owned. | No GWT AC — it is a container / roadmap. |
| **Story** | An **independently valuable, sprint-sized, GWT-testable** increment (INVEST "V"). PM-owned. | Given/When/Then, observable outcome QA can assert. |
| **Sub-task** | Dev/infra breakdown meaningful **only inside its parent Story**. Cannot be sprinted alone. | A single "Done when …" line. |
| **Task (top-level)** | An infra prerequisite that **spans multiple Stories** (e.g. repo scaffold). Use sparingly. | A single "Done when …" line. |

### The Story-vs-sub-task-vs-Task test (the value bar)
Ask of each candidate item: **is it independently valuable, sprint-sized, and testable via a Given/When/Then that QA could assert on its own?**
- **Yes** → it is a **Story**.
- **No, and it only makes sense inside one parent Story** → **sub-task**.
- **No, but it is a prerequisite that several Stories depend on** → **top-level Task**.

Both extremes are wrong. 14 flat Stories fails the test downward (most items were not independently valuable). Collapsing everything into a single Story fails it upward (it buries two or three separable value increments and kills sprint planning). The correct output is however many items genuinely clear the value bar — often a small number, not one and not many. Worked example: KTP-853's v0 came out to **3 Stories** (provisioning, proven-migration, parity harness), because each is independently valuable, testable, and ships at a different moment, while all the infra/config sits under them as sub-tasks and one shared-prerequisite Task.

### Claude usage
Draft → get approval → then write to Jira. Never fan out Stories. For ≥5 tickets, present a staged batch table for one-pass approval before touching Jira.

## Closing Tickets in Jira

Before transitioning any ticket to Done/Closed, post a closing comment (via `/post-comment`) that includes:

1. **What was done** — summary of work delivered per AC
2. **Why it's closeable** — validation evidence (tests green, UI verified, quality gate findings, etc.)
3. **References** — commit SHAs, MR/PR links, branch names

Never close a ticket without this evidence trail. The Jira comment is the audit trail for why a ticket was closed.

**Process:**
1. Validate e2e and/or UI for the ticket's ACs
2. Draft closing comment via `/post-comment` with the three elements above
3. Get user approval on the comment
4. Post and transition ticket status

## Adversarial-Gated Ticket Closure

Never close a ticket without adversarial review. Before moving any ticket from "In Review/Testing" to "Done":

1. Spawn the adversarial general (BMAD) with the ticket's ACs and collected evidence
2. The adversarial must give a per-AC verdict: PASS, FAIL, or BLOCKED with justification
3. Route adversarial findings through Amelia (code) and Winston (architecture)
4. Don't dismiss findings; address them or document why they're accepted risks

**Coverage classifications (honest labeling):**
- **VERIFIED** = tested end-to-end (E2E script, UI test, or direct observation)
- **CODE VERIFIED** = unit test passes but no E2E
- **BLOCKED** = cannot test without infrastructure (staging, GCP, etc.)
- Never conflate CODE VERIFIED with VERIFIED

Learned from INS-205 session 2026-03-27: coverage was inflated from 36% to 86% by relabeling "unit test exists" as "PASS." The adversarial general caught this and also discovered a critical infinite fetch loop bug.

## Something Not Working — Investigation-First Workflow

Applies when Gabriel or anyone reports: unexpected behavior, visual bug, feature misbehavior, broken interaction, "this isn't working." Does NOT require a formal bug ticket. The trigger is "something isn't working as expected," whether during development or after deploy.

### Phase 1: Investigate (Quinn)

Quinn owns investigation. Before anyone touches code:

1. Invoke `superpowers:systematic-debugging` — complete its Phase 1 (Root Cause Investigation) and Phase 2 (Pattern Analysis)
2. Identify the **specific** file, layer, component, or endpoint causing the issue
3. If frontend/visual: capture screenshot evidence of the current broken state
4. Post investigation findings to the ticket (Quinn-signed comment via `/post-comment`)

No guessing. No "it's probably X." Find the actual root cause.

### Phase 2: Fix (Amelia)

Amelia implements the fix that Quinn's investigation identified:

1. Fix only what Quinn identified. Do not expand scope.
2. Apply the fix directly. No proposals, no "Option A or Option B." Gabriel sees results, not menus.
3. Commit with root cause in the message (what was wrong, why, what changed)
4. Push, create MR, deploy

### Phase 3: Validate (Quinn)

Quinn validates the fix on dev (or locally if dev is down):

1. Invoke `superpowers:verification-before-completion` before any completion claim
2. For frontend: use `/klever-test` (AC validation sub-module) or direct browser observation
3. Capture after-fix screenshot evidence
4. Post validation result to ticket (Quinn-signed comment): PASS with evidence, or FAIL with what's still broken

If FAIL → back to Phase 1. Quinn re-investigates (the root cause was wrong or incomplete).

### Phase 4: Close

Only after Phase 3 PASS. Post closing comment via `/post-comment` with: root cause, fix reference (commit + MR), before/after evidence.

### When Leo joins

Leo speaks only if the AC itself is wrong or ambiguous. Restating existing AC adds noise. If Quinn's investigation reveals the AC doesn't describe the actual expected behavior, Leo rewrites the AC. Otherwise Leo stays silent.

### Trivial fixes (escape hatch)

If the fix is a genuine one-liner with an obvious root cause (typo, wrong import, config value, off-by-one visible in a stack trace): Amelia can fix directly without full Phase 1. The test: "Can I name the exact line and explain why it's wrong without reading any other file?" If yes, skip to Phase 2. If no, full workflow.

### Persona scope (for this workflow)

| Persona | Does | Does NOT |
|---------|------|----------|
| Quinn | Investigate root cause, validate fix, capture evidence | Write production code, propose fixes, write AC |
| Amelia | Implement the fix Quinn identified, commit, push | Investigate (Quinn's job), validate own fix, skip to fixing |
| Leo | Rewrite AC when it's wrong or ambiguous | Debug, investigate, validate, propose implementation |

### Anti-patterns (from KTP-628 RCA)

- Guessing the fix without investigation (Amelia fixed metrics-popup.tsx; real bug was in update-flow-lines.tsx)
- Posting "Fix Shipped" without Phase 3 validation
- Leo doing investigation/QA work (wrong persona)
- Proposing options instead of applying and testing a fix
- Stopping at "needs visual verification on dev" without doing the verification

Learned from KTP-628 2026-05-08: Amelia shipped wrong-layer fix same day as ticket creation. Fix deployed but problem persisted. Leo investigated two days later, found real cause, but proposed two options without applying either. No Quinn validation at any point.

### Frontend fetch loops

Detectable by installing a fetch interceptor via `window.__fetchLog` pattern. Compare call counts over 5 seconds: 0 at idle is healthy, 100+/sec is a loop.

Learned from INS-205 2026-03-27: competitor infinite fetch loop (~100 req/sec) was only discovered because the adversarial general questioned date-refetch behavior.

## AC Quality Standards

**Standard template:** `~/.claude-shared-config/skills/templates/jira-ticket-description.md` (merged standard, Gabriel 2026-07-20). Only Summary + Acceptance Criteria are mandatory. Lead with a Hero AC (the plain user outcome anyone understands), then supporting ACs, each a one-line outcome header + Given/When/Then (no redundant description line). Keep the AC-0 scope-confirmation gate. Optional-only, never force-filled: Out of scope, Design/Technical Recommendations, Implementation Recommendations. Questions are NOT a section, they go as ticket comments. No em-dashes; no machine-local filesystem paths (name internal docs; shared refs like code paths/BQ tables/sheet ids/skills are fine).

When writing acceptance criteria:
- Use Given/When/Then format
- Each AC must describe an observable outcome, not a task
- ACs must be assertable by QA without reading the code
- Avoid vague language: "properly", "correctly", "as expected"

## Ticket Anti-Pattern: Deferring a Decision While Writing ACs That Presuppose Its Answer

Learned from session `crisp-vireo`, KTP-1153/1154 rewrite review (2026-08-26). The recognizable shape: a ticket honestly flags an unresolved architectural choice, then writes acceptance criteria for one branch of it. This reads as thorough and is unbuildable, because the ACs silently pick the answer the prose refused to pick. Two concrete instances: one ticket said "two contracts are defensible, pick one" then specified hot reload in AC-1; another said "confirm which copy wins" then replaced the disk copy in AC-1, which only holds if the image wins. Neither was implementable as written.

The fix is to split the decision from the implementation. Keep on the ticket only the criteria that hold regardless of which way the decision goes (usually the observability and logging ones), and gate the implementation criteria behind the recorded decision, either in a second ticket or an explicitly not-ready section.

**How to apply:** when writing a ticket that contains "pick one before implementing" or "confirm X before", check every AC against both branches of that choice. Any AC that is only valid under one branch does not belong on the ticket yet.

## Ticket Description Standards

- Story format: "As a [role], I want [capability], so that [benefit]"
- Include at least 2 spec-based acceptance criteria
- Reference related tickets and dependencies
- Include context section explaining why the work is needed

## Adversarial Codebase Verification for New Tickets

Before finalizing any ticket spun out of RCA notes, incident reports, or investigation sessions, adversarially verify every factual claim against the local codebase:

1. **Entity names** (topics, subscriptions, tables, fields): grep the codebase for the exact name. RCA notes use approximate or pattern-level names, not literal resource identifiers.
2. **Publisher/consumer claims**: read the actual publisher code to confirm it can produce the payload described. If only one publisher exists and it uses typed serialization, it cannot have emitted a bare string.
3. **Schema field claims**: read the actual `.graphqls` schema or entity definition. Never trust RCA shorthand about which fields exist on a type.
4. **Config interpretation**: read the actual `application.yaml` or equivalent. Config keys like `ignoreableProperties` or `timestampIdentifier` have framework-specific semantics that may differ from the plain English reading.

Spawn parallel Explore agents (one per ticket) for efficiency. Each agent verifies all claims in one ticket and reports CRITICAL / HIGH / MEDIUM / LOW findings.

Learned from SPV-141 → SPV-143/144/145 session (2026-04-11): all three tickets drafted from RCA incidental findings had CRITICAL factual errors (wrong subscription name, non-existent schema field, conflated ERS metadata with domain columns). Caught by adversarial review before the tickets reached the team.

## RCA-to-Ticket Name Verification

RCA incidental findings use pattern-level or shorthand names (e.g., "Compliance_<Entity>_Update-ERS" for a class of subscriptions) not literal resource names. When extracting a specific ticket from an RCA finding:

- Grep the codebase for the actual topic/subscription/table name
- Cross-reference IAC/terraform for infrastructure resource names
- The RCA is context for why the work matters; the codebase is the source of truth for what things are actually called

Learned from SPV-143: RCA said "Compliance_Lead_Update-ERS" but actual topic is just "Compliance_Lead_Update" with ERS generating its own subscription name.

## Code-Grounded Ticket Descriptions

Ticket descriptions should reference actual repo file paths with line numbers (e.g., `app/micro-services/compliance-ers/src/main/resources/application.yaml lines 22-31`). Benefits:

- Claims become self-verifying: anyone can read the file and confirm
- Implementers get direct navigation to relevant code
- Reduces ambiguity about which service, which class, which config key
- Adversarial reviewers can trace every claim to source

Include a `h2. References` section at the bottom of every ticket listing all cited files and their relevance.

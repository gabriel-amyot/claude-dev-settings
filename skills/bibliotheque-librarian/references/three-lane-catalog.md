# Three-Lane Catalog Pattern

Reference for the Supervisr Bibliothèque root INDEX.md structure. This pattern governs how incoming knowledge entries from the inbox are routed into the three catalog lanes and how section descriptions are written.

---

## Why Three Lanes

People arrive at a knowledge library in one of three modes:

1. **Curious** — learning the system, onboarding, filling a conceptual gap.
2. **Crisis** — something is broken RIGHT NOW, they need an answer fast.
3. **Executing** — they have a job to do and need the right tool or procedure.

A single flat list forces all three modes to scan the same index. Three lanes match intent to catalog structure, eliminating scanning.

---

## Lane 1: Understand

**Header:** `## I Need to Understand Something`

**Purpose:** Conceptual knowledge. The reader is learning, not panicking.

**Table columns:** `Question | Where to Look`

**What belongs here:**
- Glossary and terminology (what does SBE/ERS/EQS mean?)
- Service descriptions and responsibilities
- Domain model explanations (insurance lead lifecycle, compliance pipeline)
- Team roster and ownership
- Data flow diagrams and architecture overviews
- Technology choices and why we made them

**Trigger phrases that route here:**
- "What is X?"
- "What does X do?"
- "How does X work?"
- "What is the relationship between X and Y?"
- "Who owns X?"
- "Where is X defined?"

**Example entries:**

| Question | Where to Look |
|----------|--------------|
| What does SBE/ERS/EQS/LLS mean? | [GLOSSARY.md](../GLOSSARY.md) |
| How does the lead pipeline flow? | [stack/interaction-disposition-flow.md](../stack/interaction-disposition-flow.md) |
| What is the insurance lead domain? | [domain/INDEX.md](../domain/INDEX.md) |

**Classification rule:** If the question starts with "what", "who", "why was X designed as", or "how does the system handle", it belongs in the Understand lane.

---

## Lane 2: Blocked

**Header:** `## I Am Blocked by an Error`

**Purpose:** Symptom-first triage. The reader is under pressure and needs to identify the cause quickly.

**Table columns:** `Symptom | Likely Cause | Go Here`

**What belongs here:**
- HTTP error codes with context (not raw "401" but "Gateway → subgraph returns 401")
- Pipeline failure messages (terraform init failure, registry errors)
- Data anomalies visible in the product (empty dashboard, missing transcripts)
- Auth failures with service-pair context
- Known infrastructure windows (nightly downtime, maintenance)
- Agent anti-patterns that lead to wasted hours (tunnel vision, wrong hypothesis)

**Trigger phrases that route here:**
- "I'm getting a 4xx / 5xx"
- "Pipeline is failing"
- "Dashboard shows empty"
- "Service X can't reach service Y"
- "Deploy is broken"
- "Same error keeps happening"
- "X is returning null / empty"

**Example entries:**

| Symptom | Likely Cause | Go Here |
|---------|-------------|---------|
| Gateway → subgraph returns 401 | Dual-header conflict: `Authorization` + `userAuthorization` sent together | [stack/gateway-dual-header-401.md](../stack/gateway-dual-header-401.md) |
| Pipeline fails at `terraform init` | Terraform registry maintenance window (~midnight-1AM EST) | [operations/cicd-registry-maintenance-window.md](../operations/cicd-registry-maintenance-window.md) |
| Dashboard shows empty / no transcripts | Datastore key.name != interactionId | [stack/interactions-mv-schema-and-key.md](../stack/interactions-mv-schema-and-key.md) |

**Classification rule:** If the entry starts from an observable failure (error code, missing data, broken pipeline), it belongs in the Blocked lane. The Symptom column must be specific enough to pattern-match: write "Gateway → subgraph returns 401" not just "401 error".

---

## Lane 3: Do Something

**Header:** `## I Need to Do Something`

**Purpose:** Task-oriented execution. The reader has a job and needs the right runbook or tool.

**Table columns:** `Task | Where to Look`

**What belongs here:**
- Deployment procedures
- Recovery playbooks
- Handoff checklists
- Operational SOPs (create a ticket, run a migration, rotate a credential)
- Tool usage guides when the tool has non-obvious invocation

**Trigger phrases that route here:**
- "How do I deploy X?"
- "How do I recover X?"
- "I need to hand off X"
- "How do I create X?"
- "Steps to do X"
- "Runbook for X"

**Example entries:**

| Task | Where to Look |
|------|--------------|
| Deploy a service | [operations/INDEX.md](../operations/INDEX.md) |
| Take over a contractor's AI feature | [operations/ai-agent-feature-handoff-checklist.md](../operations/ai-agent-feature-handoff-checklist.md) |

**Classification rule:** If the entry describes a repeatable human action with a defined start and end, it belongs in the Do Something lane.

---

## Entries That Span Multiple Lanes

Some knowledge legitimately belongs in more than one lane. Apply these rules:

**Symptom + concept = Blocked (primary) + Understand (secondary)**
Example: "WebClient.bodyValue(String) double-serializes JSON" is a debugging symptom (Blocked) but also a conceptual explanation (Understand). Place it in Blocked first (readers hitting this are in crisis). If the concept is deep enough to warrant its own file, also add a row to Understand.

**Procedure + background = Do Something (primary) + Understand (secondary)**
Example: "Rebuild dev Datastore from BQ sink" is a procedure (Do Something) but "why BigQuery is the recovery source" is conceptual (Understand). Add the procedure to Do Something. The file itself can contain both the how and the why.

**Tooling gotcha = Blocked (if it manifests as a failure) or Do Something (if it's a workflow step)**
Example: "gitlab pipeline vs pipelines command" is a Blocked entry if it causes accidental pipeline triggers. If it's framed as a how-to-list-pipelines question, it belongs in Do Something.

**Rule:** When in doubt, ask "What mode is the reader in when they need this?" Crisis → Blocked. Learning → Understand. Executing → Do Something.

---

## Writing "Go Here When..." Section Triggers

Every section description in the root INDEX.md `## Sections` block must include a "Go here when..." clause. This converts passive labels into active routing instructions.

**Without trigger (bad):**
```
- **[stack/](stack/INDEX.md)** — GCP services, service catalog, data model, BigQuery
```

**With trigger (good):**
```
- **[stack/](stack/INDEX.md)** — Service architecture, data flows, gateway behavior. Go here when debugging service interactions or understanding how data moves.
```

**Formula:** `{what the section contains}. Go here when {the reader's current situation or goal}.`

The trigger phrase answers the question the reader is asking before they click: "Is this where I should look?"

**Effective trigger patterns:**
- "Go here when debugging X"
- "Go here when something is broken"
- "Go here when you need business context for Y"
- "Go here when you need to ship / fix / recover"
- "Go here when you need to know who owns X"

---

## Bootstrap Placeholder Hygiene

When a section INDEX is first scaffolded, it gets placeholder text:

```markdown
## Contents
*Section bootstrapped 2026-04-18. Populate with:*
- Suggested topic 1
- Suggested topic 2
```

**Rule:** When the librarian writes the FIRST real entry to a section, it MUST delete the bootstrap placeholder entirely — do not append below it. The placeholder is temporary scaffolding. A section with both placeholder and real content is malformed.

**Detection:** If a section INDEX has `*Section bootstrapped` text AND at least one real content entry, the placeholder must be removed before the write is saved.

---

## Adding Rows to the Root INDEX

When promoting an inbox entry that introduces a new symptom, question, or task:

1. Determine which lane(s) the entry belongs in (see classification rules above).
2. Write the row in the correct table.
3. For Blocked lane: use the exact three-column format: `Symptom | Likely Cause | Go Here`. Make the Symptom column a specific observable failure, not a generic term.
4. For Understand lane: phrase the Question column as a natural question the reader would type.
5. For Do Something lane: phrase the Task column as an imperative ("Deploy a service", not "Service deployment").
6. The "Go Here" / "Where to Look" cell should be a markdown link to the specific file, not a folder. Exception: if the entry is the section INDEX itself (e.g., a broad topic with multiple files), link to the section INDEX.

---

## What Does NOT Get a Root INDEX Row

Not every file warrants a row in the root catalog tables. Reserve root-level entries for:
- Knowledge that a reader would reach for under pressure (Blocked lane)
- Questions that come up repeatedly or in onboarding (Understand lane)
- Tasks that recur or are high-stakes (Do Something lane)

Routine section maintenance, minor gotchas, and supporting detail files should be indexed in their section INDEX only, not promoted to the root.

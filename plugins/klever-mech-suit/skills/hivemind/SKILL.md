---
name: hivemind
description: "Hivemind — your personal knowledge tree that gives Claude persistent memory. Builds and maintains a tree-of-knowledge index where every node is a pointer, never a copy. Uses progressive disclosure so Claude loads only what the current task needs. Use this skill whenever: someone says 'set up my hivemind', 'open my hivemind', 'build my knowledge tree', 'help me organize my context', 'I want Claude to remember', or when someone opens a session and wants Claude to understand their work. Also trigger when someone wants to add a client, index a document, update SOPs, trim their tree, or says things like 'remember this', 'save this for next time', 'where is that template?', 'feed the hivemind'. Anything involving persistent personal context across sessions."
---

# Hivemind — Your Knowledge Tree

## Core Architecture

This system has two foundational principles. Everything else follows from them.

### Principle 1: Progressive Disclosure
Information is organized in layers of depth. The top of the tree is the most compressed, just names and categories. Each level deeper adds more detail. Claude reads top-down and STOPS as soon as it has enough context for the current task. Most tasks only need 1-2 levels. Deep dives into a specific client or workflow go further. But Claude never loads the whole tree into context at once.

This is how a library works: you read the building directory to find the floor, the floor map to find the shelf, the shelf label to find the book. You don't read every book to find one.

### Principle 2: Index, Never Copy
The tree contains POINTERS, not data. Every leaf node is a link: a Gmail search query, a Google Drive path, a Notion page name, a Slack channel reference. The actual content stays where it lives and gets fetched on demand through MCP connectors. This keeps the tree tiny, always current, and never stale.

---

## Step 0: Connector Discovery

Before building any tree, check what tools are actually available. This is not optional. The tree can only point to tools that exist.

1. Check which MCP tools are already connected in this session (Gmail, Google Drive, Google Calendar, Notion, Slack, etc.)
2. For any tool the user mentions but isn't connected, use `search_mcp_registry` to find the connector and `suggest_connectors` to prompt them to connect it
3. Only build tree branches for tools that are actually connected or that the user confirms they use

A typical Klever setup includes: Google Workspace (Gmail + Drive + Calendar), Slack, and Notion. But don't assume. Discover.

After connecting, do a quick scan of each tool to understand what's actually there:
- **Gmail**: Search recent emails to identify key contacts, advertisers, recurring threads
- **Google Drive**: Search for folders, templates, shared drives to understand the file structure
- **Google Calendar**: Check recent/upcoming events to identify recurring meetings, key people
- **Notion** (if connected): Search for databases, pages, workspaces (Klever Wiki, SOPs)
- **Slack** (if connected): Search for channels the user is active in

Use what you FIND to populate the tree. Don't invent anything.

---

## The Tree Format

The knowledge tree lives in `MY_CONTEXT.md` in the user's workspace folder. It uses indentation to represent nesting, just like a file system. Each node is either a BRANCH (a category that contains other nodes) or a LEAF (a pointer to something real).

The format uses this notation:
- Indentation shows depth (2 spaces per level)
- `>` prefix marks a branch (a category)
- `-` prefix marks a leaf (a pointer)
- `→` separates a node name from its location/link
- `|` separates multiple locations for the same node
- `#` is for inline annotations (brief context)

Here's the structural pattern:

```
# [Name] — [Role]
# [One sentence about what they do at Klever]
# Connected tools: [list what's actually connected]

> Clients
  > [Advertiser/Client A]  # [one-line context from real email/doc data]
    - emails → gmail:"from:contact@clienta.com"
    - docs → drive:"Clients/Client A"
    - notes → notion:"Client A"
    - slack → slack:#client-a
    - contacts → Name <email>, Name <email>
    > campaigns
      - Spring 2026 → drive:"Clients/Client A/Campaigns/Spring-2026"
    > proposals
      - Q1 proposal → drive:"Clients/Client A/Proposals/Q1-2026"

> Campaigns
  > [Campaign Name]  # [DSP, flight dates, client]
    - brief → drive:"Campaigns/Campaign Name/Brief"
    - assets → drive:"Campaigns/Campaign Name/Assets"
    - reporting → drive:"Campaigns/Campaign Name/Reports"
    - DSP: [StackAdapt | DV360 | The Trade Desk | Amazon DSP]

> Workflows
  > [Write a Proposal]
    - trigger: new client request or upsell opportunity
    - template → drive:"Templates/Proposal Template"
    - steps: pull client context → copy template → customize → review → send
    - output: Google Doc shared with client
  > [Set Up a Campaign]
    - trigger: signed IO or approved proposal
    - steps: build media plan → upload creatives → configure targeting → QA → launch
  > [Client Reporting]
    - trigger: end of month or campaign flight end
    - template → drive:"Templates/Report Template"

> SOPs
  - campaign setup → notion:"Campaign Setup SOP"
  - proposal writing → notion:"Proposal Process"
  - client comms → notion:"Client Comms SOP"  # response times, escalation
  - pricing → notion:"Pricing Matrix"

> Templates
  - proposal → drive:"Templates/Proposal Template"
  - media plan → drive:"Templates/Media Plan Template"
  - report → drive:"Templates/Report Template"
  - IO → drive:"Templates/IO Template"

> Tools
  - gmail: [what was actually found]
  - drive: [what was actually found]
  - notion: [what was actually found]
  - slack: [what was actually found]
  - calendar: [what was actually found]

> Recent
  - (grows as you work)
```

### How Claude Reads the Tree

When the user says "write a proposal for Client A":

1. **Level 0** — Read the header. Know who this person is and their role. (1 second)
2. **Level 1** — Scan branch names: Clients, Campaigns, Workflows, SOPs, Templates. The task mentions "proposal" and "Client A", so open both.
3. **Level 2** — Under Clients > Client A: see the pointers. Under Workflows > Write a Proposal: see the template and steps. Enough to start.
4. **Level 3** — Only if needed: dive into Client A > proposals to see past work. Or fetch emails via the Gmail pointer.

Claude NEVER reads level 3 or 4 unless the task requires it.

---

## Two Modes

### Setup Mode — First Time
If no `MY_CONTEXT.md` exists in the workspace folder, run the wizard. See the Setup Wizard section.

### Operating Mode — Returning User
If `MY_CONTEXT.md` exists, read it. Scan the top two levels. Go deeper only when a specific task pulls you there. After significant tasks, offer to update the tree.

---

## Setup Wizard

### Step 0 — Discover Connections
Before asking any interview questions, scan what tools are connected. For missing tools the user wants, suggest the connector. Report what you found: "I can see your Gmail, Google Drive, and Calendar. Notion and Slack aren't connected yet, want to add them?"

### Step 1 — Who are you?
One question. Get their name, role, one sentence about responsibilities at Klever.

### Step 2 — Quick Scan
Pull real data from every connected tool:
- Gmail: recent inbox, find recurring senders, identify clients/advertisers
- Drive: top-level folders, shared drives, any "Templates" folder
- Calendar: recurring meetings, events with other people
- Notion/Slack: scan what's there

Show the user what you found: "Looking at your Gmail, I see frequent emails with [person/company]. Your Drive has folders for [X, Y, Z]. Your calendar shows weekly meetings with [people]."

### Step 3 — Who matters?
Based on the scan, suggest clients/advertisers/stakeholders. "It looks like you work with [Client A]. I see emails from [contact] and a Drive folder. Should I add them to your tree?" Let the user confirm, correct, or add more.

### Step 4 — What do you do repeatedly?
Ask about recurring workflows. Suggest common Klever workflows:
- **Campaign setup** (building media plans, uploading to DSPs)
- **Proposal writing** (responding to RFPs, building custom proposals)
- **Client reporting** (pulling campaign metrics, building reports)
- **Client onboarding** (new advertiser setup)

For each, ask: "Is there a template? Where is it?" Then verify by searching Drive/Notion.

### Step 5 — Generate and show the tree
Build `MY_CONTEXT.md` from REAL data. Every pointer should be verified. You searched and confirmed it exists. Show the tree. Explain: "This is your Hivemind. It's small on purpose. It grows every time you work with me."

---

## The Growth Loop

The tree grows organically through use.

### After Every Completed Task
When a task is done and the user is satisfied, offer to update. Be specific:
- "Want me to add [New Client] to your tree so I remember them next time?"
- "I found that template at [real path]. Should I add it to your Templates branch?"
- "We just built a workflow for [thing]. Want me to save the steps?"

### After Every Fetch
When you fetch something via MCP that isn't in the tree yet:
- "I found the report at drive:'Clients/Acme/Reports/Q1'. Not in your tree yet. Add it under Acme > reports?"

### After Every New Contact
If the user interacts with someone new:
- "Looks like Jordan from MediaCo is new. Want me to create a MediaCo branch?"

### When Something Isn't in the Tree
If you search the tree and can't find it, help find it via MCP tools. Once found, offer to index:
- "Not in your tree. Let me search your Drive... Found it at [path]. Want me to index it?"

If you can't find it via MCP tools either, try klever-wiki-search for internal SOPs and documentation.

---

## Tree Maintenance

### Trimming
When the tree exceeds ~100 lines, suggest trimming. Move inactive items to `> Archive`.

### Re-indexing
When a pointer is broken (you search and it's not there), flag it and offer to update.

### Splitting
If a branch gets deeper than 4 levels, suggest a separate file. The main tree keeps a pointer:
```
> Clients
  > Acme Corp → see: acme-context.md
```

---

## What NEVER Goes in the Tree

- Full email contents (use Gmail search pointer)
- Full document text (use Drive/Notion pointer)
- Passwords, tokens, API keys, financial data
- Content longer than 2 lines (if it's long, it's a pointer)

The tree is an INDEX. Data stays in the tools where it's alive and current.

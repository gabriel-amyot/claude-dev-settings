# Tool & Skill Description Audit — 2026-04-03

## Scope
45 skills, 16 agents, 11 plugins across local config, Supervisr, and Klever orgs.

---

## Part 1: Critical Description Deficiencies

### P0 — Missing Org/Platform Routing (High Misroute Risk)

#### 1. `gitlab` skill
**Current:** "Access and query GitLab repositories. List groups, projects, clone repos, and manage merge requests across your GitLab instance. Supports multiple organizations with secure token storage."
**Problem:** No mention that Klever infra lives exclusively on GitLab. No anti-pattern saying "does NOT work with GitHub." No mention that Supervisr uses GitHub, not GitLab for app repos.
**Proposed:**
```yaml
description: "Access and query GitLab repositories (Klever, Origin8 infra). List groups, projects, clone repos, manage merge requests, read CI/CD logs, manage pipeline variables. Use for Klever infrastructure (grp-beklever-com), Origin8 DAC/IAC repos, and any GitLab-hosted repo. Does NOT work with GitHub. For Supervisr app repos, use GitHub (gh CLI) instead. Input: org name or repo path. Returns: repo lists, MR details, pipeline logs."
```

#### 2. `supervisr-github-review` agent
**Current:** "Pragmatic PR reviewer for Supervisr.AI. Fetches GitHub PRs authored by teammates, identifies only high-impact issues, and posts inline comments with a direct, conversational tone."
**Problem:** No anti-pattern. Could be confused with `pr-review` skill or `pr-review-toolkit` plugin.
**Proposed:**
```yaml
description: "Review GitHub PRs for Supervisr.AI repos only. Fetches PRs authored by teammates on GitHub, identifies high-impact issues, posts inline comments. Does NOT work with GitLab MRs (use /gitlab for Klever). Does NOT replace /pr-review (which is for your own PRs, not teammates'). Input: none (auto-discovers). Returns: posted inline comments on GitHub."
```

#### 3. `pr-review` skill
**Current:** "Review a pull request following the established protocol: clone/fetch branch to clean location, read Jira AC, review source files. Never review from local working tree. Use when reviewing PRs or merge requests."
**Problem:** Doesn't say which platform. Doesn't distinguish from `supervisr-github-review` or `pr-review-toolkit`.
**Proposed:**
```yaml
description: "Review a single PR/MR you are actively working on. Clones branch to /tmp for isolation, reads Jira AC, reviews source files against repo standards. Works with both GitHub PRs and GitLab MRs. Use for reviewing your own work before shipping. For reviewing teammates' PRs on GitHub, use supervisr-github-review agent instead. For multi-agent comprehensive review, use /pr-review-toolkit:review-pr. Input: PR/MR URL or branch name. Returns: structured review report."
```

#### 4. `gcloud` skill
**Current:** "Use when the user asks about GCP resources: checking logs, querying Datastore, debugging deployments, Cloud Run errors, service issues..."
**Problem:** Doesn't distinguish Supervisr GCP projects from Klever GCP projects. Both orgs use GCP.
**Proposed:**
```yaml
description: "Query GCP resources for Supervisr.AI and Klever. Check Cloud Run logs, query Datastore, debug deployments, inspect service errors. Project aliases: dev-core, dev-data, uat-core, uat-data, prod-core, prod-data (Supervisr); prj-d-grid-* (Klever). Triggers on: 'check logs', 'what's failing in dev', 'query datastore', or any known project alias. Does NOT manage infrastructure (use Terraform/DAC repos for that). Does NOT run terraform plan/apply. Input: project alias or service name. Returns: logs, entity data, service status."
```

---

### P1 — Ambiguous Scope (Moderate Misroute Risk)

#### 5. `jira` skill
**Current:** Very long description with many triggers. Good coverage but missing:
**Add to end:** "Multi-org: auto-detects org from cwd. When calling from subagents, always pass --org {klever|supervisrai}. Input: ticket key, JQL query, or natural language. Returns: ticket details, search results, or confirmation of creation."

#### 6. `supervisr-release` skill
**Current:** No YAML frontmatter description (just a markdown heading).
**Problem:** Claude must infer purpose from the heading alone.
**Proposed:**
```yaml
description: "Release pipeline for Supervisr.AI microservices only. Runs tests, creates git tag, builds Docker image, publishes GraphQL schema to Apollo. Supports --skip-tests, --no-build, --schema-only, --check-sync. Does NOT work with Klever services (Klever uses GitLab CI pipelines). Does NOT deploy (deployment is handled by CI/CD on tag push). Input: service name or cwd auto-detection. Returns: tag name, build status, schema publish result."
```

#### 7. `supervisr-validate` skill
**Current:** No YAML frontmatter description.
**Proposed:**
```yaml
description: "Pre-release validation for Supervisr.AI services. Runs spec compliance, AC verification, compile, tests, and smoke tests. Auto-detects ticket from branch name. Use before /supervisr-release to catch issues. Does NOT work with Klever repos. Input: none (auto-detects from branch). Returns: structured pass/fail report with AC coverage."
```

#### 8. `supervisr-review` skill
**Current:** No YAML frontmatter description.
**Proposed:**
```yaml
description: "Code review of staged/committed changes in Supervisr.AI repos. Reviews against repo-specific standards (agent-os/standards/) and global CLAUDE.md. Checks code style, test quality, security (OWASP Top 10), API compatibility. Does NOT work with Klever repos (use repo-specific CLAUDE.md standards instead). Input: git diff or file list. Returns: structured review report with severity ratings."
```

#### 9. `test-harness` skill
**Current:** No YAML frontmatter description.
**Proposed:**
```yaml
description: "Manage SPV-3 local test harness for Supervisr.AI integration tests. Build Docker images, start/stop services, run tests, check logs, diagnose failures. For Supervisr services only (lead-lifecycle, EQS, compliance-engine, gateway). Does NOT work with Klever services. Input: harness command (build, start, stop, test, logs). Returns: service status, test results, log output."
```

#### 10. `morning-brief` skill
**Current:** No YAML frontmatter description.
**Proposed:**
```yaml
description: "Process daily morning brief from transcript or recording. Cleans up text, extracts tasks, generates standup script, creates execution plan, and produces steering assessment. Input: /morning-brief [optional-date]. Returns: structured brief with action items."
```

---

### P2 — Missing Input/Output Format

These skills have decent descriptions but would benefit from explicit I/O:

| Skill | Add to description |
|-------|-------------------|
| `archive` | "Input: ticket ID or folder path. Returns: list of promoted artifacts and archive location." |
| `create-tickets` | "Input: epic description or list of stories. Returns: created Jira keys and local scaffold paths." |
| `sprint-close` | "Input: sprint name or ticket list. Returns: closing comments posted per ticket with coverage classification." |
| `adversarial-review` | "Input: test file or test report path. Returns: adversarial findings report with severity classification." |
| `tribal-knowledge` | "Input: natural language question. Returns: answer with source provenance and durability rating (HIGH/MEDIUM/LOW)." |
| `ticket-init` | "Input: ticket ID (e.g., KTP-115). Returns: scaffolded folder at tickets/{ID}/ with INDEX.md, ac.yaml, reports/ tree." |
| `slack-search` | "Input: search query (supports Slack syntax: from:, in:, after:). Returns: matching messages with channel, author, timestamp." |
| `post-comment` | "Input: target (PR URL, Jira key, Slack channel). Returns: posted content URL and audit log entry." |

---

### P3 — Overlap/Confusion Between Similar Tools

#### PR Review Ecosystem (3 tools, unclear routing)
| Tool | When to use |
|------|------------|
| `/pr-review` (skill) | Review YOUR OWN PR/MR before shipping. Single branch, isolated clone. |
| `supervisr-github-review` (agent) | Review TEAMMATES' GitHub PRs for Supervisr repos. Auto-discovers. |
| `/pr-review-toolkit:review-pr` (plugin) | Comprehensive multi-agent review. Spawns code-reviewer, silent-failure-hunter, type-design-analyzer, etc. Use for deep review of complex changes. |

**Recommendation:** Add disambiguation to each description referencing the other two.

#### Post/Comment Ecosystem (skill + agent, same name)
| Tool | When to use |
|------|------------|
| `/post-comment` (skill) | User invokes directly. Pipeline: draft → render → preview → approve → post. |
| `post-comment` (agent) | System-spawned by other agents. Same pipeline but non-interactive. |

**Recommendation:** Rename agent to `post-comment-agent` or add "(agent version, spawned by other agents)" to description.

#### BMAD Party (2 agents, clear but could be clearer)
Already well-differentiated. Good example of anti-pattern usage.

---

## Part 2: Session History Findings

### Routing was clean
- 0 GitHub/GitLab cross-org misroutes detected in last week
- Jira org routing: no evidence of wrong-org queries

### Meta-command overhead
- 73% of commands were non-productive (/buddy, /model, /btw, /login, /rate-limit-options)
- These are NOT tool description problems; they're workflow overhead

### Retry patterns
- 24 retries, only 5 attributed to wrong tool. The other 19 were execution failures (timeouts, errors), not routing failures
- Tool descriptions won't fix this. Better error handling and SESSION_STATE logging will.

---

## Part 3: Klever-Specific Gaps

### Missing tool: Klever GitLab CI routing rule
**Problem:** No explicit rule preventing Claude from trying to use GitHub Actions for Klever CI/CD.
**Fix:** Add to `/gitlab` skill description: "Klever CI/CD runs on GitLab CI. Never use GitHub Actions for Klever repos."

### Missing tool: Klever BigQuery schema validation
**Problem:** `gcloud` skill doesn't mention the BigQuery schema validation gate workflow.
**Fix:** Add to `gcloud` description: "For BigQuery schema validation before wiring adapters, follow ~/.claude/library/context/schema-validation-gate.md."

### `app-user-management` Lombok workaround
**Problem:** This critical build constraint (always append `-Dmaven.compiler.proc=full`) lives only in repo CLAUDE.md. If a subagent doesn't read CLAUDE.md first, builds will fail silently.
**Fix:** This is a CLAUDE.md concern, not a tool description concern. Already handled correctly.

---

## Part 4: Agent Description Improvements

| Agent | Issue | Fix |
|-------|-------|-----|
| `dev-crawl` | Says "For Supervisr dev environment work only" — good. | Add: "Does NOT work with Klever. For Klever, use night-crawl which auto-discovers existing tests." |
| `night-crawl` | Already mentions "For other orgs (e.g. Klever)" — good. | Add I/O: "Input: ticket ID + completion promise. Returns: test results, fix commits, adversarial report." |
| `supervisr-ship` | Vague: "Spec-driven shipping agent." | Add: "For Supervisr.AI repos on GitHub only. Does NOT ship Klever services (Klever ships via GitLab CI tags). Input: ticket ID. Returns: tag, build, deploy status + Jira comment." |
| `pickup-ticket` | Good description. | Add: "Input: Jira ticket key (e.g., SPV-69, KTP-115). Returns: scaffolded ticket folder with Jira context, spec clarity report." |
| `push-adr` | Vague: "Push architectural decisions to agent-os folders." | Add: "Input: decision summary or existing draft ADR path. Returns: created ADR file, updated contracts, cross-references in agent-os/ tree." |
| `mother-base-housekeeper` | Vague: "detects repo drift, missing docs, and infrastructure inconsistencies across the Supervisr workspace" | Add: "Supervisr repos only. Checks CLAUDE.md coverage, config freshness, infra template consistency. Does NOT cover Klever repos (use /mb-doc-housekeeping for DAC repos)." |

---

## Part 5: Quick Wins (Lowest Effort, Highest Impact)

### 1. Add frontmatter to 5 skills missing it
`supervisr-release`, `supervisr-validate`, `supervisr-review`, `test-harness`, `morning-brief` have NO YAML frontmatter. Claude relies solely on markdown headings for routing. Adding proper `description:` fields will dramatically improve routing accuracy for these frequently-used skills.

### 2. Add "Does NOT" clauses to 4 org-specific tools
`gitlab`, `gcloud`, `supervisr-github-review`, `dev-crawl` — each needs one line saying what it does NOT cover.

### 3. Add I/O format to top 8 skills
The 8 skills listed in P2 above. One sentence each: "Input: X. Returns: Y."

### 4. Disambiguate the PR review ecosystem
Add cross-references between `/pr-review`, `supervisr-github-review`, and `/pr-review-toolkit:review-pr`.

---

## Part 6: Token Cost Analysis

Adding the proposed description improvements across all 45 skills and 16 agents would add approximately:
- ~2,500 tokens to skill listing (descriptions are truncated to 250 chars in listings)
- ~800 tokens to agent listing
- **Total: ~3,300 additional tokens per session**

vs. estimated savings from prevented misroutes:
- Each misroute wastes ~5,000-15,000 tokens (wrong tool invocation + retry)
- Even preventing 1 misroute per session pays for the description overhead 2-5x over

**ROI: Strongly positive.** The description investment pays for itself if it prevents even one misroute per 3-4 sessions.

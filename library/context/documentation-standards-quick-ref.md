# Documentation Standards — Quick Reference

Load when: writing or reviewing ADRs, creating docs/, updating agent-os/, or asking "where does this doc go?"

Full standard: `project-management/documentation/process/documentation-standards.md`

---

## The Three-Layer Decision Test

Ask one question before placing any doc:

| Signal | Layer | Location |
|--------|-------|----------|
| Past tense — what happened and why | `docs/` | `docs/adr/` or `docs/architecture/` |
| Present tense — how the system works right now | `agent-os/` | `agent-os/specs/` or `agent-os/standards/` |
| Cross-service, distilled knowledge | Bibliothèque | `bibliotheque/stack/`, `domain/`, `operations/` |

**ADRs always go in `docs/adr/`.** Never in `agent-os/`. Verify: `grep -r "^# ADR" agent-os/` must return empty.

---

## Required Structures

### Every `agent-os/index.md`
Must include a `## Related Services` section:
```markdown
## Related Services
| Service | Relationship | Big Picture |
|---------|-------------|-------------|
| lead-lifecycle-service | Orchestrates call flow | [link] |
```
Without it, agents cannot discover cross-service flows.

### Every `docs/` folder
Must include:
- `README.md` — states purpose, links to documentation-standards.md, lists subfolders
- `INDEX.md` — one-line summary per doc

### Every `docs/adr/` folder
Must include `INDEX.md` — ADR registry table: ID, title, status, scope, date.

### Every Bibliothèque cross-service entry
Must include `## Service-Local Documentation`:
```markdown
## Service-Local Documentation
| Service | Local Slice |
|---------|------------|
| retell-service | `agent-os/specs/architecture/index.md` |
```
Without it, the mesh breaks — agents can't navigate global → local.

---

## ADR Metadata Block (required at top of every ADR)

```markdown
- **Status:** proposed | accepted | deprecated | superseded by ADR-NNN
- **Date:** YYYY-MM-DD
- **Scope:** {service-name} | {app1, app2} | platform-wide
- **Ticket:** SPV-NNN (if applicable)
- **Supersedes:** ADR-NNN (if applicable)
```

Naming: `NNN-kebab-title.md` (3-digit single-service, 4-digit monorepo).

---

## Migration Checklist (per repo)

1. `ls docs/adr/` — ADRs present here, not in agent-os
2. `grep -r "^# ADR" agent-os/` — returns empty
3. `agent-os/index.md` exists and has `## Related Services`
4. `docs/README.md` exists and links to standard
5. `docs/INDEX.md` exists
6. `docs/adr/INDEX.md` exists
7. CLAUDE.md has routing table with `docs/` entries
8. Bibliothèque entries for this repo have `## Service-Local Documentation`

Migration tickets: SPV-156 (LLS, P1) → SPV-161 (origin8-web, P3).

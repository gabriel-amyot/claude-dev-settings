# Operationalize: Local Context

## Org Detection

Resolve from cwd path:
- `grp-beklever-com` → Klever
- `supervisr-ai` → Supervisr
- `origin8` → Supervisr (legacy)
- else → Personal

## Org Path Mappings

| Org | Root | Bibliothèque | Skills |
|-----|------|--------------|--------|
| Klever | ~/Developer/grp-beklever-com | project-management/documentation/bibliotheque/ | ~/.claude/skills/ |
| Supervisr | ~/Developer/supervisr-ai | project-management/documentation/bibliotheque/ | ~/.claude/skills/ |
| Personal | ~/Developer/gabriel-amyot | — | ~/.claude/skills/ |

## Knowledge Write Targets

### Klever
| Type | Path |
|------|------|
| Tribal knowledge inbox | project-management/documentation/bibliotheque/inbox/ |
| Ticket context | project-management/tickets/{PREFIX}/{EPIC-or-no-epic}/{ID}/reports/ |
| Meeting decisions | project-management/general/meetings/DECISIONS_LOG.md |
| ADR drafts | project-management/tickets/{PREFIX}/{EPIC-or-no-epic}/{ID}/architecture/adr/ |
| Promoted ADRs | Affected repo's agent-os/ for repo-specific decisions; project-management/documentation/architecture/ for cross-cutting decisions only |

### Supervisr
| Type | Path |
|------|------|
| Tribal knowledge inbox | project-management/documentation/bibliotheque/inbox/ |
| Ticket context | Resolve the org's current ticket-folder schema before writing |
| ADR drafts | The resolved ticket folder's architecture/adr/ |
| Promoted ADRs | Affected repo's architecture truth source; PM documentation only for cross-cutting decisions |

### Global (any org)
| Type | Path |
|------|------|
| User preference, cross-project | ~/.claude/library/context/ |
| Working memory | This conversation's tracked session state and knowledge manifest; durable knowledge goes to the shared library |

## Conventions

- INDEX.md required after every write (progressive disclosure)
- Never use Claude Code's default memory system. Use library of knowledge.
- Skill proposals queue: `~/.claude/skill-proposals/`

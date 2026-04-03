# Operationalize: Local Context

## Org Detection

Resolve from cwd path:
- `grp-beklever-com` → Klever
- `supervisr-ai` → Supervisr
- `origin8` → Supervisr (legacy)
- else → Personal

## Org Path Mappings

| Org | Root | Library | Skills |
|-----|------|---------|--------|
| Klever | ~/Developer/grp-beklever-com | project-management/documentation/library/ | ~/.claude/skills/ |
| Supervisr | ~/Developer/supervisr-ai | project-management/documentation/ | ~/.claude/skills/ |
| Personal | ~/Developer/gabriel-amyot | — | ~/.claude/skills/ |

## Knowledge Write Targets

### Klever
| Type | Path |
|------|------|
| Project knowledge | project-management/documentation/library/ |
| Ticket context | project-management/tickets/{ID}/reports/ |
| Meeting decisions | project-management/general/meetings/DECISIONS_LOG.md |
| ADR drafts | project-management/tickets/{ID}/architecture/adr/ |
| Promoted ADRs | project-management/documentation/architecture/adr/ |

### Global (any org)
| Type | Path |
|------|------|
| User preference, cross-project | ~/.claude/library/context/ |
| Working memory | ~/.claude/projects/*/memory/MEMORY.md |

## Conventions

- INDEX.md required after every write (progressive disclosure)
- Never use Claude Code's default memory system. Use library of knowledge.
- Skill proposals queue: `~/.claude/skill-proposals/`

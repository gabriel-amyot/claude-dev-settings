# Jira Ticket Description Template

Use markdown formatting. The `markdown_to_jira_wiki()` function in `jira_skill.py` converts:
- `## Header` to `h2. Header`
- `**bold**` to `*bold*`
- `- item` to `* item`
- Numbered lists (`1. item`) pass through as-is (Jira handles them)

## Template

```markdown
{user_story}

## Scope

{scope_items_as_bullet_list}

## Investigation Approach

{approach_steps_as_numbered_list, spikes only}

## Acceptance Criteria

1. **AC-1: {short title}**
   Given {precondition}
   When {trigger}
   Then {observable outcome}
   And {additional outcome if needed}

2. **AC-2: {short title}**
   Given {precondition}
   When {trigger}
   Then {observable outcome}

## Definitions

{definition_items_as_bold_term_followed_by_description}

## Guardrails

{guardrail_items_as_numbered_list, epics only}
```

## Rules

1. Never use em-dash (U+2014), en-dash (U+2013), or double-hyphens as separators. Use commas, periods, colons, or conjunctions.
2. Use markdown headers (`##`) for sections, not `---` separators or ALL-CAPS labels.
3. Acceptance Criteria MUST be an `## Acceptance Criteria` section (H2).
4. ACs MUST be a numbered list (`1.`, `2.`, etc.), not a table or bold paragraphs.
5. Each AC uses the Given/When/Then format with a short title: `**AC-N: {title}**`.
6. No long definitions inside ACs. Keep ACs concise. Definitions go in a separate `## Definitions` section at the bottom of the ticket.
7. When multiple outcomes apply, use `And` on a new line (not a comma-separated list).
8. Keep the user story as the first line, no header needed.
9. Only include sections that have content. Skip empty sections.
10. For spikes: include "Investigation Approach" section. For stories: skip it.
11. For epics with guardrails: include "Guardrails" section on the epic. Children reference the parent.
12. `## Definitions` goes at the bottom, after AC. It is reference material, not the spec.

## Example (Story)

```markdown
As a Proximity Map user, I want the brand/advertiser selector to reflect my actual permissions so I only see brands I have access to.

## Acceptance Criteria

1. **AC-1: Brands sourced from backend**
   Given a user logs into the Proximity Map
   When the brand/advertiser selector loads
   Then the list comes from the IAM/permissions API (not a hardcoded frontend list)
   And the list reflects the user's actual access permissions

2. **AC-2: Empty state handled**
   Given a user with no brand permissions logs in
   When the selector loads
   Then a clear message is displayed explaining no brands are available
   And no empty dropdown is shown
```

## Example (Spike)

```markdown
As the platform security owner, I want all O8-era Auth0 artifacts cataloged so we can safely clean up what is no longer needed.

## Scope

- Enumerate all M2M applications in Auth0
- Code search across O8 and Supervisr codebases
- Produce deletion catalog for Dan's review

## Investigation Approach

1. Enumerate all M2M applications and API permissions/scopes in Auth0 tenant
2. Code search for each permission across both codebases
3. Attach grep evidence for each deletion-eligible entry
4. Deliver catalog for human review

## Acceptance Criteria

1. **AC-1: M2M application catalog with classification**
   Given the Auth0 tenant has been fully audited
   When the spike is complete
   Then a catalog exists listing every Auth0 M2M application
   And each entry has a status of `deletion-eligible` or `reused-in-supervisr-stack`
   And each classification is backed by codebase search evidence

2. **AC-2: Reused credentials documented**
   Given any credential is classified `reused-in-supervisr-stack`
   When the catalog is reviewed
   Then the entry names the specific Supervisr service using it
   And it explains why the credential cannot be removed

## Definitions

**Supervisr stack:** Services in GCP projects with `sprvsr` in the name (sprvsr-core, sprvsr-data, sprvsr-clarif).

**O8-era:** Everything outside `sprvsr-*` projects.
```

# Post-Comment Templates

Templates for `/post-comment`. Organized by intent, not platform. The engine handles platform-specific formatting.

## Available Templates

| Template | Variables | Use Case |
|----------|-----------|----------|
| `review-response.md` | `body`, `action?`, `code?`, `lang?` | Respond to a PR/MR review comment |
| `review-comment.md` | `file`, `line`, `body`, `severity?`, `suggestion?`, `lang?` | Post a new code review finding |
| `pr-description.md` | `summary`, `body`, `testing`, `ticket` | PR/MR description body |
| `status-update.md` | `date`, `body`, `next_steps` | Jira ticket progress update |
| `deploy-comment.md` | `environment`, `body`, `frontend?`, `frontend_version?`, `frontend_link?`, `backend?`, `backend_version?`, `backend_link?`, `mention?` | Post-deploy notice |
| `batch-preview.md` | `count`, `rows`, `first_preview` | Summary table before bulk post |

Variables marked with `?` are optional. They control conditional sections via `{{#var}}...{{/var}}` blocks.

## Draft File Format

Drafts use YAML frontmatter for variables, with the body as markdown content:

```markdown
---
file: src/main/java/Foo.java
line: 42
severity: Warning
---
This method doesn't handle null input. Consider adding a guard clause.
```

The `body` variable is automatically populated from the content after the frontmatter.

## Conditional Sections

Templates support `{{#var}}...{{/var}}` blocks that are included only when the variable is present and truthy:

```markdown
{{#suggestion}}
**Suggestion:**
\```java
{{suggestion}}
\```
{{/suggestion}}
```

## Adding Templates

1. Create a new `.md` file in this directory
2. Use `{{variable_name}}` syntax for placeholders
3. Use `{{#var}}...{{/var}}` for optional conditional sections
4. Add an entry to the table above
5. Attribution is injected by the engine, not the template

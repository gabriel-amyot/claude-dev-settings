---
name: save-process
description: "Captures a completed workflow as a reusable process card. Trigger when: user says 'save this process', 'let's save that', 'remember how we did this', 'save that workflow', or Claude recognizes a multi-step task the user does regularly and suggests saving it. Also trigger on '/save-process'."
---

# Save Process

Captures a completed workflow as a reusable playbook in `references/playbooks/`.

## When to Trigger

1. **User asks**: "save this process", "let's save that", "remember how we did this"
2. **Claude suggests**: After completing a multi-step task that looks repeatable (3+ steps, involves templates or tools, the user does it regularly)

## Steps

### 1. Identify the Workflow
Review the last 10-20 exchanges in the conversation. Extract:
- **Name**: Short, action-oriented (e.g., "Set Up a New Campaign", "Write a Client Proposal")
- **Trigger**: What causes this workflow to start (e.g., "new IO received", "client asks for a proposal")
- **Steps**: Numbered list of what was done, in plain language
- **Tools used**: Which MCP tools or external systems were involved
- **Templates**: Any templates referenced or used
- **Output**: What the finished product looks like

### 2. Confirm with User
Show a summary: "Here's what I captured. Anything to adjust?"

Let them rename, reorder, add, or remove steps. Keep it conversational.

### 3. Write the Process Card
Save to `references/playbooks/{kebab-case-name}.md`:

```markdown
# {Process Name}

**Trigger:** {what starts this workflow}
**Time:** {rough estimate if known}
**Tools:** {list of tools involved}

## Steps

1. {Step one in plain language}
2. {Step two}
3. ...

## Templates

- {template name} → {location pointer}

## Notes

- {Any tips, gotchas, or context from the conversation}
```

### 4. Update Indexes
- Update `references/playbooks/INDEX.md` with the new entry
- Add a pointer under `> Workflows` in `MY_CONTEXT.md` if it exists:
  ```
  > Workflows
    > {Process Name}
      - playbook → references/playbooks/{file}.md
  ```

### 5. Confirm
Tell the user: "Saved. Next time you need to {trigger}, I'll pull up the playbook."

## Rules

- Keep process cards short. Under 30 lines. If a step needs explanation, it's a separate reference doc.
- Use plain language. These are for people, not machines.
- Always verify template pointers actually exist before writing them.
- Never duplicate a process that already exists in playbooks. If similar, ask if this replaces or extends the existing one.

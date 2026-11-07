# Skill Proposal: tool-description-lint
Date: 2026-08-24
Source: KTP-869 live-demo failure — a stale tool description disabled a served tool

## Trigger
Before shipping any MCP server, or whenever a tool is added to / removed from a served set.

## Scope
org (Klever), useful globally for anyone building MCP servers

## Problem it prevents
`draft_bid_change`'s description still said "Applying it is a separate, human step" from an era when
apply was CLI-only. A model read it, concluded no apply tool existed for it, and refused a direct
instruction during a live demonstration. The same response's `next_step` field said the opposite.

## Draft Steps
1. Enumerate the served tool set from the running server (`tools/list`), not from source.
2. For each tool description, flag any phrase asserting a capability is unavailable, manual, or
   handled elsewhere, when a served tool provides it.
3. Flag any description that names a tool NOT in the served set, or fails to name one it points at.
4. Assert exactly one field is designated the runtime availability signal, and that descriptions
   defer to it rather than making their own static claim.
5. Emit a test file pinning the forbidden phrases, so the regression fails rather than ships.

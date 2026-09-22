# Skill Proposal: ast-behaviour-diff
Date: 2026-09-12
Source: prime-lynx — reviewing MR !19 on app-ttd-trading-mcp ("docs only, check the code still works")

## Trigger

Invoke when a review question is "did this change behaviour?" rather than "is this change good":

- A large diff claimed to be documentation-only, comment-only, or a pure refactor
- "Check the code still works as before"
- A rename, reformat, or lint sweep that must be proven inert
- Before green-flagging any MR whose diff is too large to read line by line

## Scope

Global. Python first, since `ast` is stdlib and needs no dependency. The same shape works for any
language with a parseable AST and an available comparison dump.

## Draft Steps

1. Resolve the two revisions to compare (MR base and head, or two shas). Confirm the base is the
   current tip of the target branch, so the answer is not invalidated by drift.
2. For each changed source file, read both revisions with `git show <rev>:<path>` rather than
   checking anything out. No worktree needed for the comparison itself.
3. Parse both, strip every module/class/function docstring, compare `ast.dump`. Comments never
   enter the AST, so comment churn cancels for free.
4. Report per file: IDENTICAL or DIFFERS. A DIFFERS result narrows the read to that one file.
5. When every file is IDENTICAL, state the remaining surfaces a docstring change can still move,
   and check them explicitly. For MCP servers, a `@mcp.tool` docstring is the served tool
   `description` and is prompt text. For public libraries it is the published API documentation.
   An AST match proves the code is inert; it does not prove the artifact is.
6. Only then run the test suite, as confirmation rather than as the primary evidence.

## Notes

Step 5 is the part that makes this more than a convenience. On the source session the AST check
was clean across four files and the MR still changed runtime behaviour, because the docstrings it
rewrote are served to a model on every turn. A skill that stops at step 4 produces a confident
wrong answer.

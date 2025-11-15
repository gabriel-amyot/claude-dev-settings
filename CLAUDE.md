# CLAUDE.md

This file provides comprehensive guidance to Claude Code and other AI assistants when working with this Claude Code configuration repository.

## Repository Overview

This repository contains a comprehensive Claude Code configuration system designed for professional React/React Native development. It provides:

- **Custom Slash Commands**: Pre-built workflows for common development tasks
- **Specialized Agents**: Expert agents for code review and TypeScript error fixing
- **Development Workflows**: TDD and Lean development methodologies with enforcement
- **Quality Standards**: Code review guidelines, commit conventions, and TypeScript/linting best practices
- **Security Configuration**: Comprehensive permissions model protecting sensitive data
- **MCP Tool Integration**: Pre-configured Model Context Protocol tool recommendations

## Directory Structure

```
claude-dev-settings/
├── .claude/
│   └── CLAUDE.local.md          # Local context file (symlinked)
├── agents/
│   ├── code-reviewer.md         # Code review specialist agent
│   └── typescript-error-fixer.md # TypeScript error resolution agent
├── commands/
│   ├── create-prd.md           # Product Requirements Document generator
│   ├── estimate.md             # Ticket analysis and time estimation
│   ├── generate-tasks.md       # Feature task breakdown
│   ├── lean.md                 # Lean development workflow activator
│   ├── process-task-list.md    # Task list processor
│   ├── tdd.md                  # TDD workflow activator
│   └── update-ai-dev-tasks.md  # AI development task updater
├── docs/
│   ├── ai-dev-tasks/          # AI-assisted development task workflows
│   │   ├── create-prd.md
│   │   ├── generate-tasks.md
│   │   └── process-task-list.md
│   ├── guidelines/            # Development standards and guidelines
│   │   ├── code_review_agent.md
│   │   ├── commit_guidelines.md
│   │   └── typescript_lint_fixes.md
│   └── workflows/             # Development workflow definitions
│       ├── lean_workflow.md
│       └── tdd_workflow.md
├── settings.json              # Claude Code permissions and settings
├── .gitignore                # Git ignore rules
└── README.md                 # Setup and usage instructions
```

## Available Slash Commands

### Project Management Commands

#### `/create-prd`
Generate Product Requirements Documents using a structured workflow.
- **Purpose**: Create comprehensive PRDs for new features
- **Workflow**: Guided process defined in `docs/ai-dev-tasks/create-prd.md`
- **Output**: Stores PRD in project's `/tasks` directory

#### `/estimate <ticket-description>`
Analyze tickets and create implementation plans with time estimates.
- **Purpose**: Break down tickets into technical tasks with realistic estimates
- **Process**:
  1. Parse ticket requirements and acceptance criteria
  2. Investigate codebase to identify affected components
  3. Create step-by-step implementation plan
  4. Provide time estimates with breakdown
  5. Recommend sub-task division if needed
  6. Identify risks and testing strategy

#### `/generate-tasks`
Break down features into actionable development tasks.
- **Purpose**: Convert high-level features into specific, implementable tasks
- **Workflow**: Defined in `docs/ai-dev-tasks/generate-tasks.md`

#### `/process-task-list`
Process and organize task lists.
- **Purpose**: Analyze and structure task lists for execution
- **Workflow**: Defined in `docs/ai-dev-tasks/process-task-list.md`

### Development Workflow Commands

#### `/tdd [task-description]`
Activate Test-Driven Development workflow mode.
- **Purpose**: Switch to rigorous TDD methodology
- **Workflow**: 8-step TDD process (see TDD Workflow section)
- **Enforcement**: Mandatory workflow with status announcements
- **Key Principle**: Tests written before implementation, always

#### `/lean [task-description]`
Activate Lean development workflow with quality gates.
- **Purpose**: Rapid development with iterative code review
- **Workflow**: 5-step development process (see Lean Workflow section)
- **Focus**: Requirements analysis → Implementation → Review → Refine → Commit

## Specialized Agents

### Code Review Agent (`agents/code-reviewer.md`)

**When to Use:**
- After implementing new features
- Before committing significant changes
- When refactoring code
- For security and quality assessment

**Capabilities:**
- Principal engineer-level review (20+ years FAANG experience standards)
- Code quality assessment (structure, readability, maintainability)
- Security analysis (vulnerabilities, input validation, auth patterns)
- Best practices verification (separation of concerns, design patterns)
- Test coverage assessment
- Performance optimization identification
- Overfitting detection

**Review Process:**
1. Understand code purpose and context
2. Apply guidelines from `docs/guidelines/code_review_agent.md`
3. Provide constructive feedback with specific examples
4. Prioritize issues by severity (Critical/Major/Minor)
5. Suggest concrete improvements with code examples
6. Acknowledge good practices

**Usage:**
```
# After implementing a feature
"I've implemented the user authentication module. Please review it."
→ Uses code-reviewer agent for comprehensive review
```

### TypeScript Error Fixer Agent (`agents/typescript-error-fixer.md`)

**When to Use:**
- TypeScript compilation errors preventing builds
- CI failures due to type errors
- Post-refactoring type issues
- Pre-commit hook failures
- ESLint/linting errors

**Systematic Approach:**
1. **Analysis Phase**: Examine tsconfig.json, ESLint config, dependencies
2. **Error Discovery**: Run `npx tsc --noEmit` and linting commands
3. **Prioritization**: Fix blocking errors first, then type errors, then linting
4. **Implementation**: Minimal, targeted fixes following guidelines
5. **Validation**: Re-run checks after each fix group
6. **Reporting**: Summarize fixes and suggest preventive measures

**Key Principles:**
- Understand error before fixing
- Prefer explicit typing over `any` or type assertions
- Follow project patterns from `docs/guidelines/typescript_lint_fixes.md`
- Consider impact on other parts of codebase

**Usage:**
```
# When TypeScript errors occur
"CI is failing with TypeScript errors. Please fix them."
→ Uses typescript-error-fixer agent for systematic resolution
```

## Development Workflows

### TDD Workflow (`docs/workflows/tdd_workflow.md`)

**⚠️ MANDATORY: This workflow MUST be followed completely - never compacted or summarized.**

#### The 8-Step TDD Process

**Step 1: Write Tests First**
- Write comprehensive tests defining expected behavior
- Include normal cases, edge cases, error scenarios
- Use explicit input/output pairs
- **Never**: Create mock implementations or production code

**Step 2: Verify Tests Fail**
- Run all tests and confirm they fail for the right reasons
- Document which tests fail and why
- **Never**: Proceed if tests pass (indicates bad tests)

**Step 3: Commit Tests Only**
- Commit with: `test: Add tests for [feature]`
- Tests are now locked specification
- **Never**: Include implementation code

**Step 4: Write Implementation**
- Write minimal code to pass tests
- Iteration cycle: Code → Run tests → Analyze → Fix → Repeat
- **Never**: Modify the committed tests

**Step 5: Quality Review**
- Stop coding completely
- Use Code Review Super Star Agent
- Document findings in review log

**Step 6: Fix Review Issues**
- Address all quality issues systematically
- Re-run tests after each fix
- Document resolutions
- **Never**: Modify original tests

**Step 7: Refactor**
- Improve clarity and readability
- Optimize performance if needed
- Apply DRY principles
- Run linters and fix style issues
- Run tests after each change

**Step 8: Final Commit**
- Perform final review
- Verify all feedback addressed
- Commit with: `feat: Implement [feature]`

#### Status Announcements
Always announce progress:
- ✅ Success: `=== [STEP NAME] COMPLETE - PROCEEDING TO [NEXT STEP] ===`
- ❌ Failure: `=== [STEP NAME] FAILED - REASON: [explanation] - RETRYING ===`

#### Definition of Done
- [ ] Tests written before implementation
- [ ] Tests confirmed to fail initially
- [ ] All tests pass with implementation
- [ ] Linter shows no errors/warnings
- [ ] Zero critical review issues
- [ ] No overfitting confirmed
- [ ] Major issues resolved
- [ ] Documentation updated
- [ ] Separate commits for tests and implementation

### Lean Workflow (`docs/workflows/lean_workflow.md`)

**⚠️ MANDATORY: This workflow MUST be followed completely - never compacted or summarized.**

#### The 5-Step Development Process

**Step 1: Requirements Analysis & Design**
- Analyze requirements thoroughly
- Define expected behavior and edge cases
- Plan implementation approach
- Document key design decisions

**Step 2: Initial Implementation**
- Write implementation based on requirements
- Include error handling for edge cases
- Follow best practices and coding standards
- Use clear variable names and comments

**Step 3: Code Review**
- Stop coding completely
- Use Code Review Agent
- Document all findings
- Analyze for: logic errors, edge cases, performance, clarity, best practices

**Step 4: Iterative Refinement**
- Address all review issues systematically
- Iteration cycle: Fix → Re-review → Document → Repeat
- Run linters and fix style issues
- **Never**: Introduce new features during fixes

**Step 5: Final Review & Commit**
- Perform final code review
- Verify all feedback addressed
- Ensure code is clean and well-documented
- Commit with: `feat: Implement [feature]`

#### Definition of Done
- [ ] Requirements fully analyzed
- [ ] Implementation covers all requirements
- [ ] Code review completed
- [ ] Zero critical issues
- [ ] All major issues resolved
- [ ] Linter shows no errors/warnings
- [ ] Code is well-documented
- [ ] Edge cases handled properly
- [ ] Final review passed

## Code Review Standards

Reference: `docs/guidelines/code_review_agent.md`

All code must meet these standards:

### Review Criteria
- **Correctness**: Logic is sound, handles all cases
- **Test Coverage**: Adequate tests for functionality
- **Security**: No vulnerabilities (XSS, injection, auth issues)
- **Performance**: Efficient algorithms and data structures
- **Maintainability**: Clear, readable, well-structured code
- **Overfitting**: General solutions, not hardcoded to test cases

### Issue Classification
- **🔴 Critical**: Security vulnerabilities, data loss, crashes
- **🟡 Major**: Logic errors, performance issues, maintainability problems
- **🟢 Minor**: Style issues, minor optimizations, documentation

### Review Log Template
```
=== REVIEW CYCLE [#] ===
Component: [name]
Review Type: [checkpoint/overfitting-check/final]
Tests Status: [X/Y passing]

Issues Found:
- 🔴 Critical: [count]
- 🟡 Major: [count]
- 🟢 Minor: [count]

Overfitting Check:
- [ ] Handles cases beyond test inputs
- [ ] No hardcoded test-specific values
- [ ] Edge cases properly handled

Resolutions:
1. [Issue] -> [How fixed] -> [Verified by]
===
```

## Commit Guidelines

Reference: `docs/guidelines/commit_guidelines.md`

### Format
```
<type>: <message title>

<optional bullet points summarizing changes>
```

### Rules
- Title is lowercase, no period at end
- Title max 50 characters, clear summary
- Use body to explain *why*, not just *what*
- Bullet points concise and high-level
- **NEVER** add ads like "Generated with Claude Code"
- Only commit staged files/changes

### Allowed Types

| Type     | Description                           |
|----------|---------------------------------------|
| feat     | New feature                           |
| fix      | Bug fix                               |
| chore    | Maintenance (tooling, deps)           |
| docs     | Documentation changes                 |
| refactor | Code restructure (no behavior change) |
| test     | Adding or refactoring tests           |
| style    | Code formatting (no logic change)     |
| perf     | Performance improvements              |

### Examples

**Good:**
```
feat(auth): add JWT login flow

- Implemented JWT token validation logic
- Added documentation for the validation component
```

**Bad:**
```
Update stuff.
Generated with Claude Code!
```

## TypeScript and Linting Guidelines

Reference: `docs/guidelines/typescript_lint_fixes.md`

### Quick Fix Workflow

1. **Identify error source**: TypeScript compiler or linter
2. **Run checks**:
   - `npx tsc --noEmit` for TypeScript
   - `npm run lint` for linting
3. **Fix systematically**: Type errors first, then linting
4. **Verify fixes**: Re-run checks after each batch

### Project Discovery

```bash
# Check TypeScript configuration
cat tsconfig.json

# Verify dependencies
cat package.json

# Check linting configuration
cat .eslintrc.js || cat .eslintrc.json || cat eslint.config.js
```

### Error Categories

- **Type mismatches** (`TS2322`, `TS2345`): Variable/parameter type conflicts
- **Missing declarations** (`TS7016`, `TS2307`): Module or type definition issues
- **Property errors** (`TS2339`, `TS2551`): Non-existent properties
- **Function signature** (`TS2554`, `TS2556`): Argument count/type mismatches

### Priority Order for Fixes

1. Type errors (prevent compilation)
2. Import/export errors (module resolution)
3. ESLint errors (code quality)
4. ESLint warnings (style/best practices)
5. Prettier formatting (code style)

### Common Fixes

**Unused variables:**
```typescript
// Remove unused code
// Prefix with underscore: _unusedVar
// Or add: // eslint-disable-line @typescript-eslint/no-unused-vars
```

**Missing dependencies:**
```typescript
// Add missing dependencies to useEffect, etc.
useEffect(() => {
  fetchData(id);
}, [id]); // ✅ include 'id'
```

### Automated Fixing

```bash
# TypeScript check
npx tsc --noEmit

# ESLint auto-fix
npx eslint . --fix

# Prettier format
npx prettier --write .
```

### Emergency Fixes (Use Sparingly)

```typescript
// @ts-ignore           // Suppress TypeScript errors
// @ts-expect-error     // Expect an error
/* eslint-disable */   // Suppress ESLint errors
```

**Note**: These are temporary solutions. Always plan to fix properly later.

## Security & Permissions

Reference: `settings.json`

### Allowed Operations
- File operations: `Read`, `Write`, `Edit`, `MultiEdit`, `List`
- Git operations: All standard git commands
- Development tools: `npm`, `npx`, `node`, `python`, `make`, `jq`
- GitHub CLI: `gh` commands
- Vercel CLI: `vercel` commands
- MCP tools: Browser navigation, Context7 library docs

### Denied Operations

**Destructive commands:**
- `rm -rf *`
- `curl *`, `wget *`
- `ssh *`, `scp *`

**Protected files:**
- `*.env*`, `.env.*` - Environment files
- `*secret*` - Secret files
- `*password*` - Password files
- `*.key`, `*.pem`, `*.p12`, `*.pfx` - Key files
- `.ssh/*` - SSH configuration

### Best Practices
- Never commit environment files or secrets
- Use `.gitignore` to exclude sensitive data
- Warn user if they request to commit protected files
- Follow principle of least privilege

## MCP Tools Integration

Pre-configured MCP tools (install via `claude mcp add`):

- **react-mcp**: React development assistance
- **figma-mcp**: Figma design integration
- **github-mcp**: GitHub operations and automation
- **postgres-mcp**: PostgreSQL database operations
- **sqlite-mcp**: SQLite database operations
- **filesystem-mcp**: Advanced file system operations
- **web-search-mcp**: Web search capabilities
- **npm-mcp**: NPM package management

### Installation
```bash
claude mcp add react-mcp npx @modelcontextprotocol/server-react
claude mcp add github-mcp npx @modelcontextprotocol/server-github
# ... etc (see README.md for complete list)
```

## Setup Instructions

### Initial Setup on New Device

1. **Clone repository:**
```bash
git clone <your-private-repo-url> ~/.claude-shared-config
```

2. **Create symbolic links (recommended):**
```bash
ln -sf ~/.claude-shared-config/settings.json ~/.claude/settings.json
ln -sf ~/.claude-shared-config/commands ~/.claude/
ln -sf ~/.claude-shared-config/agents ~/.claude/
ln -sf ~/.claude-shared-config/docs ~/.claude/
```

3. **Or copy files:**
```bash
cp ~/.claude-shared-config/settings.json ~/.claude/settings.json
cp -r ~/.claude-shared-config/commands ~/.claude/
cp -r ~/.claude-shared-config/agents ~/.claude/
cp -r ~/.claude-shared-config/docs ~/.claude/
```

4. **Install MCP tools** (see README.md for complete list)

### Updating Configuration

To sync changes across devices:
```bash
cd ~/.claude-shared-config && git pull
```

## Working with This Repository

### When Modifying Configurations

1. **Test changes**: Symlink to active `~/.claude/` directory for testing
2. **Validate workflows**: Test TDD/Lean workflows with real sessions
3. **Update documentation**: Keep docs in sync with command/agent changes
4. **Document MCP tools**: Add new tools to README.md
5. **Commit properly**: Follow commit guidelines defined above

### Architecture Notes

- **Modular design**: Commands and agents in separate files for easy extension
- **Symbolic linking**: Configuration designed for symlink-based deployment
- **Structured documentation**: Guidelines and workflows in `/docs` for clarity
- **Security-first**: Settings.json enforces comprehensive security model
- **React/React Native focus**: Optimized for modern React development

### Best Practices for AI Assistants

1. **Always read relevant guidelines**: Check `docs/guidelines/` before performing tasks
2. **Follow workflows strictly**: TDD and Lean workflows must not be compacted
3. **Use specialized agents**: Leverage code-reviewer and typescript-error-fixer
4. **Respect permissions**: Never attempt to read or modify protected files
5. **Commit properly**: Follow commit guidelines exactly
6. **Announce progress**: Use status announcements in TDD/Lean workflows
7. **Review thoroughly**: Use Code Review Agent for all significant changes
8. **Document decisions**: Explain reasoning in code comments and commit messages
9. **Test comprehensively**: Ensure tests cover edge cases and error scenarios
10. **Iterate to quality**: Don't settle for "good enough" - follow Definition of Done

## Key Conventions

### File Naming
- Commands: `kebab-case.md` in `/commands`
- Agents: `kebab-case.md` in `/agents`
- Documentation: `snake_case.md` in `/docs`
- Workflows: `snake_case.md` in `/docs/workflows`
- Guidelines: `snake_case.md` in `/docs/guidelines`

### Documentation References
- Use `@docs/path/to/file.md` for referencing documentation
- Use `~/.claude/` for absolute paths in user instructions
- Use relative paths within this repository structure

### Slash Command Format
- Simple activators (e.g., `/tdd`) reference workflow docs
- Complex commands (e.g., `/estimate`) include full instructions
- Always specify where to find detailed workflows

### Agent Frontmatter
```yaml
---
name: agent-name
description: When to use this agent with examples
color: yellow|cyan|green|red
---
```

## Troubleshooting

### Commands Not Working
- Ensure symbolic links are created correctly
- Check `~/.claude/commands/` directory exists
- Verify command files have `.md` extension

### Permission Denied Errors
- Check `settings.json` permissions configuration
- Ensure you're not trying to access protected files
- Review denied operations list above

### Workflow Not Enforcing
- Verify workflow files exist in `~/.claude/docs/workflows/`
- Check command files reference correct workflow paths
- Ensure you've activated workflow with `/tdd` or `/lean`

### MCP Tools Not Available
- Install tools using `claude mcp add` commands
- Check MCP tool configuration in Claude settings
- Verify npx can execute MCP servers

## Version History

**Current Version**: 2024-11 (November 2024)

**Major Changes**:
- Added code-reviewer and typescript-error-fixer agents
- Comprehensive TypeScript lint fixing guidelines
- Enhanced commit guidelines with examples
- Expanded security permissions model
- MCP tool integration recommendations
- TDD and Lean workflow refinements

---

## Quick Reference

### Most Used Commands
- `/tdd` - TDD workflow
- `/lean` - Lean workflow
- `/estimate` - Ticket analysis
- `/create-prd` - PRD generation

### Most Used Agents
- `code-reviewer` - Code quality review
- `typescript-error-fixer` - Type error resolution

### Essential Guidelines
- `commit_guidelines.md` - How to commit
- `code_review_agent.md` - Review standards
- `typescript_lint_fixes.md` - Fix type errors

### Essential Workflows
- `tdd_workflow.md` - 8-step TDD process
- `lean_workflow.md` - 5-step lean process

---

**Remember**: This configuration system is designed to enforce quality, security, and best practices. Always follow the defined workflows and guidelines to ensure consistent, high-quality code delivery.

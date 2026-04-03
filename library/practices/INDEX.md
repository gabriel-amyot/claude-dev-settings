# Practices

How to do things well. Methodologies, checklists, workflows, and standards. 28 books across 9 sections.

## Sections

### development/ — Core development patterns
| File | Summary |
|------|---------|
| `test-driven-development-red-green-refactor.md` | TDD methodology: test-first, red-green-refactor cycle, quality gates (364 lines) |
| `subagent-driven-development-specialized-tasks.md` | Delegating specialized work to subagents for focused execution (189 lines) |
| `condition-based-waiting-async-patterns.md` | Asynchronous waiting patterns for conditional task execution (120 lines) |
| `finishing-development-branch-cleanup-merge.md` | Branch completion: cleanup checklist, testing, merge protocol (200 lines) |
| `using-git-worktrees-isolated-branches.md` | Git worktree usage for parallel isolated branch work (213 lines) |

### testing/ — Testing practices and anti-patterns
| File | Summary |
|------|---------|
| `testing-anti-patterns-and-refactoring.md` | Common anti-patterns (flaky tests, over-mocking) and how to fix them (302 lines) |
| `testing-skills-with-subagent-harnesses.md` | Validating skill definitions using subagent-based test harnesses (387 lines) |
| `verification-before-completion-protocols.md` | Verification protocols to confirm task completion quality (139 lines) |

### debugging/ — Failure investigation
| File | Summary |
|------|---------|
| `systematic-debugging-failure-trace-hypothesis.md` | Methodology: failure trace analysis, hypothesis formation, verification (295 lines) |
| `root-cause-tracing-investigation-artifacts.md` | Root cause analysis: investigation patterns, artifact collection (174 lines) |
| `find-polluter.sh` | Shell utility: identifies problem-causing commits or changes (63 lines) |

### collaboration/ — Working with others
| File | Summary |
|------|---------|
| `requesting-code-review-preparation-guide.md` | How to prepare and request code reviews effectively (105 lines) |
| `receiving-code-review-incorporating-feedback.md` | How to receive, triage, and incorporate review feedback (209 lines) |
| `code-reviewer-persona-guidelines.md` | Code reviewer persona definition and review guidelines (146 lines) |
| `sharing-skills-distribution-patterns.md` | Skill sharing: packaging, distribution, versioning patterns (194 lines) |
| `dispatching-parallel-agents-coordination.md` | Coordinating multiple parallel agents: dispatch, collect, synthesize (180 lines) |

### writing/ — Communication and prompt engineering
| File | Summary |
|------|---------|
| `writing-skills-persuasion-clarity-structure.md` | Comprehensive: persuasion, clarity, structure, tone adaptation (622 lines) |
| `anthropic-best-practices-prompt-design.md` | Anthropic's best practices for effective prompt and instruction design (1150 lines) |
| `persuasion-principles-communication.md` | Persuasion and communication principles for AI contexts (187 lines) |

### planning/ — Plan creation and execution
| File | Summary |
|------|---------|
| `writing-effective-implementation-plans.md` | How to write clear, actionable implementation plans (116 lines) |
| `executing-pre-written-plans.md` | Executing plans: tracking, adaptation, completion criteria (76 lines) |
| `brainstorming-ideation-problem-framing.md` | Ideation techniques: creative exploration, problem reframing (54 lines) |

### quality/ — Quality assurance and security
| File | Summary |
|------|---------|
| `code-review-priority-checklist.md` | Priority order: correctness > test independence > coverage > security > perf > maintainability |
| `defense-in-depth-layered-security-patterns.md` | Layered security: fail-safes, input validation boundaries, trust zones (127 lines) |

### standards/ — Coding standards and conventions
| File | Summary |
|------|---------|
| `commit-message-conventional-format.md` | Conventional commit format (`type:message`) with examples (57 lines) |
| `typescript-lint-fix-workflow.md` | TypeScript and lint error fixing: discovery, systematic fix, verification (140 lines) |

### workflows/ — Activatable development modes
| File | Summary |
|------|---------|
| `tdd-workflow-test-first-quality-gates.md` | TDD mode: test-first discipline, quality gate enforcement (142 lines) |
| `lean-workflow-minimal-process-rapid-iteration.md` | Lean mode: minimal overhead, rapid iteration, waste elimination (138 lines) |

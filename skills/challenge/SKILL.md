---
name: challenge
description: "Challenge recent work, ideas, or design decisions. Frames an adversarial review of implementation choices, architecture, or any work product. Use when you want a critical second opinion on what you just built or decided. Does NOT challenge test validity (use /test-adversarial for that). Input: description of work to challenge, file paths, or 'last N prompts'. Returns: adversarial findings with risk assessment and alternatives."
user_invocable: true
---

# Challenge — Adversarial Work Review

## Purpose
Provide a critical, adversarial perspective on recent work, decisions, or ideas. This is NOT a test validator (use /test-adversarial for that). This challenges the *thinking* behind the work.

## When to Use
- After completing a feature or significant code change
- When you've made architectural or design decisions and want them stress-tested
- When you want a "devil's advocate" perspective on your approach
- When reviewing your own or someone else's implementation choices

## Input
- Describe the work to challenge, OR
- Provide file paths to review, OR
- Say "challenge the last N prompts" to review recent conversation work

## Process
1. **Understand the intent** — What was the user trying to accomplish?
2. **Identify assumptions** — What assumptions underpin the approach?
3. **Challenge each assumption** — Is there evidence against it? What if it's wrong?
4. **Find alternatives** — What other approaches could work? What are their trade-offs?
5. **Assess risk** — What could go wrong with the chosen approach?
6. **Rate severity** — CRITICAL (will fail), HIGH (likely problems), MEDIUM (worth considering), LOW (minor concern)

## Output Format
```
## Adversarial Review

### Assumptions Challenged
1. [Assumption] — [Why it might be wrong] — Severity: [CRITICAL/HIGH/MEDIUM/LOW]

### Alternative Approaches
1. [Alternative] — [Trade-offs vs current approach]

### Risk Assessment
- [Risk 1]: [Impact] + [Likelihood]

### Verdict
[Overall assessment: proceed as-is, reconsider X, or stop and rethink]
```

## Anti-patterns
- Do NOT use this for test validity challenges → use /test-adversarial
- Do NOT use this for AC/ticket quality → use /ticket-scan
- Do NOT use this for code style/standards → use /supervisr-review or /pr-review

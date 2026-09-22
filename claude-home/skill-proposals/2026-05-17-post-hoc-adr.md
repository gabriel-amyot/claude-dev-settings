# Skill Proposal: post-hoc-adr
Date: 2026-05-17
Source: KTP-669 design review session

## Trigger
After an agent-implemented feature ships and the developer wants to review the design decisions before debugging. "Review the architecture", "explain the design", "write an ADR for this", "what decisions were made".

## Scope
org (Klever, potentially global)

## Draft Steps
1. Read the implementation diff (git log + changed files)
2. Extract all design decisions (architectural patterns, state management, data flow)
3. For each decision: document rationale, alternatives considered, consequences
4. Draw state/sequence diagrams (mermaid or ASCII)
5. Run fair adversarial review: challenge each decision without agenda
6. Write draft ADR to ticket folder
7. Present to developer for calibration

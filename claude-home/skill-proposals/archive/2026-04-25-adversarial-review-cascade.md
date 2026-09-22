# Skill Proposal: adversarial-review-cascade
Date: 2026-04-25
Source: KTP-130 overnight sprint adversarial review

## Trigger
After any major overnight sprint, implementation phase, or before shipping. "Review everything", "adversarial review", "full audit".

## Scope
global

## Draft Steps
1. Dispatch 6 BMAD personas in parallel: Dexter (process), Winston (architecture), Quinn (code), Adversarial General (claims), PM (project health), PO+Leo (features)
2. Each reads persona file, reviews designated domain, writes structured report
3. Synthesize findings into consolidated severity table (CRITICAL/HIGH/MEDIUM/LOW)
4. Fix CRITICAL and HIGH findings immediately in the same session
5. Commit all reports and fixes, post summary

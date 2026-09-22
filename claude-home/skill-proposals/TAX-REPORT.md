# Skill Tax Report

Skills measured: 89.
Total description characters loaded every session: **33,869** (~8,467 tokens).
Mean per skill: 380 chars.

This is the standing cost of the skill set. Bodies are not counted —
they load only on invocation. A narrow skill that never fires costs
only its description line, which is why a raw skill count is a poor
proxy for bloat.

## The 20 most expensive descriptions

| Skill | Chars | Generic-word % |
|---|---|---|
| ui-probe | 1,454 | 1.3 |
| feedback-to-spec | 812 | 4.2 |
| klever-test | 791 | 2.4 |
| sprint-factory | 785 | 1.7 |
| meeting-to-action | 763 | 3.7 |
| dark-factory | 756 | 6.5 |
| crawl-adversarial-review-cascade | 742 | 17.2 |
| deploy-identity | 729 | 3.6 |
| klever-mr | 707 | 7.0 |
| skill-evals | 693 | 6.2 |
| klever-data-pipeline | 686 | 5.8 |
| service-factory | 682 | 3.7 |
| harness-audit | 639 | 3.3 |
| um-local-grant | 614 | 3.7 |
| jira | 609 | 17.5 |
| pr-review | 603 | 11.7 |
| gcloud | 591 | 14.3 |
| java-quality | 581 | 0.0 |
| bibliotheque-librarian | 506 | 4.3 |
| adversarial-cascade | 500 | 7.4 |

The top 20 account for 14,243 chars, 42% of the total.

## Broad AND expensive — the ones worth rewriting

Long description built largely from generic verbs. These are the
mis-trigger risks: they cost the most to carry and match the most
situations they were not written for.

| Skill | Chars | Generic-word % |
|---|---|---|
| crawl-adversarial-review-cascade | 742 | 17.2 |
| jira | 609 | 17.5 |
| pr-review | 603 | 11.7 |
| gcloud | 591 | 14.3 |
| create-tickets | 496 | 10.4 |
| challenge | 430 | 15.6 |
| test-adversarial | 388 | 17.5 |
| graphify | 353 | 11.3 |
| har-diagnostic | 349 | 13.5 |
| epic-reorganization | 346 | 9.6 |
| index-context | 318 | 9.3 |
| cloudflare-pages | 307 | 10.9 |

## Missing a description (never routes correctly)

- agent-os:audit-docs
- push-adr

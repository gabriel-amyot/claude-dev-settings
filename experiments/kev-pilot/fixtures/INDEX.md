# Diagnostic fixtures

- [diagnostic_queries.jsonl](diagnostic_queries.jsonl): Twenty-four authored global-library retrieval challenges with sparse relevance judgments.
- [blind-review-grades.json](blind-review-grades.json): Fresh page-support judgments without expected labels or model outputs.
- [label-review-comparison.json](label-review-comparison.json): Unadjudicated disagreements between authored and fresh diagnostic grades.

These are developer-authored diagnostics, not an independent holdout or a labeled production distribution. Labels describe relevance, not truth or currency. Unlisted documents remain unjudged. No-match cases express test intent and do not establish complete corpus absence. The category `suppressed_prompt` deliberately exposes an existing hook policy difference. It cannot support a model-only improvement claim. Group related requests together in later dataset splits. Never include labels in model inference inputs.

The fresh review covers 127 query-page pairs across 24 requests. Three of 28 overlapping grades differ. These are unadjudicated diagnostic judgments. The registered inference fixture remains unchanged. The recovery-page example is absent even from the metadata baseline's eight returned candidates, so reranking cannot repair that case. This is a diagnostic candidate-coverage observation, not a population recall estimate.

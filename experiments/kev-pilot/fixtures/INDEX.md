# Diagnostic fixtures

- [diagnostic_queries.jsonl](diagnostic_queries.jsonl): Twenty-four authored global-library retrieval challenges with sparse relevance judgments.

These are developer-authored diagnostics, not an independent holdout or a labeled production distribution. Labels describe relevance, not truth or currency. Unlisted documents remain unjudged. No-match cases express test intent and do not establish complete corpus absence. The category `suppressed_prompt` deliberately exposes an existing hook policy difference. It cannot support a model-only improvement claim. Group related requests together in later dataset splits. Never include labels in model inference inputs.

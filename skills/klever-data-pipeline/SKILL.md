---
name: klever-data-pipeline
description: "Explore and interrogate the Klever data pipeline knowledge from Marc-André's knowledge-transfer sessions (ingestion CSV->BQ, Dataform, Generic DSP normalization, cost/billing, demo data, BI-agent security, the Buying Agent vision). Use when the user asks how the Klever data pipeline works, 'how would Marc-André do X', about BigQuery cost, Dataform tags, Generic DSP, demo data loading, store locations, dev/prod data parity, DSP scaling (Airflow/Snowflake), or wants to be quizzed on the material. Triggers: 'data pipeline', 'how does ingestion work', 'Generic DSP', 'Dataform', 'BigQuery cost', 'demo data', 'BI agent security', 'Buying Agent', 'quiz me on the pipeline'. Klever org."
user_invocable: true
nav:
  bay: know
  when: "Answer questions about the Klever data pipeline / Dataform / BigQuery architecture from Marc-André's KT sessions. Explore from many angles, quiz, find quotes, trace topics."
  when_not: "Live BQ queries (use klever-bq-store-lookup or gcloud). Running Dataform (do it in the GCP UI). Generic Jira/ticket work."
  org: [klever]
---

# Klever Data Pipeline — knowledge tutor

A queryable layer over Marc-André's 2026-06-12 knowledge-transfer sessions on the Klever data pipeline. Answers from many angles, grounded in distilled docs + the verbatim transcript.

**Source of truth (read on demand, never bulk-load all of it):**
`~/Developer/grp-beklever-com/project-management/general/knowledge-transfer/marc-andre-2026-06-12/`
- `distilled/00-MASTER-BRIEF.md` — the map, glossary, open questions. **Read this first, every time.**
- `distilled/01-ingestion-pipeline.md` — CSV→BQ Cloud Function, filedefinitions.yaml, write methods, DDI/TTD.
- `distilled/02-dataform-transformation.md` — Dataform, Generic DSP, crash isolation, lineage tracing, running it.
- `distilled/03-demo-data-and-locations.md` — store locations, geoloc microservice, demo-data system.
- `distilled/04-cost-and-billing.md` — BigQuery economics, partition/cluster, SKU, medallion-ish layers.
- `distilled/05-agentic-future-and-security.md` — DSP scaling, Buying Agent, BI-agent SQL-rewrite gateway, docs, CI future.
- `distilled/ACTION-CHECKLIST.md` — what Gabriel must do himself.
- `transcripts/session1_70min.clean.txt`, `session2_43min.clean.txt` — verbatim (cleaned). Grep these for exact quotes.
- `frames/sessionN_*.png` — screen frame every 30s (frame K ≈ K×30s). `distilled/DECK-session{1,2}.md` pairs frames with transcript.

## How to answer (workflow)

1. **Always read `00-MASTER-BRIEF.md` first** to ground terminology and the map.
2. Pick the topical doc(s) matching the question and read them. Only read the transcript when the user wants an exact quote, a nuance not in the distilled docs, or to verify.
3. To find a quote or check a detail: `grep -i` the `.clean.txt` transcripts. Cite with the session + approximate timestamp (transcript lines are ~ chronological; the `.srt` files have exact times).
4. **Honor the fidelity rule:** identifiers flagged `[verify]` in the docs are ASR best-guesses. Never assert an exact table/service name as fact. If the user needs the real name, say it's unverified and point them to the repo/BigQuery to confirm.
5. Whisper hears "Klever" as "Clover/Claver" — normalize silently.

## Modes (infer from the ask, or let the user pick)

- **Explain** — "how does X work?" → distilled doc, structured answer, with the *why*.
- **Marc-André's-take** — "how would Marc-André do X / what does he think about Y?" → answer in his stated reasoning (cost-reactive, crash-isolation, generic-DSP-sacred, demo-in-real-tables, agents-make-PRs). Quote when useful.
- **Trace** — "where does table/feature X come from?" → walk the lineage technique from `02` (normalization doc → Dataform → dependencies/ JSON → microservice).
- **Quiz** — generate questions from the docs, grade answers, fill gaps. Good for Gabriel internalizing it.
- **Quote** — find the exact verbatim passage (grep transcripts) + timestamp + frame reference.
- **Do** — "what do I need to do about X?" → `ACTION-CHECKLIST.md`, scoped to the topic.
- **Gaps** — list the open questions / `[verify]` items relevant to the topic and who owns them.

## Guardrails

- This skill reports the knowledge; it does not run Dataform, mutate BigQuery, or post externally.
- When the knowledge conflicts with current code/BQ, the code/BQ wins — flag the doc as stale and suggest updating it (the docs are derived from one KT session, not ground truth).
- Keep answers grounded: prefer "Marc-André said …" over invented detail. If it's not in the material, say so.

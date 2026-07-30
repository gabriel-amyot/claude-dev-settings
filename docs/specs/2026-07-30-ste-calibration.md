# STE Calibration — findings (2026-07-30)

Corpus: 15 approved `.posted` external comments (Jira/MR/Slack), lint via `evals/ste/calibrate.py`.

## Score distribution (violations per 100 words)

| stat | value |
|---|---|
| min | 2.07 |
| p50 | 4.35 |
| p75 | 4.68 |
| p90 | 6.66 |
| p95 | 7.07 |
| max | 8.55 |
| mean | 4.39 |

## The finding that matters

Gabriel's approved posts trip almost entirely on **grammar/style** checks, not AI-slop checks:

| check | total hits | is it "AI slop"? |
|---|---|---|
| long_sentence(>20w) | 77 | no — his sentence length |
| contraction | 49 | no — his human voice ("don't", "it's", "I'd") |
| passive_voice | 32 | partly |
| semicolon | 29 | style |
| ing_main_verb | 5 | style |
| marketing_adjective | 0 | **yes — never fires** |
| modal_hedge | 0 | **yes — never fires** |
| phrasal_verb | 0 | **yes — never fires** |
| banned_word | 0 | **yes — never fires** |
| nominalization | 0 | **yes — never fires** |

The six AI-slop patterns (the actual target) score ~0 on Gabriel. His violations are contractions and long sentences — which his own external-voice rule deliberately allows (`feedback_human_voice_external_messages`: write like a human, use "don't").

## Consequence for the hard gate

A naive full-score gate (block if total > N) would fight Gabriel's own voice: it would flag his contractions and sentence length, not AI slop. To not block his historical good posts, N would have to sit above 8.55 — so high it catches almost nothing.

The better gate splits the score:
- **slop-subset score** = marketing + hedge + phrasal + banned + nominalization. Gabriel's corpus = ~0. Gate this near zero to block AI drift without touching his voice.
- **grammar checks** (long sentence, contraction, passive, semicolon) = keep advisory (shown, not blocked), or soften contraction to a soft marker like em-dash.

Decision pending (see gate options presented to Gabriel).

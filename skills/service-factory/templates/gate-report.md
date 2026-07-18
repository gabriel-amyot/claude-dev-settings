# Gate report (S14) — the ONLY relay format at gates, ≤12 lines, /caveman

Every gate touchpoint emits exactly this. Rich detail goes to the linked files,
never the chat. CLOCK/SPEND/LOOPS on every one (the governor is always visible).

```
GATE: <name>        CLOCK: 38m   SPEND: ~$6   LOOPS: 1/3
STATUS: <one line>
OBSERVED: O7 [OBSERVED] … · O9 [OBSERVED] …
RULED OUT: H1 (strong, own-env) · H4 (weak — cross-env)
NEXT: <cheapest act + cost>
NEED FROM YOU: <the question + options; PARK always one>
EXPRESS: taken|declined — <one-line reason>
PARKED: n    LINKS: board.yaml · observations.yaml · rca.md
```

Rules:
- `NEED FROM YOU` always lists PARK as an option (timeout → park, never a silent default).
- On a pulse, exactly 4 options: park / ask reporter / shrink scope / new named budget.
  If a decisive burst is in flight, add a 5th: `await in-flight decisive burst (ETA …)` (IFM-13).
- `PARKED: n` counts parking-lot entries; they are drained only at Phase 9.

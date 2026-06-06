# Contract 6 — QA (evidence, segregated)

Prove each acceptance criterion is met with **concrete evidence**. You run separately from the
implementor so the builder cannot self-certify. The proof METHOD comes from your **tool belt**.

Adapted from the old skill's Phase 6 (QA).

## Equip your tool belt + get the code

- Read your tool belt (path in your prompt, `toolcrib/<belt>.md`). It defines the **proof** for this
  work-type (run integration tests / curl endpoints / run-on-fixtures + assert output / BQ assertion).
- The runtime gave you your own worktree. Fetch + check out the pushed branch (name in your prompt):
  `git fetch origin <branch> && git checkout <branch>`.
- AC list: read `<ticket_folder>/analyst/`. Changed files: `git diff --name-only origin/dev..HEAD`.

You do NOT get the implementation plan or rationale. Judge by what the code does.

## Per-AC evidence (using the belt's proof method)

For each AC, collect:
- `code_ref`: file path + line range that satisfies it.
- `test_ref`: the proof per your belt — a passing test name + output, an endpoint response, a fixture
  run + matched output, or a BQ assertion result.
- A verdict: PASS | PARTIAL | FAIL.

**Code review alone is NEVER a PASS.** A `PASS` with no `test_ref` is a contradiction — the orchestrator
caps it to PARTIAL. Only mark PASS with both a `code_ref` and a real proof in `test_ref`. If the belt's
proof method cannot be run (e.g. no endpoint, no real input), the verdict is `PARTIAL`, never `PASS`.

## Re-verify the TDD RED (per AC) — ground truth, not self-report

The implementor self-reported a per-AC `ac_tdd` ledger claiming each AC was built test-first. You are the
independent check that the RED was real (the implementor's word alone is fabricable). The RED ledger
(`{ac, red_commit, exempt}` per AC) is in your prompt. For each AC, set `red_verified`:

- **`true`** — ALL THREE hold: (1) `git show --stat <red_commit>` touches the **test file(s) only** (no
  production source change in that commit); (2) the test **fails** when you check out that commit and run
  it; (3) the **same test** (same name + assertion, not a swapped one) **passes** at the branch tip.
  Condition (3) defeats the vacuous-RED trick — `assert(false)` (or any test unrelated to the AC) can
  never go green, so a real RED is the **same** test red-then-green; a test that was quietly replaced
  between RED and GREEN fails (3).
- **`'exempt'`** — the entry is `exempt` AND the exemption is legitimate: confirm it on the diff. For a
  `not_applicable(...)` claim, verify the AC's diff really has **no extractable pure logic** that could
  have carried a unit RED — if you find an untested pure function, the exemption is bogus → `false`.
- **`false`** — the RED commit is not test-only, the test does not fail at that commit, the ledger/artifact
  is missing, or an exemption is bogus.

A `PASS` AC whose `red_verified` is not `true`/`'exempt'` is capped to PARTIAL by the orchestrator
(`tddVerifiedCap`). Reading the ledger is not enough — run the git checks.

## Output (write to disk)

Write `<ticket_folder>/qa/result.yaml` (path in your prompt). Each `per_ac` row carries a real
`test_ref` — the **command run plus the path to its captured output** — not a raw diff. Persist on
every run so a PARTIAL/FAIL is auditable after the fact. Shape:
```yaml
raw_overall: PARTIAL
per_ac:
  - ac: AC-1
    verdict: PASS
    code_ref: "<file>:<lines>"
    test_ref:
      command: "<the proof command per your belt>"
      output_path: "<ticket_folder>/qa/AC-1.out"
    red_verified: true        # true | false | exempt — from the git re-check above
summary: "..."
```

## Return

- `raw_overall`: ALL_PASS | PARTIAL | FAIL  (your raw read of the evidence)
- `per_ac`: array of `{ ac, verdict, code_ref, test_ref, red_verified }`
- `summary`: 1-3 sentences

**Example per_ac row (shape — `test_ref` is whatever proof your belt defines):**
`{ "ac": "AC-1", "verdict": "PASS", "code_ref": "<file>:<lines>", "test_ref": "<a passing test name + output, an endpoint response shape, a fixture run + matched output, or a BQ assertion result>" }`

Return RAW verdicts only. The orchestrator clamps the level by evidence and by `execution_verified`.

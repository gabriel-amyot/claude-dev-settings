# Retirement verdict (evidence standard)

Use this when the audit names a retirement candidate, or the user asks "do we still need X", "is X dead weight", "consolidate these skills". The audit produces a verdict with an evidence trail. It does not approve retirement. The user decides.

A code diff shows overlap. It does not show usage. Retirement needs several independent evidence sources that converge.

## Evidence steps

Run every step and record what each one found.

1. **Mechanism diff.** Compare the candidate with its suspected replacement. Name the specific overlap: same inputs, same core loop, same output shape. "They sound similar" is not overlap.
2. **Creation commit.** Read the full message of the commit that created the candidate (`git log --diff-filter=A -- <path>`). The author often states an assessment there.
3. **Sibling decision doc.** Search the harness repo and the org knowledge library for a proposal or decision doc about the candidate. A prior session may have decided already and nobody acted.
4. **Independent corroboration.** Search friction audits, harness reviews and retros for the candidate, flagged without prompting. Several reports that repeat one original assessment count as one source.
5. **Invocation evidence, with coverage.** Look for real use: a handoff that was picked up, a report-back, ledger or session-archive activity, catalog invocation records. Report one of three results:
   - `observed_use`: there is evidence the candidate ran. Name it.
   - `no_use_full_coverage`: no use, AND the sources cover the whole period and every runtime path. State the period and the sources.
   - `unknown_coverage`: no use found, but coverage is partial (quoted-text scans, missing runtime sources, short window). This is NOT evidence of non-use.

## Verdict

| Result | Condition |
|---|---|
| `RETIRE_RECOMMENDED` | Steps 1 to 4 converge AND step 5 is `no_use_full_coverage` |
| `CONSOLIDATE_RECOMMENDED` | Overlap is real, but step 5 is `observed_use` |
| `INCONCLUSIVE` | Steps conflict, or step 5 is `unknown_coverage`. Say which steps conflict. Do not force a verdict. |
| `KEEP` | No real overlap |

## If the user approves retirement

Archive, never delete:

1. Move the skill with `git mv` to an `_archive/<name>/` folder in the same tree.
2. Add a retirement banner at the top of the body (keep the frontmatter): what was retired, why, and where the decision lives.
3. Update every routing table, index and doc that names the skill as live.

Destructive steps run only in `--apply` mode, after the user approves each one.

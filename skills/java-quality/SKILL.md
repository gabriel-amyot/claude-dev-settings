---
name: java-quality
description: "Everything that checks Java before a human has to. Controls the always-on PMD gate (turn it off, relax a rule, tune thresholds, scan a repo, opt a repo in) and runs on-demand typechecking that catches compile and type errors PMD is blind to. Triggers on: 'java quality', 'the linter is too strict', 'turn off the java gate', 'stop blocking on X', 'why is PMD complaining', 'lint my java', 'scan this repo', 'does this compile', 'typecheck this', 'check my java', 'why won't this build', 'is this java correct', 'tune the thresholds', 'the gate is annoying'. Klever org, Java repos."
user_invocable: true
nav:
  bay: fix
  when: "Adjust, silence, diagnose or run Java checking. Any complaint that Java linting is too strict, too noisy, or not working. Any question of whether Java compiles or typechecks."
  when_not: "Reviewing a diff or plan (use /crit). Runtime behaviour and live bugs (use /investigate). Creating an MR (use /klever-mr)."
  org: [klever]
---

# Java Quality

**Usage:** `/java-quality [command]`

```bash
python3 ~/.claude/skills/java-quality/java_quality.py <command>
```

### Where the rules live

The ruleset is **personal config**, not a product artifact:
`~/.claude/skills/java-quality/klever-java-rules.xml`, version controlled in
`claude-dev-settings`. It applies to every Java file edited, in any repo, with
no footprint in any Klever repo.

These are one engineer's standards, not a ratified team standard. They do not
belong in a shared product repo until the team agrees and CI consumes them.
A repo-level `config/pmd/klever-java-rules.xml` therefore means "the team
ratified this" and takes precedence when present. `adopt` is the promotion
path.

Never hand-edit `~/.claude/pmd-java-gate.json` or the ruleset XML. This CLI
validates every change against PMD and rolls back anything PMD refuses to load.
Hand-editing can silently kill the gate, which is worse than no gate: it prints
a green check over code nobody checked.

## Two engines, one door

| | Gate: PMD + Checkstyle | Typecheck (jdtls) |
|---|---|---|
| When | automatic, every Java edit | you ask |
| Cost | ~2s (PMD 1.0s + Checkstyle 0.6s) | ~8s warm, ~10s cold |
| State | none | cached workspace index |
| Catches | raw `Object` return, `return null`, complexity, magic literals, javadoc bloat, swallowed exceptions, unused imports, naming, fall-through, equals/hashCode | does not compile, type mismatch, undefined method, wrong arity, unresolved import |

The gate runs two engines because neither covers the other. PMD has the custom
rules and complexity metrics; Checkstyle has import hygiene, naming, and a set
of real bug checks (`FallThrough`, `EqualsHashCode`, `MissingSwitchDefault`)
that PMD does not report. On real code Checkstyle adds few findings, which is
the point: it was scoped to non-overlapping checks rather than bulk-imported.

Measured on a probe file: **PMD 0 findings, jdtls 4 errors.** They are
complementary, not redundant. Neither is a code review.

## Command map

Route the user's intent. Do not improvise file edits.

| User says | Command |
|---|---|
| "is it on", "what's it checking" | `status` (also the bare default) |
| "turn it off", "this is annoying" | `off` |
| "turn it back on" | `on` |
| "what rules are active" | `rules` |
| "stop blocking on X", "make X a warning" | `relax <Rule>` |
| "X should block", "be strict about X" | `strict <Rule>` |
| "too strict", "loosen complexity" | `threshold <Rule> <prop> <n>` |
| "lint this repo", "how bad is it" | `scan [path]` |
| "does this compile", "typecheck this" | `compiles <file.java>` |
| "publish these rules to repo Y's CI" | `adopt <repo-path>` |
| "it's not firing", "is it working" | `doctor` |

## Guidance

**`off`** — The instant kill switch. Use it without hesitation when the user is
frustrated. It is one flag and fully reversible. Do not defend the gate first.
Turn it off, then ask what annoyed them.

**`relax <Rule>`** — The middle setting. The rule still reports but stops
blocking. Prefer this over `off` when the complaint names one specific rule.

**`threshold`** — Validated. If PMD cannot load the result the change is
rejected and the file restored. Common knobs:

```
threshold CyclomaticComplexity   methodReportLevel     8    # lower = stricter
threshold CognitiveComplexity    reportLevel          10
threshold CommentSize            maxLines              6
threshold AvoidDuplicateLiterals maxDuplicateLiterals  3
```

PMD's own defaults are 10 and 15. At those levels this codebase reported 2 and
0 violations, which is silence, not health. Do not "fix" noise by restoring PMD
defaults.

**`compiles <file>`** — Runs the Eclipse compiler with the full Maven
classpath. Add `--rebuild` after a branch switch or a `pom.xml` change. If
results look wrong, suspect a stale index and `--rebuild` **before** concluding
anything about the code. Never report a typecheck finding as fact without that.

**`adopt`** — Does **not** switch the gate on, it already runs everywhere from
the user ruleset. It publishes your personal standards into a shared team repo
so CI can enforce them for everyone. That changes other people's builds. Get
agreement first, and never run it to clear a factory phase.

**`doctor`** — Ten checks across both engines, including a live probe that
writes known-bad Java and asserts the hook exits 2. Run it whenever the user
suspects nothing is happening.

## Rules in the gate

Custom rules exist because PMD ships no equivalent. Each encodes a repeated
review objection. Standards: `[[feedback-java-code-standards]]` in memory.

| Rule | Catches |
|---|---|
| `NoRawObjectReturn` | methods returning raw `Object` |
| `NoNullReturn` | `return null`, including null-means-success contracts |
| `NoUncheckedThrow` | unchecked exceptions. **Advisory by design** |
| `CommentSize` | javadoc over 6 lines |
| `AvoidDuplicateLiterals` | magic strings repeated 3+ times |
| `InvalidLogMessageFormat` | log placeholder count mismatches |
| `EmptyCatchBlock`, `PreserveStackTrace` | swallowed failures |
| `CyclomaticComplexity`, `CognitiveComplexity` | complexity, at 8 and 10 |

Checkstyle side (`klever-checkstyle.xml`):

| Rule | Catches |
|---|---|
| `FallThrough`, `MissingSwitchDefault` | switch bugs |
| `EqualsHashCode` | overriding one without the other, breaks every HashMap |
| `StringLiteralEquality` | `s == "literal"`. Does **not** catch `a == b` between two String variables |
| `UnusedImports`, `RedundantImport`, `AvoidStarImport` | import cruft |
| `NeedBraces`, `OneStatementPerLine`, `EmptyBlock` | statement hazards |
| `TypeName`, `MethodName`, `MemberName`, … | naming consistency |
| `MethodLength` (60), `ParameterNumber` (7) | loose size backstops below PMD's complexity rules |

**No `Javadoc*` checks, deliberately.** Stock `sun_checks.xml` and
`google_checks.xml` REQUIRE javadoc on public members, which is the opposite of
the standard here. Never swap in a stock config.

**`NoUncheckedThrow` is advisory on purpose.** The ask was "every throw should
be checked", but the blanket form conflicts with Spring, whose
`DataAccessException` hierarchy is unchecked by design, and a `@RestController`
cannot propagate a checked exception cleanly. `EmptyCatchBlock` and
`PreserveStackTrace` block instead, since swallowed failures are the real risk.
If asked to make it blocking, do it, but restate this once.

## Suppression

When a rule is wrong at one site, suppress there rather than weakening it
globally:

```java
@SuppressWarnings("PMD.NoNullReturn")   // method or class
// NOPMD <reason>                       // line
```

Both leave a greppable justification. Prefer this over `relax` when the problem
is one location rather than the rule itself.

## Lombok, the trap

Without a Lombok javaagent, typechecking reports a wall of phantom errors on
every Lombok class: `log cannot be resolved` (`@Slf4j`), `blank final field may
not have been initialized` (`@RequiredArgsConstructor`), `method getX() is
undefined` (`@Getter`). Measured **10 false positives on one correct file**.

The `java.jdt.ls.lombokSupport` setting alone does **not** fix it. jdtls does
not bundle Lombok. The script loads `-javaagent:<lombok.jar>` from `~/.m2`,
preferring the version the project's `pom.xml` declares. If phantom Lombok
errors reappear, run `doctor` to confirm the agent is found, then `--rebuild`.

The server JVM is pinned to Zulu 21. Brew's jdtls formula pulls openjdk 26, and
JDK 25+ breaks Lombok and Mockito in these repos.

## Why typecheck is on demand and not a hook

Two reasons, worth stating if asked to make it automatic:

1. **8 seconds per edit is not viable in a loop.** There is no daemon, so every
   run pays JVM start plus project load. PMD costs 1s and owns that slot.
2. **A language server is stateful.** Its index goes stale on a branch switch
   or pom change and produces confident wrong answers. Tolerable when a human
   asked and is reading the answer. Not tolerable silently blocking edits.

## Budget

~2s per Java edit is the whole budget, accepted explicitly. Both engines are
JVM-based with no daemon, so a third would break it. To halve the cost set
`checkstyle_binary` to `""` in the config, which disables that engine alone.

## Secret scanning is separate

`gitleaks` runs at **commit** time, not edit time, via a global
`core.hooksPath` at `~/.claude/git-hooks/`. A secret is not a code-quality
problem: once committed and pushed it lives in history and every clone, so the
boundary that matters is the commit, not the keystroke. That hook chains to
each repo's own hooks rather than replacing them. Kill switch:
`GITLEAKS_SKIP=1` or `~/.claude/.gitleaks-off`.

## Limits

Both engines are mechanical. They cannot judge API contract design, whether a
comment is useful rather than merely short, whether the right facts are being
logged, or whether a feature is over-engineered. A clean result from both is
not a review.

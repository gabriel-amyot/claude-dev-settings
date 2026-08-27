# Java Standards — Klever Backend

On-demand context: load when writing or reviewing Java code in Klever repos.

## Stack
- Java 17 (Temurin), Spring Boot, Maven
- JUnit 5 + Mockito (strict stubs mode)
- BigQuery client for data access
- Spring profiles: `local`, `dev`, `uat`, `prod`

### Build JDK — must be 17 (symptom → cause)
`app-proximity-report` builds **only under JDK 17** (`JAVA_HOME=…/temurin-17.jdk/…`). On a
machine whose default JDK is 21, Lombok fails during compile with:

```
java: java.lang.IllegalStateException: TypeTag :: UNKNOWN
```

`TypeTag :: UNKNOWN` is the classic Lombok-vs-newer-JDK signature — Lombok reaching into
`javac` internals that moved in later JDKs. **The root cause is the JDK version, not the
code.** Fix: build with Temurin 17 (set `JAVA_HOME` as in the run command below). If you hit
this, do NOT start editing the code — switch the JDK first.

*Pinning the JDK in the repo (`.mvn/jvm.config`, `.java-version`, or a Maven toolchains entry)
is the robust fix, but it touches shared/committed config that affects other engineers and CI
— propose it to the code owner via MR, do not commit it autonomously.*

## Testing

### Run command
```bash
JAVA_HOME=/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home \
  /opt/homebrew/bin/mvn -f ~/Developer/grp-beklever-com/grp-app/grp-ms/app-proximity-report/pom.xml test
```

### Conventions
- **Dual-mode tests:** Cover both `isRealData()=true` and `isRealData()=false` paths
- **Mockito strict stubs:** UnnecessaryStubbing errors are test bugs, not warnings. Fix them by removing unused stubs or switching to `lenient()` only when justified.
- **Test naming:** `{ClassName}Test` in same package under `src/test/`
- **Coverage targets:** SQL query shape, DTO mapping, service logic, validation, controller routing
- **Pass criteria:** 0 failures, 0 errors. No exceptions.

### Pre-existing test failures
When running tests after code changes reveals failures that predate your changes (stale assertions, UnnecessaryStubbing), fix them. Attribute in commit: "Fixed pre-existing test bug: [description]." Never leave pre-existing failures unresolved.

### Test summary extraction — survive error-path noise
Error-path tests (assertion of expected exceptions, 500 responses, invalid payloads) can throw stack traces into build output that look like failures but aren't. Always confirm via the canonical summary line, never by skimming `tail -N`.

**Canonical extraction:**
```bash
./mvnw test 2>&1 | grep -E "Tests run:|BUILD SUCCESS|BUILD FAILURE"
```

**Never use `-q` when you need pass/fail status** — the quiet flag suppresses the `BUILD SUCCESS` / `BUILD FAILURE` line, leaving you guessing from partial stack traces.

**Ground-truth signal:** look for the final aggregate line `Tests run: N, Failures: 0, Errors: 0, Skipped: 0` followed by `[INFO] BUILD SUCCESS`. Anything else is either a real failure or a truncated log.

Learned from 2026-04-13 SPV-92 consolidation: clean build showed Mockito-style stack traces from deliberate error-path assertions in `QuotesControllerTest`; `grep -E "Tests run:|BUILD"` resolved the ambiguity instantly.

## Code Style
- Code should be self-documenting. Name variables and methods intuitively.
- If explanation is needed, use `log.debug()` instead of comments.
- Keep methods small and focused. Extract helper methods.
- Boolean helpers read like questions: `isStaleWebhook()`, `hasPermission()`, `shouldRetry()`
- No comment cruft. A well-named method beats a comment.

## Architecture Patterns
- `@Service` for business logic, `@Repository` for data access
- Adapters pattern: BigQuery adapters implement interfaces, mock adapters used in local/test
- Feature flags: `proximity-map.data-source=mock|real` switches between mock and BQ adapters
- Spring profiles control environment-specific config

## Starting Backend Locally

### Mock mode (default)
```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-ms/app-proximity-report
JAVA_HOME=/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home \
  /opt/homebrew/bin/mvn spring-boot:run -Dspring-boot.run.profiles=local
```
Port: 8097

### Real data mode
```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-ms/app-proximity-report
JAVA_HOME=/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home \
  /opt/homebrew/bin/mvn spring-boot:run -Dspring-boot.run.profiles=local \
  -Dspring-boot.run.arguments="\
    --proximity-map.data-source=real \
    --proximityReport.bigquery.projectId=prj-d-biz-report-im9q1fvvc7 \
    --proximityReport.bigquery.datasetId=klever_proximity_data"
```
Requires `gcloud auth application-default login` first.

## Schema Validation
Before wiring any BigQuery adapter, verify actual schema with `bq show --schema` or `SELECT * LIMIT 1`. See `~/.claude/library/context/schema-validation-gate.md` for full procedure.

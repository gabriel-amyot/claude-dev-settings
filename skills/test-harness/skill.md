# Test Harness Skill

Manage the SPV-3 local test harness: build images, start/stop services, run tests, check logs, and diagnose failures.

## Harness Root

```
~/Developer/supervisr-ai/project-management/tools/test-harness/
```

## Usage Examples

```bash
/test-harness build lead-lifecycle-service --force   # Rebuild one service image
/test-harness build --force                          # Rebuild all images
/test-harness build                                  # Build only missing images

/test-harness start                                  # Start all services, wait for healthy
/test-harness stop                                   # Tear down all containers

/test-harness test                                   # Run the 9-step flow test
/test-harness test --step 3                          # Run from step 3 onward

/test-harness logs lead-lifecycle                    # Tail last 80 lines for one service
/test-harness logs                                   # Tail logs for all services

/test-harness status                                 # Show container status + health
/test-harness diagnose                               # Full diagnosis: logs + PubSub state + common failure patterns

/test-harness restart lead-lifecycle                 # Stop + rebuild + start one service
/test-harness restart                                # Full stop + rebuild all + start
```

## Service Name Reference

| Short name (for logs/restart) | Image name | Source dir |
|-------------------------------|------------|-----------|
| `lead-lifecycle` | `lead-lifecycle-service:local` | `lead-lifecycle-service/` |
| `retell-service` | `retell-service:local` | `retell-service/` |
| `compliance-ers` | `web-ers:local` | `compliance-ers/` |
| `eqs` | `query-service:local` | `supervisor-query-service/` |
| `compliance-engine` | `supervisor-compliance-engine:local` | `supervisor-compliance-engine/` |

## Workflow

Parse the command from the user's invocation args, then execute accordingly.

### `build [service] [--force]`

1. If `--force` and a service name given: `docker rmi {image}:local`, then rebuild that one
2. If `--force` and no service: remove all `:local` images, rebuild all
3. Run: `~/Developer/supervisr-ai/project-management/tools/test-harness/scripts/build-images.sh [service] [--force]`
4. Report success or paste the Maven/Docker error and diagnose it

**Common build failures:**
- `LiteWebJarsResourceResolver` / springdoc class errors → springdoc version incompatible with Spring Boot version; downgrade springdoc in pom.xml
- `NoClassDefFoundError` → dependency version mismatch; run `mvn dependency:tree` to find conflict
- JIB auth error → `gcloud auth application-default login`
- Platform warning (amd64 vs arm64) → add `-Djib.from.platforms=linux/arm64` to the JIB command

### `start`

1. Run: `./scripts/start.sh`
2. If a service fails to become healthy within timeout, automatically run `diagnose` for that service

### `stop`

Run: `./scripts/stop.sh`

### `test [--step N]`

1. Run: `./scripts/test-spv3-flow.sh`
2. If a step fails, read the error, cross-reference the actual GraphQL schema in the service source, and propose the fix

### `logs [service]`

Run:
- Single: `docker logs test-harness-{service}-1 --tail 20 2>&1`
- All: loop over all 7 containers and print headers between each

### `status`

Run: `docker compose -f ~/Developer/supervisr-ai/project-management/tools/test-harness/docker-compose.yml ps`

Print a clean summary with container name, status, health, and ports.

### `diagnose [service]`

**Log reading strategy:**
1. Start with `--tail 20`
2. If the error is clear → stop, diagnose, fix
3. If the 20 lines show an exception but the `Caused by:` root cause is cut off → escalate to `--tail 50`, then `--tail 100`
4. If the service is chatty (many INFO lines, no obvious error in tail) → switch to grep: `docker logs test-harness-{service}-1 2>&1 | grep -E "ERROR|WARN|Exception|Failed|refused" | tail -20`
5. Never read the full log speculatively — escalate in steps, grep when signal-to-noise is low

1. Run `status` first
2. For each unhealthy container (or the named service):
   - Pull last 20 log lines first (escalate if needed — see above)
   - Check for known failure patterns (see below)
   - State the probable cause and exact fix
3. Check PubSub topics were provisioned:
   - `docker logs test-harness-lead-lifecycle-1 2>&1 | grep -i "emulator\|topic\|subscription"`
   - `docker logs test-harness-eqs-1 2>&1 | grep -i "emulator\|topic\|subscription"`
4. Check port conflicts: `lsof -i :8080 -i :8082 -i :8085 -i :9000 -i :9001 -i :9002 -i :4010 -sTCP:LISTEN`

**Known failure patterns:**
| Log snippet | Cause | Fix |
|-------------|-------|-----|
| `LiteWebJarsResourceResolver` | springdoc version mismatch | Downgrade springdoc to `2.6.0` in pom.xml, rebuild |
| `Connection refused` to `pubsub-emulator:8085` | Emulator not ready or wrong host | Check `PUBSUB_EMULATOR_HOST` env var in compose |
| `UNAUTHENTICATED` / Datastore auth error | GCP ADC not mounted | `gcloud auth application-default login` |
| `Address already in use` | Port conflict | `./scripts/stop.sh` then check `lsof -i :{port}` |
| `platform mismatch (amd64/arm64)` | Image built for wrong arch | Rebuild with `--force` |

### `restart [service]`

1. `./scripts/stop.sh`
2. If service given: `docker rmi {image}:local`, rebuild that one
3. If no service: rebuild all
4. `./scripts/start.sh`

## Report

After `test` or `diagnose`, write a brief status note to:
`~/Developer/supervisr-ai/project-management/tickets/SPV-3/reports/status/test-harness-run-{YYYY-MM-DD}.md`

Keep it short: result (PASS/FAIL), which step failed, what was fixed.

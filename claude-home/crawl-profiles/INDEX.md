# Crawl Profiles (Harness Definitions)

Harness profiles define **where** a crawl runs. Agent definitions define **how** a crawl behaves. The two are combined at invocation time.

## Harness Matrix

| Profile | Environment | Docker | GCP | GitLab | Verification |
|---------|-------------|--------|-----|--------|--------------|
| local-harness | local | FATAL | WARN | WARN | `supervisr-test.sh --env local` |
| rnd-harness | rnd | WARN | FATAL | WARN | `supervisr-test.sh --env rnd` |
| dev-harness | dev | WARN | FATAL | FATAL | `supervisr-test.sh --env dev` |

## Invocation Pattern

```
/ralph-loop "{agent} {ticket}" --profile {harness} --max-iterations N
```

Examples:
- `/ralph-loop "night-crawl SPV-3" --profile local-harness --max-iterations 7`
- `/ralph-loop "night-crawl SPV-3" --profile rnd-harness --max-iterations 10`
- `/ralph-loop "dev-crawl SPV-85" --profile dev-harness --max-iterations 20`

## Profiles

- **local-harness.yaml** — Docker containers + emulators. Self-contained, no cloud.
- **rnd-harness.yaml** — R&D-BAC1 isolated GCP (prj-rnd-n-back1-aqsxotdlv0). Real services, full isolation.
- **dev-harness.yaml** — Shared GCP dev (prj-sprvsr-d-core). Real infra, multi-engineer.

# Supervisr Datastore Topology (Per Environment)

Cross-service reference for Datastore databases, namespaces, and GCP projects across all environments. Use this when querying, extracting, or cleaning Datastore entities outside the local emulator.

## GCP Projects

| Alias | Project ID | Environment |
|-------|-----------|-------------|
| `dev-core` | `prj-sprvsr-d-core-kkomv80zrg` | Dev |
| `dev-data` | `prj-sprvsr-d-data-fudybht2id` | Dev |
| `uat-core` | `prj-sprvsr-u-core-d1et2qoxtw` | UAT |
| `uat-data` | `prj-sprvsr-u-data-mjn3pfrtey` | UAT |
| `prod-core` | `prj-sprvsr-p-core-6of3dwjpzt` | Prod |
| `prod-data` | `prj-sprvsr-p-data-n2s076aw4z` | Prod |
| `rnd-bac1` | `prj-rnd-n-back1-aqsxotdlv0` | R&D (isolated, tear-down-after) |

## Databases and Namespaces

### Lead Lifecycle Service (LLS)

| Environment | Project | Database | Namespace | Kinds |
|-------------|---------|----------|-----------|-------|
| Dev | `dev-core` | `lead-lifecycle-us-central1` | `lead_lifecycle` | `leads`, `global-scheduling-config`, `lead_suppression`, `idem_lead_lifecycle_service` |
| R&D | `rnd-bac1` | `lead-lifecycle-us-central1` | `lead_lifecycle` | Same as above |
| Emulator | `local-project` | (default) | `lead_lifecycle` | Same as above |

**Gotcha:** LLS always uses the `lead_lifecycle` namespace. Queries without `--namespace lead_lifecycle` return 0 results.

### Compliance ERS (Event + Materialized View Store)

| Environment | Project | Database | Namespace (Event Store) | Namespace (MV Store) | Kinds |
|-------------|---------|----------|------------------------|---------------------|-------|
| Dev | `dev-data` | `compliance-us-central1` | (default) | (default) | `leads`, `lead_events`, `interactions`, `interaction_events`, `rules`, `rule_events`, `supervisors`, `supervisor_events`, `partner_configurations`, `lead_source_configurations`, `phone_pool_entries` |
| R&D | `rnd-bac1` | `compliance` | `supervisr_webErs_local` | `supervisr_webErs_local_mv` | Same kinds, split across event/MV namespaces |
| Emulator | `local-project` | `compliance` | `supervisr_webErs_local` | `supervisr_webErs_local_mv` | Same as R&D |

**Note:** Dev uses default namespace (no namespace separation between event store and MV). R&D/Emulator use separate namespaces for event store vs materialized views.

### EQS (Entity Query Service)

EQS is **read-only**. It reads from the compliance MV store written by ERS.

| Environment | Project | Database | Namespace | Operations |
|-------------|---------|----------|-----------|------------|
| Dev | `dev-data` | `compliance-us-central1` | (default) | READ ONLY |
| R&D | `rnd-bac1` | `compliance` | `supervisr_webErs_local_mv` | READ ONLY |

## Operational Tools

| Tool | Location | Purpose |
|------|----------|---------|
| Bulk delete (DEV-ONLY) | `project-management/tools/datastore-ops/nuke_entities.py` | Delete entities with 5-layer safety (allowlist, blocklist, dry-run, backup, confirmation) |
| Extract/backup | `project-management/tools/datastore-extract/extract_dev_data.py` | Export entities to JSON for harness seeding |

## Key Differences: Dev vs R&D

| Aspect | Dev | R&D (BAC1) |
|--------|-----|------------|
| Project split | Separate core/data projects | Single project |
| Database names | Region-suffixed (`compliance-us-central1`, `lead-lifecycle-us-central1`) | Short names (`compliance`) |
| ERS namespaces | Default (no namespace) | Separate event/MV namespaces |
| Persistence | Long-lived, shared | Ephemeral, tear-down-after |

## Verified Counts (2026-03-21, pre-cleanup)

Snapshot before SPV-92 cleanup:

| Database | Kind | Count | Project |
|----------|------|-------|---------|
| `compliance-us-central1` | `leads` | 2,010 | `dev-data` |
| `compliance-us-central1` | `lead_events` | 3,287 | `dev-data` |
| `lead-lifecycle-us-central1` | `leads` | 2,020 | `dev-core` (namespace: `lead_lifecycle`) |

All deleted with backups at `tools/datastore-ops/backups/`.

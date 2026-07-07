# Changelog

All notable changes to this project are documented here. Format loosely follows
Keep a Changelog; the top-most version must match the `<version>` in `pom.xml`.

## [1.4.2] - 2026-06-30

### Fixed
- Corrected null-handling in the proximity aggregation adapter when a POI has no visits.

## [1.4.1] - 2026-06-24

### Changed
- Bumped Placer client timeout from 10s to 30s for large viewport queries.

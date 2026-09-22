# Skill Proposal: um-local-seed
Date: 2026-04-18
Source: KTP-499 local testing session

## Trigger
When starting local development with User Management backend and the database is empty or needs fresh data.

## Scope
Repo-local (app-user-management)

## Draft Steps
1. Check if MySQL Docker container is running (`docker ps --filter name=user-management-mysql`)
2. Check if data already exists (`SELECT COUNT(*) FROM user`)
3. If empty, run changeset 12 SQL directly against the container
4. Verify seeded counts: 24 users, 24 permissions, 12 DSP accounts
5. Start backend with `--spring.profiles.active=local --server.port=8090`

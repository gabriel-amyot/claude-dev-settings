# Skill Proposal: port-squatter-preflight
Date: 2026-05-19
Source: KTP-669 SBE-4 zombie process investigation

## Trigger
Before any localhost API testing, tunnel setup, or `/klever-local-stack` startup. Also at session start when debugging backend behavior via localhost.

## Scope
org (Klever) — could generalize to global

## Draft Steps
1. Check ports 8096, 8097, 8098 (proximity-planning, proximity-report, user-management) for listening processes
2. For each occupied port, identify the process (ps aux, lsof)
3. If process is a stale Java jar (started >2h ago), warn and offer to kill
4. If process is an active tunnel (ssh), report as healthy
5. If process is something unexpected, warn and do NOT kill automatically

## Context
A Friday-started `java -jar target/proximity-report.jar` on port 8097 caused 2+ hours of false investigation. Every curl hit the stale local JAR instead of the COS through the SSH tunnel. Could be integrated into `/klever-local-stack` or `/pre-flight` rather than standalone.

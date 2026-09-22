# Skill Proposal: klever-local-stack
Date: 2026-04-17
Source: KTP-499 local validation session

## Trigger
"start user-management locally", "spin up the backend", "run the portal locally", or any KTP ticket requiring local backend+frontend

## Scope
org (Klever)

## Draft Steps
1. Check Docker is running, start MySQL container with lower_case_table_names=1
2. Build backend jar with Java 17 (detect JAVA_HOME, fail fast if wrong version)
3. Start jar with local profile, verify health endpoint
4. Seed test data (agencies, advertisers, users) via SQL
5. Check frontend .env.local has KLEVER_USER_MANAGEMENT_URL + LOCAL_MOCK vars
6. npm install if needed, npm run dev
7. Verify both endpoints respond, print summary

# Skill Proposal: local-auth-preflight
Date: 2026-05-20
Source: Sprint proof system run session (6 days debugging auth chain)

## Trigger
Before running e2e tests, proof system, or any browser-based validation that needs UM permissions. Also before `/klever-local-stack` when LOCAL_MOCK_GOOGLE is configured. Phrases: "auth preflight", "check local auth", "why access denied locally."

## Scope
org (Klever)

## Draft Steps
1. **Check ADC identity**: Run `gcloud auth application-default print-access-token`, resolve to email via token info. Verify it matches expected Klever identity (`gamyot@beklever.com`). If wrong org, suggest `gcloud auth application-default login --account=gamyot@beklever.com`.
2. **Check UM health**: Curl `http://localhost:8098/user/actuator/health`. If 000, check for Java process on port. If 404, report wrong context path.
3. **Check demo user exists in local MySQL**: Query `SELECT auth0_id FROM user WHERE email = 'g.amyot@beklever.com'` in `klever-mysql-local`. Compare against `.env.local` `KLEVER_DEMO_AUTH0_USER_ID`. If mismatch, offer to UPDATE.
4. **Check demo user has Measurement component**: Query `user_component` join for the demo user. Verify component 8 (Measurement) is granted.
5. **Check DSP accounts for Klever agency**: Query `dsp_account WHERE agency_id = 133`. Verify at least `efbuw` (Shrimp Basket) exists.
6. **Report**: Green/red per check. If any red, provide the fix command.

## Rationale
This session spent 60%+ of its time (across 6 days) debugging what was ultimately: no tunnels, wrong ADC, missing DB user, stale Next.js cache. A 30-second preflight would have surfaced all four in one pass.

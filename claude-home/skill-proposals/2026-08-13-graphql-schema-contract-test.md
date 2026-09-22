# Skill Proposal: graphql-schema-contract-test
Date: 2026-08-13
Source: KTP-1062/1065 TTD validation ladder — the write path shipped inoperable behind 125 green tests

## Trigger
Any repo holding vendor GraphQL documents as string constants, and a committed introspection dump of
that vendor's schema. Invoke when adding or editing a document constant, or when onboarding a new
vendor GraphQL integration.

Klever today: `app-klever-media-api` (`TTDBidGateway`, `TTDPartnerReadEndpoint`) and
`app-ttd-trading-mcp` (`documents.py`), both against
`grp-mcp/app-ttd-graphql-api-docs-mcp/data/ttd-graphql-schema.json`.

## Scope
org (Klever), generalisable to any vendor GraphQL integration.

## Why
Mocked tests cannot catch a false belief about a vendor's wire contract: the mock returns what the
author thinks the vendor returns, so the same wrong assumption is encoded in the code and its tests.
`maxBidCPMInAdvertiserCurrency { amount }` on a scalar `Decimal` passed 125 tests and failed on the
first live call. A field-name golden test does not catch it either — the bug is in the shape.

## Draft Steps
1. Locate the committed introspection dump; record its capture date. Fail the test if the dump is
   older than a configured age (drift guard).
2. Parse each document constant: for every `field { ... }` sub-selection, resolve the parent type and
   the field's unwrapped type.
3. Assert a sub-selection appears only on OBJECT / INTERFACE / UNION, never on SCALAR or ENUM. This
   is the check that catches the class of bug above.
4. Assert every named field exists on its parent type, and every enum literal is a declared value.
5. Assert declared variables match the operation's argument types.
6. Report the failing path as `Type.field -> Kind` so the fix is obvious without opening the schema.

## Notes
Prototype verified during the source session: rejects the shipped document, passes the fixed one,
offline, no credential, milliseconds. Pairs with a wire-shape test built from one real captured
vendor response (`TTDBidGatewayTest`) — schema catches the request, capture catches the parse.

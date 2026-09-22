# Skill Proposal: deployed-image-truth
Date: 2026-09-14
Source: dac-gcp-front-au0api !28 prod promotion review

## Problem it fills

`/deploy-identity` resolves **which branch deploys**. It does not resolve **which image version is
deployed**, and for any service whose configuration ships inside its container that is the gap that
matters.

Worked failure, 2026-09-14: `app-klever-media-api` `application-prod.properties` on `origin/dev` had
bid writes armed against the live Powers book. I concluded prod was armed and built a Terraform guard
around it. Prod runs **0.11.0**, built from `origin/main`, which declares no `klever.ttd.write.*`
lines at all. The branch-level deploy-identity stamp was correct and still did not catch it, because
the drift was in the image version, not the branch.

## Trigger

Before asserting what a deployed service does, when the claim rests on a file that ships inside the
image: Spring `application-{env}.properties`, any bundled config, a compiled constant, a resource
file. Also whenever a review cites a `*-prod.properties` file as evidence about production.

## Scope

Org (Klever first, the pattern generalises to any DAC-deployed service).

## Draft steps

1. Resolve the service's DAC repo and the image-version variable, conventionally
   `TF_VAR_cloudrun_{service}_docker_version`.
2. Read that variable **per environment scope**, not just the default. The dev and prod scopes carry
   different values and only the scoped read is meaningful.
3. Map the prod value to a commit or tag in the application repo (`pom.xml` version, or the release
   tag).
4. Read the config file **at that commit**, never on `origin/dev` and never on the working tree.
5. Emit a stamp that names the version, not only the branch:
   `[VERIFIED against prod image 0.11.0 = main@2e38022]`.
6. When the deployed version differs from the branch tip, say so explicitly and name both, because
   that gap is usually the actual finding.

## Relationship to existing tooling

Extends `~/.claude/skills/deploy-identity/`. Could be a mode on that skill
(`/deploy-identity --image <service>`) rather than a separate skill, which is probably the better
shape: same concept, one more resolution step, and it keeps a single stamp vocabulary.

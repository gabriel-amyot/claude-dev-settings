# Foursquare Targeting: Where the Docs Live and What They Answer

Generic pointer for any integration with the Foursquare Targeting (Geopulse) API. No org IDs, keys or customer names. Org-specific evidence lives in each org's bibliothèque (vendors/foursquare).

**Checked 2026-11-06.** All pages below loaded without a login. The vendor docs change. Re-open the linked section before you rely on a fact, and update the check date.

## Two doc trees

The site navigation does not link the two trees to each other. Open the URLs directly.

| Tree | Base | Audience |
|---|---|---|
| Developer reference | `docs.foursquare.com/developer/reference/targeting-api-*` and `marketing-solutions-tokens` | API integrators |
| Campaign products | `docs.foursquare.com/campaign-products/docs/*` | Users of the Foursquare UI (build, deploy to DSP) |

The [Geofences](https://docs.foursquare.com/developer/reference/geofences) page documents the **Pilgrim SDK Geofences API**. It is not the Targeting Proximity designer.

## Which page answers what (checked 2026-11-06)

| Question | Page and section |
|---|---|
| What the API is for | [Overview](https://docs.foursquare.com/developer/reference/targeting-api-overview) |
| `KEY` parameter, browser restriction | [Authentication: Introduction](https://docs.foursquare.com/developer/reference/targeting-api-authentication#introduction) |
| Rate limits | [Authentication: throttle allocation](https://docs.foursquare.com/developer/reference/targeting-api-authentication#tracking-throttle-allocation-real-time) |
| User tokens, refresh, Bearer header | [Tokens: Getting tokens](https://docs.foursquare.com/developer/reference/marketing-solutions-tokens#getting-tokens), [Refreshing tokens](https://docs.foursquare.com/developer/reference/marketing-solutions-tokens#refreshing-tokens), [Using tokens](https://docs.foursquare.com/developer/reference/marketing-solutions-tokens#using-tokens) |
| Designer iframe | [Embed: Iframe](https://docs.foursquare.com/developer/reference/targeting-api-embed#iframe), [Token authentication](https://docs.foursquare.com/developer/reference/targeting-api-embed#token-authentication) |
| Design to deployment lifecycle | [Management: Lifecycle](https://docs.foursquare.com/developer/reference/targeting-api-management#lifecycle) |
| Request a build | [Management: Request Build of a Design](https://docs.foursquare.com/developer/reference/targeting-api-management#request-build-of-a-design) |
| List builds and their deployments | [Management: List Builds](https://docs.foursquare.com/developer/reference/targeting-api-management#list-builds) |
| Request a deployment (`targetId`, `message`) | [Management: Request Deployment of a Built Design](https://docs.foursquare.com/developer/reference/targeting-api-management#request-deployment-of-a-built-design) |
| List deployments | [Management: List Deployments](https://docs.foursquare.com/developer/reference/targeting-api-management#list-deployments) |
| Visibility tags on designs | [Grant: Introduction](https://docs.foursquare.com/developer/reference/targeting-api-grant#introduction) |
| DSP onboarding per product | [Eligible platforms](https://docs.foursquare.com/campaign-products/docs/eligible-platforms) (for example [The Trade Desk Audience](https://docs.foursquare.com/campaign-products/docs/eligible-platforms#the-trade-desk-audience), [The Trade Desk Proximity](https://docs.foursquare.com/campaign-products/docs/eligible-platforms#the-trade-desk-proximity)) |
| UI deploy steps and timing | [Deploy segments to DSP: Final steps](https://docs.foursquare.com/campaign-products/docs/deploy-segments-to-dsp#final-steps) |
| Where an activated file loads | [On-Prem HTTP server](https://docs.foursquare.com/developer/docs/campaign-sdk-http) |

## Facts that trip integrators

- **The public API has no seat, partner or advertiser field.** Deploy takes only `targetId` (required) and `message` (optional metadata). Source: [Request Deployment of a Built Design](https://docs.foursquare.com/developer/reference/targeting-api-management#request-deployment-of-a-built-design), checked 2026-11-06. A Foursquare support agent confirmed this on 2026-11-05: a partner chosen in the Foursquare UI Build form is not readable or settable through the documented API.
- **`targetId` is a Foursquare deployment target (infrastructure) GUID**, not a DSP Partner ID or advertiser ID (support answer, 2026-11-05). No documented endpoint lists targets. Ask Foursquare support for the GUID.
- **"activated" is not DSP delivery.** An administrator of the On-Prem software approves and activates. "Upon activation, the targeting file associated with the deployment will get loaded into memory in the partner's On-Prem software." Source: [Management: Lifecycle](https://docs.foursquare.com/developer/reference/targeting-api-management#lifecycle), checked 2026-11-06.
- **`GET /geopulse/deployments/` lists deployments "across your infrastructure".** An API customer that is not an On-Prem partner can get zero rows (one org observed this, 2026-11-05). Read `deployments[]` from [List Builds](https://docs.foursquare.com/developer/reference/targeting-api-management#list-builds) instead. Source: [List Deployments](https://docs.foursquare.com/developer/reference/targeting-api-management#list-deployments), checked 2026-11-06.
- **Doc versus live drift** (measured by one integrator in 2026-11, not in the docs): token expiry came back as `expiresAt`, not `expiration`, and `GET /token/user/{uid}` rotated the token. Compare with [Tokens: Token API response](https://docs.foursquare.com/developer/reference/marketing-solutions-tokens#token-api-response) and re-measure before you rely on either side.
- **DSP onboarding is a support task.** "Partner ID needs to be onboarded" for The Trade Desk Audience and Proximity. Source: [The Trade Desk Audience](https://docs.foursquare.com/campaign-products/docs/eligible-platforms#the-trade-desk-audience), checked 2026-11-06.

## Getting answers the docs do not give

Use Foursquare Customer Support (`4sq.com/TargetingSupport`). Ask for target GUIDs, Partner ID onboarding, and which DSP account a target delivers to. Record the answer with its date and channel in the org bibliothèque.

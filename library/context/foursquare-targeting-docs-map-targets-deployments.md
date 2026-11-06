# Foursquare Targeting: Where the Docs Live and What They Answer

Generic pointer for any integration with the Foursquare Targeting (Geopulse) API. No org IDs, keys or customer names. Org-specific evidence lives in each org's bibliothèque (vendors/foursquare).

Verified against the live public docs on 2026-11-06. All pages below loaded without a login.

## Two doc trees

The site navigation does not link the two trees to each other. Go to the URLs directly.

| Tree | Base | Audience |
|---|---|---|
| Developer reference | `docs.foursquare.com/developer/reference/targeting-api-*` and `marketing-solutions-tokens` | API integrators |
| Campaign products | `docs.foursquare.com/campaign-products/docs/*` | Users of the Foursquare UI (build, deploy to DSP) |

The pages `developer/reference/geofences` and `get-a-geofence` etc. document the **Pilgrim SDK Geofences API**. They are not the Targeting Proximity designer. Do not use them for Targeting work.

## Which page answers what

| Question | Page |
|---|---|
| What the API is for | `developer/reference/targeting-api-overview` |
| `KEY` parameter, no browser access, IP or bundle restriction, rate limits (per minute delays, per day HTTP 429) | `developer/reference/targeting-api-authentication` |
| User tokens (`GET /token/user`, `/token/user/{uid}`), expiry, Bearer header | `developer/reference/marketing-solutions-tokens` |
| Designer iframe URLs, `embedded=true`, `factual_api_token` | `developer/reference/targeting-api-embed` |
| Designs, builds, deploy request, deployment state changes, list deployments, lifecycle | `developer/reference/targeting-api-management` |
| Visibility tags on designs (overwrite, OR filter, no revoke) | `developer/reference/targeting-api-grant` |
| Which DSP is self-serve, per product, Partner ID onboarding, naming rules, set limits | `campaign-products/docs/eligible-platforms` |
| UI deploy steps, timing (3 to 6 business days), non-self-serve tickets | `campaign-products/docs/deploy-segments-to-dsp` |
| Refresh timing (2 to 6 business days), redeploy by Build | `campaign-products/docs/refresh-segments` |
| Find a segment in the DSP by Targeting Code, Audience populates up to 72 h | `campaign-products/docs/post-deployment-faq` |
| On-Prem SDK (where an "activated" file loads) | `developer/docs/campaign-sdk-http` |

## Facts that trip integrators

- **The public API has no seat, partner or advertiser field.** Deploy (`POST /geopulse/builds/{id}/request`) takes only `targetId` (required) and `message` (optional metadata). Design, build and deployment objects carry no DSP partner or advertiser ID. A partner chosen in the Foursquare UI Build form is not readable or settable through the documented API.
- **`targetId` is a Foursquare deployment target (infrastructure) GUID**, not a DSP Partner ID or advertiser ID. Foursquare support provisions targets and gives you the GUID. No documented endpoint lists targets. The List Builds filter `deployment_target` takes "the slug of the target org".
- **"activated" is not DSP delivery.** The lifecycle is build, deploy request, then an administrator of the On-Prem software approves and activates. On activation the targeting file loads into memory in the partner's On-Prem software. It does not prove an advertiser-specific setting or ad delivery.
- **`GET /geopulse/deployments/` lists deployments "across your infrastructure".** An API customer that is not an On-Prem partner can get zero rows. Read deployments from the `deployments[]` array in `GET /geopulse/builds` instead.
- **Doc versus live drift** (measured by integrators, not in the docs): token expiry came back as `expiresAt`, not `expiration`. `GET /token/user/{uid}` rotated the token. Re-measure before relying on either side.
- **DSP onboarding is a support task.** For The Trade Desk, the Partner ID must be onboarded by Foursquare Customer Support for both Audience and Proximity. Amazon is self-serve for Audience only.
- **Grant overwrites** pre-existing visibility tags. A tag filter matches a design that carries any listed tag.

## Getting answers the docs do not give

Use Foursquare Customer Support (`4sq.com/TargetingSupport`). Ask for target GUIDs, Partner ID onboarding, and which DSP account a target delivers to. Record the answer with its date and channel in the org bibliothèque.

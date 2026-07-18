*As a* Measurement Map developer,
*I want* the proximity geo-aggregate tables to carry a campaign dimension,
*so that* the Measurement Map can be filtered by campaign (the prerequisite for KTP-746).

h2. Intent (Why)

KTP-746 (campaign filter on the Measurement Map) is not implementable today: the proximity geo-aggregate tables carry no campaign dimension. The campaign id already exists upstream in klever_data_aggregation.ttd_normalized_daily_geo_detailed_performance.CAMPAIGN_ID, and the proximity SQLX already joins ttd_campaign in its ad_performance CTE, but it drops the column in the final SELECT. This ticket carries it through. This is a data-pipeline task, not frontend or backend.

h2. Acceptance Criteria (What)

*AC-1 - DSP_CAMPAIGN_ID carried through the proximity SQLX*
_Given_ the Dataform models proximity_daily_geo_zip_performance.sqlx and proximity_daily_geo_country_performance.sqlx,
_When_ DSP_CAMPAIGN_ID is added to the ad_performance and generic_dsp_ad_performance CTE SELECTs and to both final SELECT blocks,
_Then_ the output tables carry a DSP_CAMPAIGN_ID column populated from the TTD CAMPAIGN_ID (and the generic DSP equivalent).

*AC-2 - Clustering updated*
_Given_ the new column,
_When_ bigquery.clusterBy is updated to include DSP_CAMPAIGN_ID,
_Then_ campaign-filtered queries are clustered efficiently.

*AC-3 - Cardinality and refresh strategy confirmed before merge*
_Given_ a COUNT(DISTINCT CAMPAIGN_ID) per advertiser check run during business hours,
_When_ the campaigns-per-advertiser factor is known,
_Then_ the table-size impact and the refresh strategy (incremental lookback self-heal vs one-time full refresh) are documented and confirmed with the pipeline owner before the change is merged.

*AC-4 - Verified in BQ after deploy*
_Given_ the change merged to the Dataform prod branch,
_When_ the daily tag run completes,
_Then_ DSP_CAMPAIGN_ID is present and non-null for campaign-attributable rows, verified by a BQ query.

h2. Notes
- Join key: DSP_CAMPAIGN_ID (string). It reconciles with the frontend campaign list, which already comes from portal_dashboards_data.creatives_daily_performance via the existing /api/v1/campaigns endpoint. No new API needed.
- Gate: Marc-Andre sign-off is required before any push to the Dataform prod branch (shared pipeline).
- Files: definitions/normalization/proximity/proximity_daily_geo_zip_performance.sqlx and proximity_daily_geo_country_performance.sqlx in adminbeklever/klever-data-workflow.
- Prerequisite for KTP-746. Backend campaignIds request-model + WHERE clause work happens in KTP-746 once this lands.
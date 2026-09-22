# Skill Proposal: sanity-content-seeder
Date: 2026-05-06
Source: Compostela Guide SBE implementation session

## Trigger
When seeding or migrating content into a Sanity project: "seed Sanity", "populate Sanity", "create content in Sanity", "migrate to Sanity", or when setting up a new Sanity-powered site.

## Scope
Global (any project using Sanity.io)

## Problem
Seeding Sanity content requires a specific sequence (deploy schema → create documents with correct IDs → publish → redeploy schema). The MCP tool has limitations (can't set custom _id). Singleton documents need exact IDs matching the Studio structure. Missing any step causes blank Studio views, orphan documents, or MCP errors.

## Draft Steps
1. **Audit** — Query all existing documents, identify singletons, check for ID mismatches and orphans
2. **Schema deploy** — Run `npx sanity@latest schema deploy` to sync cloud schema with local files
3. **Seed singletons** — Use Sanity CLI (`documents create --replace`) for documents that need specific IDs (siteSettings, homePage, guide)
4. **Seed collections** — Use MCP `create_documents_from_json` for posts, pages, and other collection documents (random IDs are fine)
5. **Publish** — Publish all seeded documents via MCP `publish_documents`
6. **Verify** — Query to confirm all documents exist at correct IDs, singleton views work
7. **Flag manual work** — Report which documents need manual image uploads (can't upload binary via API)

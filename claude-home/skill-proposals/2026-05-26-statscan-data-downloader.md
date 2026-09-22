# Skill Proposal: statscan-data-downloader
Date: 2026-05-26
Source: KTP-679 FSA-to-CD crosswalk pipeline

## Trigger
When downloading census boundary files, GeoSuite data packages, or Geographic Attribute Files from Statistics Canada. Triggers: "download Stats Canada", "get census boundaries", "download FSA shapefile", "GeoSuite data".

## Scope
org (Klever, Canada map pipeline)

## Draft Steps
1. Accept product type (boundary-file, geosuite, gaf) + year (default 2021)
2. Submit POST form to Stats Canada with correct params (year, lang, product type)
3. Follow 302 redirect to actual ZIP file URL
4. Download, verify size, extract
5. For CSVs: detect encoding (latin-1 for Stats Canada), validate expected columns
6. For shapefiles: verify CRS, feature count, key columns
7. Report: file paths, row/feature counts, CRS, column listing

## Why
Stats Canada's website uses POST-form-redirect patterns that break naive `curl -L` downloads. Two separate sessions (KTP-676 and KTP-679) hit this issue independently. The encoding and column naming gotchas (CDcode vs CDUID, latin-1 vs UTF-8) are repeat traps.

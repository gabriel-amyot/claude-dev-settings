# Skill Proposal: vendor-api-contract-probe
Date: 2026-05-19
Source: KTP-669 Placer parsing RCA (hallucinated field names shipped for 18 days)

## Trigger
Before shipping any vendor API integration (new endpoint or parser change). "Probe the API", "validate parser against real responses", "contract check".

## Scope
Global (any org with vendor API integrations)

## Draft Steps
1. Identify all vendor API endpoints the code calls (grep for URL constants)
2. For each endpoint, curl the real API with valid credentials and capture the response
3. Compare response field names and structure against the parser's expected paths
4. Report mismatches as CRITICAL findings
5. Save captured responses as recorded-response fixtures in `src/test/resources/`

# Recommendation Memo Template

Fill this for `workspace/recommendation-memo.md`. Keep it tight; the decision
matrix carries the comparison. Order options most-recommended-first.

---

# Snowflake Migration Approach Recommendation: <CUSTOMER>

**Prepared by:** <author> | **Date:** <date> | **Status:** <Final | Preliminary (no code)>

## Executive summary

<2-4 sentences: the customer's situation, the primary driver, and the
recommended approach with the one-line reason it wins.>

**Recommendation: Approach <#> - <name>.**

## Context & signals

- **Source platform(s):** <...>
- **Inventory:** <object_total> objects (<procedural_object_count> procedural);
  ETL: <etl_tools>
- **Code complexity:** <low/med/high> (anti-patterns: <...>)
- **Primary driver(s):** <...>
- **Constraints:** deadline <...>, team maturity <...>, compliance <...>
- **Data volume / SLA:** <...>

## Ranked options

### Option 1 (Recommended): <name>  — fit <score>, size <T-shirt>[, ~P50 <h>]

<one-paragraph description>

| Dimension | Effort | Risk | Notes |
|-----------|--------|------|-------|
| Code conversion | <L/M/H> | <L/M/H> | <...> |
| Historical data | <L/M/H> | <L/M/H> | <...> |
| Data ingestion | <L/M/H> | <L/M/H> | <...> |
| Data transformation | <L/M/H> | <L/M/H> | <...> |
| Testing & validation | <L/M/H> | <L/M/H> | <...> |
| Consumption | <L/M/H> | <L/M/H> | <...> |

**Pros:** <3> · **Cons:** <3> · **Key risks + mitigations:** <...>
**Repurchase/Retire moves:** <...>

### Option 2: <name> — fit <score>, size <T-shirt>
<same structure, condensed>

### Option 3: <name> — fit <score>, size <T-shirt>
<same structure, condensed>

## Decision matrix

| Dimension | Opt 1 | Opt 2 | Opt 3 |
|-----------|-------|-------|-------|
| Code conversion | | | |
| Historical data | | | |
| Data ingestion | | | |
| Data transformation | | | |
| Testing & validation | | | |
| Consumption | | | |
| **Overall effort** | | | |
| **Overall risk** | | | |
| **Value capture** | | | |

## Why Option 1 over Option 2

<Tie directly to signals: driver, timeline, team maturity, code complexity.>

## Next steps

1. Confirm the chosen approach.
2. Hand off to `modernization-assessment` for P50/P70/P90 + wave plan.
3. <POC slice / environment setup / etc.>

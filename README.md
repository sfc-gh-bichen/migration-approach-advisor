# Migration Approach Advisor

A Cortex Code skill that recommends ranked Snowflake migration approaches for customers migrating from a legacy data warehouse. It answers **"how should we migrate?"** — not just whether to lift-and-shift or rewrite, but which combination of strategies across six migration dimensions best fits the customer's code complexity, team maturity, timeline, and business driver.

## What it does

- Analyzes customer artifacts (DDL, stored procedures, ETL exports, meeting notes, transcripts)
- Extracts decision signals (object counts, dynamic SQL, complexity, SLAs, team skills, budget)
- Scores and ranks three canonical approaches most-recommended-first:

| Approach | Strategy | One-liner |
|----------|----------|-----------|
| A — Automated Lift & Shift | Rehost + Replatform | SnowConvert mechanical conversion; fastest, carries tech debt |
| B — Selective Refactor | Replatform + Refactor | Convert then modernize high-value parts; balanced effort/value |
| C — Re-architect / Rewrite | Re-architect + Rebuild | New model (Data Vault/dimensional), ELT-native, Iceberg, Cortex; highest value |

- Produces a **recommendation memo** (markdown) and an **exec Google Slides deck**
- Hands off to `modernization-assessment` for P50/P70/P90 effort sizing

## When to use

Invoke this skill when a customer asks:
- "How should we migrate?"
- "Lift-and-shift vs. rewrite — which makes sense for us?"
- "What's the right migration strategy given our constraints?"
- "Compare migration options for our BigQuery / SQL Server / Redshift migration"

## How to use

In Cortex Code, type the trigger phrase or invoke directly:

```
/migration-approach-advisor
```

Or just describe what you need — Cortex Code will route automatically on phrases like:
> *"migration approach"*, *"rank migration options"*, *"how should we migrate"*, *"lift and shift vs refactor"*

### Workflow overview

1. **Intake** — Provide code paths, meeting notes, source platform, driver, constraints
2. **Signal extraction** — Skill parses code + notes into structured signals
3. **Scoring** — Three approaches scored across six dimensions (code conversion, data migration, ingestion, transformation, testing, consumption)
4. **Recommendation** — Ranked options with pros/cons, rationale, and risk mitigations
5. **Deliverables** — Markdown memo + exec slides deck
6. **Handoff** *(optional)* — Pass chosen approach to `modernization-assessment` for detailed sizing

### Example

**Prompt:**
> I'm working with Ariat, a retail company migrating from BigQuery + SQL Server to Snowflake. They have 161 BQ tables (126 are GA4 wildcard date-partitioned), 27 stored procedures (4 high-complexity with UNNEST + dynamic SQL), and a Cloud Function orchestrating 10 SP calls. Their team has low Snowflake maturity. They want to go live in ~8 weeks on the CDP workload. Recommend migration approaches.

**What the skill produces:**
- `workspace/signals.json` — extracted complexity, volume, team, timeline signals
- `workspace/approach-scores.json` — ranked A/B/C with per-dimension effort/risk
- `workspace/recommendation-memo.md` — ranked options with rationale (likely B #1: convert DDL with SnowConvert, CoCo for the 4 high-complexity procs, Task DAG for Cloud Function)
- Google Slides exec deck

## Scripts

```bash
# Extract signals from code directory + notes
uv run --project . python scripts/extract_signals.py \
  --code-dir <path/to/sql> --notes <notes.txt> --out workspace/signals.json

# Score and rank approaches
uv run --project . python scripts/approach_scorer.py \
  --signals workspace/signals.json \
  --matrix references/decision-matrix.csv \
  --out workspace/approach-scores.json
```

## Reference files

| File | Purpose |
|------|---------|
| `references/approach-taxonomy.md` | The 3 canonical approaches + 6 Rs taxonomy |
| `references/dimension-playbook.md` | 6 migration dimensions × Snowflake phases |
| `references/signal-extraction.md` | Signal categories and manual fill guidance |
| `references/decision-matrix.csv` | Signal-to-approach affinity weights |
| `references/report-template.md` | Recommendation memo template |
| `references/slides-outline.md` | Exec slides structure |

## Related skills

| Skill | Purpose |
|-------|---------|
| `modernization-assessment` | P50/P70/P90 effort bands + wave plan (next step after this skill) |
| `split-ddl` | Chunk monolithic DDL before parsing |
| `sql-complexity-analysis` | Score stored procedure complexity |
| `migration-guide` | Code conversion specifics (SnowConvert) |

---
name: migration-approach-advisor
description: "Use when a customer needs to CHOOSE HOW to migrate a legacy database/data warehouse to Snowflake - recommends 2-3 ranked migration approaches (most-recommended-first) from customer code, meeting notes, and context. Covers the full spectrum from automated lift-and-shift to selective refactor to complete re-architect/rewrite, broken down across all six migration dimensions: database code conversion, historical data migration, data ingestion, data transformation, testing and validation, and consumption workloads. Produces a markdown recommendation memo plus an exec Google Slides deck. Hands off to modernization-assessment for detailed effort sizing. Triggers: migration approach, migration options, migration strategy, how should we migrate, lift and shift vs rewrite, rehost vs refactor vs re-architect, rank migration approaches, recommend a migration path, which migration approach, migration decision, modernization options."
---

# Migration Approach Advisor

Recommends ranked Snowflake migration approaches grounded in Snowflake's official
9-phase migration framework and the industry 6 Rs taxonomy. Takes whatever the
customer has shared (DDL, stored procs, ETL exports, meeting notes, transcripts,
RFP context) and returns 2-3 options ordered most-recommended-first, each broken
down across the six migration dimensions with relative effort and risk.

This skill answers **"how should we migrate?"** It does NOT size effort in detail
- for P50/P70/P90 hours and wave plans, hand off to the `modernization-assessment`
skill (see Step 7).

## Setup

1. **Load** `references/approach-taxonomy.md` - the 3 canonical approaches + 6 Rs.
2. **Load** `references/dimension-playbook.md` - the 6 dimensions x Snowflake phases.
3. Create a customer workspace directory: `<cwd>/<customer_name>/` with a
   `workspace/` subfolder for generated artifacts.

## The three canonical approaches

Every recommendation is framed as a point on this spectrum (Repurchase and
Retire/Retain are tagged onto whichever option they fit):

| # | Approach | 6 Rs | One-liner |
|---|----------|------|-----------|
| A | **Automated Lift & Shift** | Rehost + Replatform | SnowConvert mechanical conversion; preserve schema and logic. Fastest, lowest delivery risk, carries tech debt. |
| B | **Selective Refactor** | Replatform + Refactor | Convert, then modernize the high-value parts (cursors to set-based, ETL to ELT/dbt, key tables remodeled). Balanced. |
| C | **Re-architect / Rewrite** | Re-architect + Rebuild | New data model (Data Vault/dimensional), ELT-native (dbt + Dynamic Tables), Iceberg, semantic layer + Cortex. Highest value, highest effort/risk. |

Ordering is **dynamic per customer** - the scorer ranks them by fit to the
customer's signals; the most-recommended approach is not always the same one.

## Workflow

### Step 1: Intake

**Goal:** Gather every artifact the customer has shared and capture context.

**Actions:**
- Collect paths to: source DDL, stored procedures/functions, ETL exports
  (SSIS/Informatica/etc.), BI/report definitions, meeting notes, transcripts.
- Ask (use `ask_user_question` for missing items): source platform(s) + versions,
  primary driver (cost / performance / AI / consolidation / regulatory), hard
  constraints (deadline, license renewal, parallel-run window), team Snowflake
  maturity, risk tolerance.

**Output:** `workspace/intake.md`.

**MANDATORY STOPPING POINT:** Confirm the artifact inventory and context before extracting signals.

### Step 2: Signal Extraction

**Goal:** Turn raw code + notes into structured decision signals.

**Actions:**
- Run the extractor on the code drop:
  ```bash
  uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extract_signals.py \
    --code-dir <path-to-code> --notes <path-to-notes> --out <workspace>/signals.json
  ```
- The parser is heuristic. **Load** `references/signal-extraction.md` and
  hand-fill any signals the notes imply but the parser missed (volumes, SLAs,
  BI tools, team skills, timeline/budget, compliance, business drivers).

**Output:** `workspace/signals.json`.

**MANDATORY STOPPING POINT:** Review the extracted signals with the user; correct misreads before scoring.

### Step 3: Approach Scoring

**Goal:** Score all three approaches across the six dimensions.

**Actions:**
- Run the scorer:
  ```bash
  uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/approach_scorer.py \
    --signals <workspace>/signals.json \
    --matrix <SKILL_DIR>/references/decision-matrix.csv \
    --out <workspace>/approach-scores.json
  ```
- Default output is **qualitative**: per-approach effort (Low/Med/High), risk
  (Low/Med/High), and T-shirt size (S/M/L/XL) for each of the six dimensions.
- **If SnowConvert / code metrics are available**, add `--code-metrics <path>` to
  also attach a rough **P50** per approach (the scorer imports the kit
  `loe_calculator.py`; if unavailable it degrades gracefully with a note).

**Output:** `workspace/approach-scores.json` (ranked most-recommended-first).

### Step 4: Rank & Recommend

**Goal:** Turn scores into a defensible, ordered recommendation.

**Actions:**
- Order approaches most-recommended-first using the scorer's overall fit.
- For each approach write: the 6-dimension breakdown, top 3 pros, top 3 cons,
  key risks + mitigations, and which Repurchase/Retire moves apply.
- State explicitly **why #1 beats #2** for this customer (tie the rationale back
  to specific signals: driver, timeline, team maturity, code complexity).

**MANDATORY STOPPING POINT:** Confirm the ranking and rationale with the user before authoring deliverables.

### Step 5: Author the Recommendation Memo

**Goal:** Produce the markdown deliverable.

**Actions:**
- **Load** `references/report-template.md` and fill it: exec summary, the ranked
  options, the per-dimension decision matrix, the recommendation rationale, and
  next steps.

**Output:** `workspace/recommendation-memo.md`.

### Step 6: Author the Exec Slides

**Goal:** Produce an exec-facing Google Slides deck.

**Actions:**
- **Load** `references/slides-outline.md`.
- Build the deck via the Google Workspace MCP (`mcp_google-worksp_create_presentation`).
  Reuse the Snowflake brand template `14NG7RAyaULOMCsOcHTyQoZxQtROW1YWSA_bTFyvpgRo`
  and brand colors `#29B5E8 / #11567F / #7D44CF`.

**Output:** Google Slides URL.

**MANDATORY STOPPING POINT:** Present the deck for review.

### Step 7: Handoff to modernization-assessment (optional)

**Goal:** Detailed effort sizing for the chosen approach.

**Actions:**
- Once the customer picks an approach, invoke the `modernization-assessment`
  skill, passing the same code drop and the chosen approach as the target stack,
  to produce P50/P70/P90 bands and a wave plan.

## Tools

### Script: extract_signals.py

Parses a code directory + notes into a normalized `signals.json`.

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/extract_signals.py \
  --code-dir <dir> [--notes <file>] --out <signals.json>
```

- `--code-dir`: directory of source SQL/ETL files (recursive).
- `--notes`: optional meeting-notes/transcript text file.
- `--out`: path for the signals JSON.

### Script: approach_scorer.py

Scores and ranks the three approaches from `signals.json`.

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/approach_scorer.py \
  --signals <signals.json> --matrix <SKILL_DIR>/references/decision-matrix.csv \
  --out <approach-scores.json> [--code-metrics <metrics.json>]
```

- `--signals`: signals JSON from Step 2.
- `--matrix`: signal-to-approach affinity weights.
- `--out`: ranked scores JSON.
- `--code-metrics`: optional; triggers quantitative P50 via the kit `loe_calculator.py`.

### Integrated skills

| Purpose | Skill |
|---------|-------|
| Detailed effort sizing (P50/P70/P90, waves) | `modernization-assessment` |
| Chunk monolithic DDL before parsing | `split-ddl` |
| Score stored-proc complexity | `sql-complexity-analysis` |
| Code conversion specifics | `migration-guide` |
| dbt / Dynamic Tables target design | `dbt-projects-on-snowflake`, `dynamic-tables` |
| Slides generation | Google Workspace MCP |

## Stopping Points

- After Step 1 (artifact + context confirmation)
- After Step 2 (signal review)
- After Step 4 (ranking + rationale approval)
- After Step 6 (deck review)

## Troubleshooting

**No code, only notes:** Run with `--notes` alone; scoring stays qualitative.
Flag the recommendation as preliminary and re-run when code arrives.

**Multiple source platforms (M&A):** Extract signals per platform; the dominant
complexity and the consolidation driver usually push toward Approach C for the
shared target with per-source lift-and-shift landing zones.

**Customer insists on lift-and-shift but signals favor refactor:** Present
Approach A as #1 if that is their hard constraint, but document the tech-debt and
under-utilization cost in the cons and offer a phased path to B/C.

**SnowConvert dialect unsupported:** Note manual-conversion risk in the code-conversion
dimension; this lowers the fit of A (which leans on automation) relative to C.

## Best Practices

- Lead with the customer's primary driver - it dominates the ranking.
- Always show the spectrum: even when one approach clearly wins, the alternatives
  make the recommendation credible.
- Tie every effort/risk rating back to a signal; never assert without grounding.
- Keep qualitative by default; only attach P50 when real code metrics exist.
- One workspace per customer; never overwrite the kit or skill references.

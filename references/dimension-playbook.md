# Dimension Playbook

The six migration dimensions, each mapped to Snowflake's official 9-phase
framework, with the patterns and tools that distinguish the three approaches.
Cite these when writing the per-dimension breakdown in the memo.

Snowflake migration guides (Oracle / Redshift / SQL Server) all use the same
9 phases. The mapping:

| Dimension | Snowflake phase |
|-----------|-----------------|
| 1. Database code conversion | Phase 3 |
| 2. Historical data migration | Phase 4 |
| 3. Data ingestion | Phase 5 |
| 4. Data transformation | Phase 5 |
| 5. Testing & validation | Phase 7 |
| 6. Consumption workloads | Phase 6 |
| (cross-cutting) | Phases 1, 2, 8, 9 |

---

## 1. Database code conversion (Phase 3)

- **Tooling:** SnowConvert AI. Deterministic conversion first, surfacing
  EWI (Errors/Warnings/Issues, severity Low->Critical), FDM (Functional Difference
  Messages), PRF (performance), OOS (out of scope). Then AI code conversion with
  optional two-sided source-system verification for functional parity
  (SQL Server, Redshift today).
- **Structural shifts:** constraints (PK/UK/FK) are metadata-only in Snowflake -
  integrity moves to the pipeline. Triggers are unsupported -> Streams & Tasks.
  Cursors are an anti-pattern -> set-based SQL. Drop legacy physical clauses.
- **Approach contrast:** A = accept SnowConvert output + fix EWIs mechanically.
  B = convert, then rewrite cursor/proc anti-patterns set-based. C = treat legacy
  logic as a spec and re-express declaratively.

## 2. Historical data migration (Phase 4)

- **Pattern:** three-box Source -> Stage -> Target. Extract (BCP / UNLOAD /
  Data Pump / partner tools) to Parquet or compressed CSV -> cloud stage ->
  `COPY INTO`. Split into 100-250 MB files for parallelism; size up a dedicated
  warehouse for the load then suspend it.
- **Approach contrast:** largely identical across A/B/C (one-time bulk load).
  C may land into a new model, adding mapping effort.

## 3. Data ingestion (Phase 5)

- **Incremental/CDC:** source CDC -> stage -> Snowpipe (files) or
  **Snowpipe Streaming** (rows, Kafka, IoT, low-latency CDC; exactly-once;
  in-flight transforms). Apply changes with `MERGE`.
- **Legacy ETL:** SSIS does not run on Snowflake - retarget (A) or rebuild in
  dbt + orchestrator (B/C). SQL Server Agent -> Snowflake Tasks (simple) or
  Airflow/ADF (complex DAGs).
- **Approach contrast:** A retargets existing jobs; B/C move to ELT and adopt
  Snowpipe/Streaming. Real-time needs push toward B/C.

## 4. Data transformation (Phase 5)

- **Decision guide (Snowflake):**
  - **Dynamic Tables** - declarative SQL pipelines (joins/aggregations,
    bronze/silver/gold), incremental refresh, TARGET_LAG >= 1 min. Preferred for
    new multi-table SQL pipelines.
  - **Streams & Tasks** - procedural logic, MERGE/upserts, stored procs, external
    calls, sub-minute or CRON scheduling, SCD Type 2.
  - **Materialized Views** - single-table query acceleration, always-current.
  - **dbt** - transformation framework/orchestration over the above.
- **Approach contrast:** A ports procedural ETL as-is (often Tasks). B introduces
  dbt + Dynamic Tables for new/refactored flows. C is ELT-native end to end.

## 5. Testing & validation (Phase 7)

- **Three levels:** (1) file/object - checksums on staged files; (2) reconciliation -
  row counts + aggregates (SUM/AVG/MIN/MAX) source vs target; (3) cell-level diff
  on business-critical tables. Then performance testing + UAT.
- **Automation:** SnowConvert AI two-sided verification for code parity; the
  `sql-verify` subagent for generated SQL.
- **Approach contrast:** A needs the strongest reconciliation (mechanical port is
  trusted only if numbers match). C needs the most validation effort because the
  model changed - parity is logical, not row-identical.

## 6. Consumption workloads (Phase 6)

- **BI repoint:** Tableau/Power BI native connectors; per-dashboard choice of
  live/DirectQuery vs extract/import. Isolate BI on dedicated warehouses.
- **SSRS:** not a recommended long-term target -> rebuild in Power BI/Tableau.
- **Modern consumption:** Semantic Views + Cortex Analyst/Search; Streamlit apps;
  data sharing / listings.
- **Approach contrast:** A repoints existing reports. B repoints + isolates +
  fixes hot queries. C adds the semantic layer and Cortex as a first-class
  consumption surface.

## Cross-cutting (Phases 1, 2, 8, 9)

- **Phase 1 Planning:** approach selection (this skill), inventory + triage
  (Retire candidates), success metrics, FinOps.
- **Phase 2 Environment/Security:** multi-account structure, RBAC hierarchy,
  network policies, resource monitors. Greenfield chance to fix security debt.
- **Phase 8 Deployment:** cutover style - big-bang vs **phased rollout**
  (recommended) vs **parallel run**; bridging so users see one system.
- **Phase 9 Optimize & Run:** warehouse right-sizing, auto-suspend, clustering,
  ongoing FinOps + governance.

# Approach Taxonomy

How the industry 6 Rs map onto the three canonical Snowflake DW migration
approaches this skill recommends. Repurchase and Retire/Retain are not standalone
options - they are moves tagged onto whichever approach fits.

## The 6 Rs (reference)

| R | Meaning | DW migration translation |
|---|---------|--------------------------|
| Rehost | Move as-is to new infra | SnowConvert mechanical conversion, same schema/logic |
| Replatform | Move with minor optimization | Convert + drop legacy physical clauses (DISTKEY, TABLESPACE), retarget ETL connection |
| Refactor | Restructure code without changing core architecture | Cursors to set-based, procs to Snowflake Scripting, ETL to ELT/dbt |
| Re-architect | Change the architecture materially | New data model (Data Vault/dimensional/medallion), declarative pipelines |
| Rebuild | Rewrite from scratch | New ELT-native build; legacy used only as a spec |
| Repurchase | Replace custom build with a product | Fivetran/managed connectors instead of hand-built ingestion |
| Retire / Retain | Decommission or leave in place | Drop unused/obsolete objects; archive cold data; keep a system out of scope |

## The three canonical approaches

### Approach A - Automated Lift & Shift (Rehost + Replatform)
- **What:** SnowConvert AI converts DDL/DML/procedural code; preserve the schema
  and logic. Drop legacy physical clauses. Retarget existing ETL connections.
- **Effort:** Lowest. **Risk-to-deliver:** Lowest. **Value capture:** Lowest.
- **When it wins:** cost/license-renewal driver, hard deadline, low team maturity,
  low-complexity codebase, explicit "minimal change" intent.
- **Cost:** carries legacy tech debt (row-by-row logic, batch assumptions);
  under-utilizes Snowflake; often a second project later to modernize.
- **Snowflake framing:** the docs' "lift and shift" path. Best as a stepping stone.

### Approach B - Selective Refactor (Replatform + Refactor)
- **What:** Convert everything, then modernize the high-value parts: rewrite
  cursor/loop procs as set-based SQL, move ETL to ELT (dbt + Dynamic Tables),
  remodel the most-queried tables, repoint BI.
- **Effort:** Medium. **Risk:** Medium. **Value capture:** Medium-High.
- **When it wins:** performance or regulatory driver, medium complexity, mixed
  team maturity, SSIS/Informatica present, balanced timeline.
- **Cost:** requires judgment on what to modernize vs port; scope can creep.
- **Snowflake framing:** the pragmatic default for most enterprises.

### Approach C - Re-architect / Rewrite (Re-architect + Rebuild)
- **What:** Design a new target model (Data Vault 2.0 / Kimball / OBT + medallion),
  build ELT-native pipelines (dbt + Dynamic Tables), adopt Iceberg where useful,
  stand up a semantic layer + Cortex. Legacy is a spec, not a source of code.
- **Effort:** Highest. **Risk:** Highest. **Value capture:** Highest.
- **When it wins:** AI or consolidation driver, high team maturity, explicit
  rewrite/greenfield appetite, real-time needs, heavily degraded legacy model.
- **Cost:** longest time-to-value; needs strong Snowflake skills and governance.
- **Snowflake framing:** the docs' "re-architecture" path; unlocks the platform.

## Tagging Repurchase / Retire

- **Repurchase** when ingestion is hand-built and brittle, or the team lacks
  capacity to maintain pipelines: recommend Fivetran/managed connectors or
  Openflow. Applies most often inside Approach B or C.
- **Retire** when the inventory shows unused objects, redundant marts, or cold
  data: recommend dropping/archiving rather than migrating. Applies to every
  approach and reduces scope - call it out in Step 1 triage.
- **Retain** when a source system is out of scope or has a dependency that cannot
  move yet: document the bridge and keep it explicit.

## Ordering rule

The most-recommended approach is **dynamic** - it is whichever scores highest fit
for the customer's signals, not a fixed favorite. Always present the full
spectrum so the recommendation is credible, and state plainly why #1 beats #2.

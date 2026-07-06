# Signal Extraction

The decision signals the scorer consumes, and how to fill the ones the parser
cannot infer. `extract_signals.py` produces these automatically from a code drop
+ notes; everything under `_needs_review` must be hand-filled from the meeting
notes or a follow-up question.

## Signals schema (signals.json)

| Field | Type | Source | Used by matrix |
|-------|------|--------|----------------|
| `source_platform` | string | code fingerprints | yes (oracle/teradata rows) |
| `object_inventory` | object | CREATE counts | LOE handoff |
| `object_total` | int | derived | context |
| `procedural_object_count` | int | proc+func+package | context |
| `code_complexity` | low/med/high | anti-pattern density | yes |
| `anti_patterns` | object | cursor/dynamic_sql/etc. | context + memo |
| `etl_tools` | list | file ext + content | yes (ssis/informatica/dbt) |
| `primary_drivers` | list | notes | yes (the strongest lever) |
| `tight_deadline` | bool | notes | yes |
| `team_maturity` | low/med/high | notes | yes |
| `real_time_need` | bool | notes | yes |
| `bi_tools` | list | notes | memo (consumption) |
| `rewrite_appetite` | bool | notes | yes |
| `preserve_appetite` | bool | notes | yes |
| `volumes_mentioned` | list | notes regex | LOE handoff |

## Fields to hand-fill (`_needs_review`)

These rarely appear cleanly in code; get them from notes or ask the user:

- `data_volume_class` - lt_1tb / 1_10tb / 10_100tb / 100tb_1pb / gt_1pb
- `sla_class` - daily / hourly / minute / sub-minute
- `timeline_weeks` - target window for cutover
- `budget` - rough band or constraint
- `compliance` - GDPR / HIPAA / PCI / SOX / none
- `consumer_count` - number of downstream BI/report consumers

## How drivers dominate

`primary_drivers` is the heaviest lever in the matrix. If the parser found none
(`["unspecified"]`), do NOT proceed to scoring on autopilot - ask the user for
the primary driver, because it usually decides the ranking:

- cost / deadline -> pulls toward A
- performance / regulatory -> pulls toward B
- AI / consolidation / rewrite-appetite -> pulls toward C

## When code is absent

If only notes are available, `object_*` and `anti_patterns` will be empty and
`code_complexity` defaults to low. The ranking still works off drivers + intent
signals, but mark the recommendation **preliminary** and re-run when code lands.

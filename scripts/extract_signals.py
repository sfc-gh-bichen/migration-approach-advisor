#!/usr/bin/env python3
"""
extract_signals.py - Parse a customer code drop + meeting notes into a normalized
signals.json for the migration-approach-advisor skill.

Heuristic by design. The skill agent reviews and hand-fills anything the parser
misses (see references/signal-extraction.md). Pure standard library so it runs
under `uv run` with no extra deps.

Usage:
  python extract_signals.py --code-dir <dir> [--notes <file>] --out <signals.json>
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter


# Source-dialect fingerprints: dialect -> list of case-insensitive regex markers.
DIALECT_MARKERS = {
    "sqlserver": [r"\bGETDATE\(\)", r"\bISNULL\(", r"\bNVARCHAR\b", r"\[dbo\]\.",
                  r"\bDATETIME2\b", r"\bIDENTITY\b", r"@@", r"\bEXEC\b"],
    "oracle": [r"\bSYSDATE\b", r"\bNVL\(", r"\bVARCHAR2\b", r"\bDUAL\b",
               r"\bCONNECT BY\b", r"\bPACKAGE\b", r"\bDBMS_\w+", r"\bNUMBER\("],
    "teradata": [r"\bBTEQ\b", r"\bQUALIFY\b", r"\bSEL\b", r"\bMULTISET\b",
                 r"\bHELP\s+TABLE\b", r"\bCOLLECT\s+STATISTICS\b"],
    "redshift": [r"\bDISTKEY\b", r"\bSORTKEY\b", r"\bDISTSTYLE\b", r"\bENCODE\b",
                 r"\bGETDATE\(\)", r"\bUNLOAD\b", r"\bSUPER\b"],
    "postgres": [r"\bSERIAL\b", r"\bplpgsql\b", r"\bRETURNING\b", r"\b::\w+",
                 r"\bGENERATE_SERIES\("],
    "mysql": [r"\bAUTO_INCREMENT\b", r"\bENGINE=", r"`\w+`", r"\bLIMIT\s+\d+,\s*\d+"],
    "bigquery": [r"\bSTRUCT<", r"\bARRAY<", r"`[\w-]+\.[\w-]+\.[\w-]+`",
                 r"\bUNNEST\(", r"\b_PARTITIONTIME\b"],
}

# ETL / orchestration tool fingerprints (filename ext + content markers).
ETL_MARKERS = {
    "ssis": [r"\.dtsx$", r"DTS:", r"SSIS"],
    "informatica": [r"\.xml$.*POWERMART", r"INFORMATICA", r"\bmapping\b.*\bmapplet\b"],
    "datastage": [r"\.dsx$", r"DataStage", r"DSJob"],
    "talend": [r"\.item$", r"talend", r"tMap"],
    "pentaho": [r"\.ktr$", r"\.kjb$", r"pentaho", r"kettle"],
    "dbt": [r"\{\{\s*ref\(", r"\{\{\s*config\(", r"dbt_project\.yml"],
    "airflow": [r"\bDAG\(", r"airflow", r"PythonOperator"],
}

OBJECT_PATTERNS = {
    "table": r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:GLOBAL\s+|LOCAL\s+|MULTISET\s+|SET\s+)?TABLE\b",
    "view": r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:MATERIALIZED\s+)?VIEW\b",
    "procedure": r"\bCREATE\s+(?:OR\s+REPLACE\s+)?PROC(?:EDURE)?\b",
    "function": r"\bCREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\b",
    "trigger": r"\bCREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\b",
    "package": r"\bCREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\b",
}

# Complexity / anti-pattern markers that push away from lift-and-shift.
COMPLEXITY_MARKERS = {
    "cursor": r"\b(DECLARE\s+\w+\s+CURSOR|OPEN\s+\w+|FETCH\s+NEXT)\b",
    "dynamic_sql": r"\b(EXEC\s*\(|EXECUTE\s+IMMEDIATE|sp_executesql)\b",
    "while_loop": r"\bWHILE\b",
    "temp_table": r"(#\w+|\bGLOBAL\s+TEMPORARY\b|\bCREATE\s+TEMP)",
    "merge": r"\bMERGE\s+INTO\b",
}

NOTE_SIGNALS = {
    "driver_cost": r"\b(cost|tco|cheaper|spend|budget|license\s+renewal|expensive)\b",
    "driver_performance": r"\b(slow|performance|latency|sla|too\s+long|hours\s+to\s+run)\b",
    "driver_ai": r"\b(ai|ml|machine\s+learning|cortex|llm|gen\s*ai|genai)\b",
    "driver_consolidation": r"\b(consolidat|m&a|merger|acquisition|multiple\s+warehouses|single\s+source)\b",
    "driver_regulatory": r"\b(regulat|complian|gdpr|hipaa|audit|sox|pci)\b",
    "tight_deadline": r"\b(deadline|urgent|by\s+q[1-4]|end\s+of\s+year|asap|hard\s+date)\b",
    "low_maturity": r"\b(new\s+to\s+snowflake|first\s+snowflake|no\s+snowflake|learning)\b",
    "high_maturity": r"\b(snowflake\s+native|already\s+on\s+snowflake|mature|experienced)\b",
    "real_time": r"\b(real[-\s]?time|streaming|kafka|cdc|sub[-\s]?second|near\s+real)\b",
    "bi_tableau": r"\btableau\b",
    "bi_powerbi": r"\b(power\s*bi|powerbi)\b",
    "bi_ssrs": r"\bssrs\b",
    "rewrite_appetite": r"\b(rewrite|re-?architect|modernize|greenfield|clean\s+slate|fresh\s+start)\b",
    "preserve_appetite": r"\b(lift\s+and\s+shift|like\s+for\s+like|minimal\s+change|as[-\s]is|preserve)\b",
}

VOLUME_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(tb|pb|gb)\b", re.I)


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def scan_code_dir(code_dir: str) -> dict:
    object_counts: Counter = Counter()
    complexity_counts: Counter = Counter()
    dialect_hits: Counter = Counter()
    etl_hits: Counter = Counter()
    file_count = 0

    for root, _dirs, files in os.walk(code_dir):
        for fn in files:
            path = os.path.join(root, fn)
            lower_name = fn.lower()
            # ETL detection by extension
            for tool, markers in ETL_MARKERS.items():
                for m in markers:
                    if m.startswith(r"\.") and re.search(m, lower_name):
                        etl_hits[tool] += 1
            if not lower_name.endswith((".sql", ".ddl", ".txt", ".prc", ".vw",
                                        ".tab", ".bteq", ".hql", ".py")):
                # still allow ETL files to be counted above; skip content scan
                if not any(lower_name.endswith(e) for e in
                           (".dtsx", ".dsx", ".ktr", ".kjb", ".item", ".xml")):
                    continue
            text = read_text(path)
            if not text:
                continue
            file_count += 1
            for dialect, markers in DIALECT_MARKERS.items():
                for m in markers:
                    if re.search(m, text, re.I):
                        dialect_hits[dialect] += 1
            for tool, markers in ETL_MARKERS.items():
                for m in markers:
                    if not m.startswith(r"\.") and re.search(m, text, re.I):
                        etl_hits[tool] += 1
            for obj, pat in OBJECT_PATTERNS.items():
                object_counts[obj] += len(re.findall(pat, text, re.I))
            for marker, pat in COMPLEXITY_MARKERS.items():
                complexity_counts[marker] += len(re.findall(pat, text, re.I))

    dialect = dialect_hits.most_common(1)[0][0] if dialect_hits else "unknown"
    return {
        "files_scanned": file_count,
        "detected_dialect": dialect,
        "dialect_signal_strength": dict(dialect_hits),
        "object_counts": dict(object_counts),
        "complexity_markers": dict(complexity_counts),
        "etl_tools": sorted(etl_hits.keys()),
    }


def scan_notes(notes_path: str) -> dict:
    text = read_text(notes_path)
    found = {}
    if not text:
        return {"signals": found, "volumes_mentioned": []}
    for sig, pat in NOTE_SIGNALS.items():
        if re.search(pat, text, re.I):
            found[sig] = True
    volumes = [f"{m.group(1)}{m.group(2).upper()}" for m in VOLUME_PATTERN.finditer(text)]
    return {"signals": found, "volumes_mentioned": volumes}


def derive(code: dict, notes: dict) -> dict:
    """Roll raw scans up into the decision signals the scorer consumes."""
    obj = code.get("object_counts", {})
    cx = code.get("complexity_markers", {})
    proc_like = obj.get("procedure", 0) + obj.get("function", 0) + obj.get("package", 0)
    total_objs = sum(obj.values()) or 1

    # Procedural density: share of anti-pattern markers relative to objects.
    proc_signal = cx.get("cursor", 0) + cx.get("dynamic_sql", 0) + cx.get("while_loop", 0)
    if proc_signal == 0 and proc_like == 0:
        code_complexity = "low"
    elif proc_signal > 20 or cx.get("dynamic_sql", 0) > 5 or proc_like > 100:
        code_complexity = "high"
    else:
        code_complexity = "medium"

    nsig = notes.get("signals", {})
    drivers = [k.replace("driver_", "") for k in nsig if k.startswith("driver_")]

    return {
        "source_platform": code.get("detected_dialect", "unknown"),
        "object_inventory": obj,
        "object_total": total_objs,
        "procedural_object_count": proc_like,
        "code_complexity": code_complexity,
        "anti_patterns": {k: v for k, v in cx.items() if v},
        "etl_tools": code.get("etl_tools", []),
        "primary_drivers": drivers or ["unspecified"],
        "tight_deadline": bool(nsig.get("tight_deadline")),
        "team_maturity": ("high" if nsig.get("high_maturity")
                          else "low" if nsig.get("low_maturity") else "medium"),
        "real_time_need": bool(nsig.get("real_time")),
        "bi_tools": [b.replace("bi_", "") for b in nsig if b.startswith("bi_")],
        "rewrite_appetite": bool(nsig.get("rewrite_appetite")),
        "preserve_appetite": bool(nsig.get("preserve_appetite")),
        "volumes_mentioned": notes.get("volumes_mentioned", []),
        "_needs_review": [
            "data_volume_class", "sla_class", "timeline_weeks", "budget",
            "compliance", "consumer_count",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract migration decision signals.")
    ap.add_argument("--code-dir", help="Directory of source SQL/ETL files.")
    ap.add_argument("--notes", help="Meeting-notes / transcript text file.")
    ap.add_argument("--out", required=True, help="Output signals.json path.")
    args = ap.parse_args()

    code = scan_code_dir(args.code_dir) if args.code_dir else {}
    notes = scan_notes(args.notes) if args.notes else {"signals": {}, "volumes_mentioned": []}
    signals = derive(code, notes)
    signals["_raw_code_scan"] = code
    signals["_raw_note_scan"] = notes

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2)
    print(f"Wrote {args.out}")
    print(f"  platform={signals['source_platform']} "
          f"complexity={signals['code_complexity']} "
          f"drivers={signals['primary_drivers']}")
    print(f"  Review/fill these by hand: {signals['_needs_review']}")


if __name__ == "__main__":
    main()

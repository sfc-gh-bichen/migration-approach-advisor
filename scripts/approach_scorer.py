#!/usr/bin/env python3
"""
approach_scorer.py - Score and rank the three canonical Snowflake migration
approaches from a signals.json.

Approaches:
  A = Automated Lift & Shift   (Rehost + Replatform)
  B = Selective Refactor       (Replatform + Refactor)
  C = Re-architect / Rewrite   (Re-architect + Rebuild)

Default output is qualitative (effort / risk / T-shirt per dimension + overall
fit). When --code-metrics is supplied, the scorer additionally imports the kit
loe_calculator.py to attach a rough P50 per approach. If the kit module cannot be
imported, it degrades gracefully and records a note.

Pure standard library (json/csv/argparse/importlib). Runs under `uv run`.

Usage:
  python approach_scorer.py --signals <signals.json> --matrix <decision-matrix.csv>
      --out <approach-scores.json> [--code-metrics <metrics.json>]
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os

APPROACHES = ["A", "B", "C"]
APPROACH_NAMES = {
    "A": "Automated Lift & Shift",
    "B": "Selective Refactor",
    "C": "Re-architect / Rewrite",
}
DIMENSIONS = [
    "code_conversion",
    "historical_data",
    "data_ingestion",
    "data_transformation",
    "testing_validation",
    "consumption",
]

# Baseline effort/risk profile per approach per dimension (1=low .. 3=high).
# These are the "all else equal" priors; signal affinities shift the fit score,
# not these structural effort/risk costs.
BASE_EFFORT = {
    "A": {"code_conversion": 2, "historical_data": 1, "data_ingestion": 1,
          "data_transformation": 1, "testing_validation": 2, "consumption": 1},
    "B": {"code_conversion": 2, "historical_data": 1, "data_ingestion": 2,
          "data_transformation": 2, "testing_validation": 2, "consumption": 2},
    "C": {"code_conversion": 3, "historical_data": 2, "data_ingestion": 3,
          "data_transformation": 3, "testing_validation": 3, "consumption": 3},
}
BASE_RISK = {
    "A": {"code_conversion": 1, "historical_data": 1, "data_ingestion": 1,
          "data_transformation": 2, "testing_validation": 1, "consumption": 1},
    "B": {"code_conversion": 2, "historical_data": 1, "data_ingestion": 2,
          "data_transformation": 2, "testing_validation": 2, "consumption": 2},
    "C": {"code_conversion": 3, "historical_data": 2, "data_ingestion": 2,
          "data_transformation": 3, "testing_validation": 3, "consumption": 3},
}

LEVEL = {1: "Low", 2: "Med", 3: "High"}


def load_matrix(path: str) -> list[dict]:
    """decision-matrix.csv columns: signal,condition,A,B,C,rationale."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def signal_truthy(signals: dict, signal: str, condition: str) -> bool:
    """Evaluate a matrix row's signal/condition against signals.json."""
    val = signals.get(signal)
    cond = (condition or "").strip().lower()
    if cond in ("true", "present", "yes"):
        return bool(val)
    if cond in ("false", "absent", "no"):
        return not bool(val)
    if isinstance(val, list):
        return cond in [str(x).lower() for x in val]
    if val is None:
        return False
    return str(val).lower() == cond


def score(signals: dict, matrix: list[dict]) -> dict:
    fit = {a: 0.0 for a in APPROACHES}
    drivers_applied = {a: [] for a in APPROACHES}

    for row in matrix:
        if not signal_truthy(signals, row["signal"], row["condition"]):
            continue
        for a in APPROACHES:
            try:
                w = float(row.get(a, 0) or 0)
            except ValueError:
                w = 0.0
            if w:
                fit[a] += w
                drivers_applied[a].append(
                    {"signal": row["signal"], "condition": row["condition"],
                     "weight": w, "rationale": row.get("rationale", "")})

    results = []
    for a in APPROACHES:
        dims = {}
        for d in DIMENSIONS:
            dims[d] = {
                "effort": LEVEL[BASE_EFFORT[a][d]],
                "risk": LEVEL[BASE_RISK[a][d]],
            }
        total_effort = sum(BASE_EFFORT[a].values())
        tshirt = ("S" if total_effort <= 8 else "M" if total_effort <= 12
                  else "L" if total_effort <= 16 else "XL")
        results.append({
            "approach": a,
            "name": APPROACH_NAMES[a],
            "fit_score": round(fit[a], 2),
            "tshirt": tshirt,
            "dimensions": dims,
            "applied_signals": drivers_applied[a],
        })

    results.sort(key=lambda r: r["fit_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return {"ranked": results, "signal_count": len(matrix)}


def attach_loe(result: dict, signals: dict, code_metrics_path: str,
               kit_calc_path: str) -> dict:
    """Best-effort import of the kit loe_calculator.py to add a P50 per approach."""
    note = None
    if not os.path.exists(kit_calc_path):
        note = f"loe_calculator not found at {kit_calc_path}; skipped quantitative P50."
        result["loe_note"] = note
        return result
    try:
        spec = importlib.util.spec_from_file_location("loe_calculator", kit_calc_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
    except Exception as e:  # noqa: BLE001
        result["loe_note"] = f"Could not import loe_calculator: {e}"
        return result

    try:
        with open(code_metrics_path, encoding="utf-8") as f:
            metrics = json.load(f)
    except OSError as e:
        result["loe_note"] = f"Could not read code-metrics: {e}"
        return result

    # Map metrics -> kit Project. Approach C carries a remodeling multiplier,
    # B a partial one, A none (mechanical conversion only).
    inv = metrics.get("object_counts", signals.get("object_inventory", {}))
    try:
        invs = [mod.ObjectInventory(k, total_count=int(v), use_default_split=True)
                for k, v in inv.items() if k in mod.PER_OBJECT_HOURS and int(v) > 0]
        ewi = metrics.get("ewi", {})
        ewi_obj = mod.EWICounts(**{k: int(ewi.get(k, 0))
                                   for k in ("critical", "high", "medium", "low")})
        rework_mult = {"A": 1.0, "B": 1.25, "C": 1.6}
        for r in result["ranked"]:
            proj = mod.Project(inventories=invs, ewi=ewi_obj,
                               team_size=int(metrics.get("team_size", 3)))
            rep = proj.report()
            p50 = (rep.get("total_hours_p50") or rep.get("p50_hours")
                   or rep.get("hours_p50") or rep.get("p50"))
            if p50 is not None:
                r["p50_hours_estimate"] = round(float(p50) * rework_mult[r["approach"]], 1)
        result["loe_note"] = "P50 attached via kit loe_calculator (rework-multiplied per approach)."
    except Exception as e:  # noqa: BLE001
        result["loe_note"] = f"loe_calculator imported but scoring failed: {e}"
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Rank Snowflake migration approaches.")
    ap.add_argument("--signals", required=True)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--code-metrics", help="Optional code metrics JSON for P50.")
    ap.add_argument("--kit-calc",
                    default=os.path.expanduser(
                        "~/Documents/Snowflake/CortexCode/Projects/"
                        "bchen-Modernization-Assessment/kit/scoring/loe_calculator.py"),
                    help="Path to kit loe_calculator.py.")
    args = ap.parse_args()

    with open(args.signals, encoding="utf-8") as f:
        signals = json.load(f)
    matrix = load_matrix(args.matrix)
    result = score(signals, matrix)

    if args.code_metrics:
        result = attach_loe(result, signals, args.code_metrics, args.kit_calc)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {args.out}")
    for r in result["ranked"]:
        line = f"  #{r['rank']} {r['name']} (fit={r['fit_score']}, size={r['tshirt']})"
        if "p50_hours_estimate" in r:
            line += f", ~P50 {r['p50_hours_estimate']}h"
        print(line)
    if result.get("loe_note"):
        print(f"  LOE: {result['loe_note']}")


if __name__ == "__main__":
    main()

"""Audit row, patient, and series counts across the AI4Quality pipeline.

Run from the repository root:
    python scripts/pipeline_count_audit.py
    python scripts/pipeline_count_audit.py --json audit.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREPROCESSING = ROOT / "_00_Preprocessing" / "OUTPUTS"
QC = ROOT / "_02_QualityCheck" / "OUTPUTS"
RCA = ROOT / "_03_RootCauseAnalysis"
DB = ROOT / "_04_Recommendations" / "data" / "ai4quality_recommendations.sqlite"


def frame(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def identifiers(data: pd.DataFrame | None, column: str) -> set[str]:
    if data is None or column not in data:
        return set()
    return set(data[column].dropna().astype(str))


def series_identifiers(data: pd.DataFrame | None) -> set[str]:
    if data is None:
        return set()
    if "series_path" in data:
        return identifiers(data, "series_path")
    if "ct_id" in data and "series_folder" in data:
        return {
            f"{ct_id}|{series_folder}"
            for ct_id, series_folder in zip(data["ct_id"], data["series_folder"])
            if pd.notna(ct_id) and pd.notna(series_folder)
        }
    return set()


def stage(name: str, data: pd.DataFrame | None) -> dict[str, Any]:
    if data is None:
        return {"name": name, "available": False}
    return {
        "name": name,
        "available": True,
        "rows": len(data),
        "patients": len(identifiers(data, "ct_id")),
        "series": len(series_identifiers(data)),
    }


def database_report() -> dict[str, Any]:
    if not DB.exists():
        return {"available": False, "path": str(DB)}
    report: dict[str, Any] = {"available": True, "path": str(DB), "tables": {}}
    with sqlite3.connect(DB) as connection:
        table_names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for table in table_names:
            columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
            rows = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            table_report: dict[str, Any] = {"rows": rows, "columns": columns}
            if "ct_id" in columns:
                table_report["patients"] = connection.execute(
                    f"SELECT COUNT(DISTINCT ct_id) FROM {table} WHERE ct_id IS NOT NULL"
                ).fetchone()[0]
                table_report["null_ct_id"] = connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE ct_id IS NULL"
                ).fetchone()[0]
            if "series_folder" in columns:
                table_report["series"] = connection.execute(
                    f"SELECT COUNT(DISTINCT COALESCE(CAST(ct_id AS TEXT), '') || '|' || series_folder) "
                    f"FROM {table} WHERE series_folder IS NOT NULL"
                ).fetchone()[0]
            report["tables"][table] = table_report
    return report


def main() -> dict[str, Any]:
    decisions = frame(PREPROCESSING / "decisions.csv")
    retained = frame(PREPROCESSING / "retained_series.csv")
    unified = frame(PREPROCESSING / "retained_series_unified_filtered.csv")
    qc_detail = frame(QC / "roi_hu_qc_results.csv")
    qc_series = frame(QC / "roi_hu_qc_summary.csv")
    qc_patients = frame(QC / "patient_hu_qc_summary.csv")
    rca = frame(RCA / "rca_results_all.csv")

    stages = [
        stage("preprocessing decisions", decisions),
        stage("accepted retained series", retained),
        stage("unified QC input series", unified),
        stage("QC ROI evaluations", qc_detail),
        stage("QC series summary", qc_series),
        stage("QC patient summary", qc_patients),
        stage("RCA schema results", rca),
    ]
    if decisions is not None and "status" in decisions:
        stages[0]["status_counts"] = decisions["status"].value_counts(dropna=False).to_dict()
    if qc_detail is not None and "status" in qc_detail:
        stages[3]["status_counts"] = qc_detail["status"].value_counts(dropna=False).to_dict()
    if rca is not None and "rca_schema" in rca:
        stages[6]["schemas"] = sorted(rca["rca_schema"].dropna().astype(str).unique())

    comparisons: dict[str, Any] = {}
    if unified is not None and qc_detail is not None:
        input_keys = set(zip(unified.ct_id.astype(str), unified.series_folder.astype(str)))
        qc_keys = set(zip(qc_detail.ct_id.astype(str), qc_detail.series_folder.astype(str)))
        comparisons["unified_to_qc"] = {
            "input_series": len(input_keys),
            "evaluated_series": len(qc_keys),
            "not_evaluated_series": len(input_keys - qc_keys),
            "unexpected_qc_series": len(qc_keys - input_keys),
        }
    if qc_detail is not None and rca is not None:
        critical = qc_detail[qc_detail.status.isin(["critical_low", "critical_high"])]
        critical_keys = set(zip(critical.ct_id.astype(str), critical.series_folder.astype(str)))
        rca_keys = set(zip(rca.ct_id.astype(str), rca.series_folder.astype(str)))
        comparisons["qc_to_rca"] = {
            "critical_qc_series": len(critical_keys),
            "rca_series": len(rca_keys),
            "rca_rows": len(rca),
            "rca_schemas": rca.rca_schema.nunique() if "rca_schema" in rca else 0,
            "critical_series_without_rca": len(critical_keys - rca_keys),
        }
    if qc_patients is not None and rca is not None:
        comparisons["qc_to_rca_patients"] = {
            "qc_patients": len(identifiers(qc_patients, "ct_id")),
            "rca_patients": len(identifiers(rca, "ct_id")),
            "qc_patients_without_rca": len(identifiers(qc_patients, "ct_id") - identifiers(rca, "ct_id")),
        }

    return {"root": str(ROOT), "stages": stages, "comparisons": comparisons, "database": database_report()}


def print_report(report: dict[str, Any]) -> None:
    print(f"Repository: {report['root']}\n")
    print("STAGES")
    for item in report["stages"]:
        if not item.get("available"):
            print(f"- {item['name']}: MISSING")
            continue
        line = f"- {item['name']}: rows={item['rows']}, patients={item['patients']}, series={item['series']}"
        if "schemas" in item:
            line += f", schemas={len(item['schemas'])}"
        print(line)
        if "status_counts" in item:
            print(f"  statuses={item['status_counts']}")

    print("\nCOMPARISONS")
    for name, values in report["comparisons"].items():
        print(f"- {name}: {values}")

    print("\nDATABASE")
    database = report["database"]
    if not database["available"]:
        print("- MISSING")
    else:
        for name, values in database["tables"].items():
            print(f"- {name}: rows={values['rows']}, patients={values.get('patients', 'n/a')}, series={values.get('series', 'n/a')}, null_ct_id={values.get('null_ct_id', 0)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Also write the audit as JSON")
    args = parser.parse_args()
    result = main()
    print_report(result)
    if args.json:
        args.json.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json}")

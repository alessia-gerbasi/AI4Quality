"""Generate and persist LLM recommendations without the Streamlit dashboard."""
import argparse
import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

from build_database import DB_PATH, build_database
from llm_recommendations import DEFAULT_MODEL, generate_recommendation


def _normalise_notes(values: pd.Series) -> list[str]:
    notes = values.fillna("")
    notes = notes[notes.str.strip().ne("")].map(
        lambda note: "; ".join(part.strip() for part in re.split(r"[|;]", str(note)) if part.strip())
    )
    return notes.drop_duplicates().tolist()


def _patient_inputs(data: dict[str, pd.DataFrame], patient_id: str) -> tuple[dict, list[dict], list[dict]]:
    rca = data["rca"]
    quality = data["image_quality"]
    patient = rca[rca.ct_id.astype(str).eq(patient_id)]
    quality = quality[quality.ct_id.astype(str).eq(patient_id)]
    patient_series = data["series"][data["series"].ct_id.astype(str).eq(patient_id)]
    quality_series = quality[["series_folder"]].dropna().drop_duplicates()
    analyzed_series = patient_series.merge(quality_series, on="series_folder", how="inner")

    warning_rows = data["patient_warnings"][data["patient_warnings"].ct_id.astype(str).eq(patient_id)]
    source = {"ct_id": patient_id, "series": analyzed_series.to_dict("records")}
    if not warning_rows.empty:
        source["patient_warning"] = warning_rows.iloc[0].to_dict()

    injector_rows = data["injector_data"][data["injector_data"].ct_id.astype(str).eq(patient_id)]
    if not injector_rows.empty:
        source["injector_data"] = injector_rows.iloc[0].to_dict()

    findings = []
    for _, row in patient.iterrows():
        diagnosis_text = row.get("rca_diagnoses")
        if pd.isna(diagnosis_text) or not str(diagnosis_text).strip():
            diagnosis_text = row.get("rca_label", "")
        for diagnosis in str(diagnosis_text).split(" | "):
            if diagnosis and diagnosis != "nan":
                findings.append({
                    "Schema": row.get("rca_schema"),
                    "Series": row.get("series_folder"),
                    "Finding": diagnosis,
                    "Explanation": row.get("rca_explanation", ""),
                    "Recommendations": row.get("rca_recommendations", ""),
                })
    for _, row in quality.iterrows():
        if str(row.get("status", "")).lower() not in {"optimal", "acceptable_low", "acceptable_high", "nan"}:
            findings.append({
                "Schema": "image_quality",
                "Series": row.get("series_folder"),
                "Finding": f"{row.get('roi_name')} {row.get('status')}",
                "Explanation": f"{row.get('metric_name')}: evaluated value {row.get('evaluated_value')}",
                "Recommendations": "Review image-quality measurement and acquisition protocol.",
            })

    source["notes"] = _normalise_notes(patient.get("rca_notes", pd.Series(dtype=str)))
    exam_findings = rca[rca.ct_id.astype(str).eq(patient_id)].to_dict("records")
    exam_findings.extend(quality.to_dict("records"))
    return source, findings, exam_findings


def generate_all(ct_id: str | None = None, model: str = DEFAULT_MODEL) -> int:
    build_database()
    with sqlite3.connect(DB_PATH) as db:
        data = {
            name: pd.read_sql_query(f"SELECT * FROM {name}", db)
            for name in ("series", "image_quality", "rca", "injector_data", "patient_warnings")
        }
        patient_ids = set(data["image_quality"].ct_id.dropna().astype(str))
        patient_ids.update(data["rca"].ct_id.dropna().astype(str))
        if ct_id is not None:
            patient_ids &= {str(ct_id)}
            if not patient_ids:
                raise ValueError(f"Patient {ct_id} was not found in QC or RCA data")

        generated = 0
        for patient_id in sorted(patient_ids, key=lambda value: int(value) if value.isdigit() else value):
            source, findings, exam_findings = _patient_inputs(data, patient_id)
            text, source_name = generate_recommendation(source, findings, exam_findings, model=model)
            db.execute(
                "DELETE FROM recommendations WHERE ct_id = ? AND scope = 'exam' AND model = ?",
                (patient_id, model),
            )
            db.execute(
                "INSERT INTO recommendations VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (patient_id, None, "exam", model, source_name, text, json.dumps({"findings": findings, "source": source}, default=str)),
            )
            generated += 1
            print(f"Generated patient {patient_id} ({source_name})")
        db.commit()
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate all AI4Quality LLM recommendations without Streamlit")
    parser.add_argument("--ct-id", help="Generate only this patient (default: all QC/RCA patients)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()
    print(f"Generated {generate_all(args.ct_id, args.model)} recommendation(s) in {DB_PATH}")


if __name__ == "__main__":
    main()

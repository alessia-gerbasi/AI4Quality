"""Simple visual recommendations dashboard."""
import sqlite3
import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from build_database import DB_PATH, build_database
from llm_recommendations import DEFAULT_MODEL, generate_recommendation, image_quality_findings

FINDING_LABELS = {
    "missing weight": "Patient weight missing for optimal dose computation",
    "contrast_load_input_missing": "Patient weight missing for contrast-load range",
    "saline_volume_high": "Saline volume high",
    "saline_volume_low": "Saline volume low",
    "contrast_volume_high": "Contrast volume high",
    "contrast_volume_low": "Contrast volume low",
    "idr_high": "IDR high",
    "idr_low": "IDR low",
    "flow_rate_high": "Flow rate high",
    "flow_rate_low": "Flow rate low",
    "pressure_high": "Pressure high",
    "protocol_execution_error": "Executed protocol differs from programmed",
    "injection_duration_low": "Injection duration short relative to scan duration",
    "injection_duration_high": "Injection duration long relative to scan duration",
}


def load_data():
    if not DB_PATH.exists():
        build_database()
    with sqlite3.connect(DB_PATH) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        exam_columns = {row[1] for row in db.execute("PRAGMA table_info(exams)")} if "exams" in tables else set()
        quality_columns = {row[1] for row in db.execute("PRAGMA table_info(image_quality)")}
        if "patient_warnings" not in tables or "attenuation_consistency" not in quality_columns or "patient_name" in exam_columns:
            build_database()
            return load_data()
        return {name: pd.read_sql_query(f"SELECT * FROM {name}", db) for name in ("exams", "series", "image_quality", "rca", "injector_data", "patient_warnings")}


def _stored_recommendation_is_stale(patient_id: str, input_json: str | None, data: dict[str, pd.DataFrame]) -> bool:
    patient_dose = data["rca"][
        data["rca"].ct_id.astype(str).eq(str(patient_id))
        & data["rca"].rca_schema.fillna("").astype(str).eq("dose_schema_v1")
    ]
    has_missing_weight = patient_dose.rca_label.fillna("").astype(str).str.lower().eq("missing weight").any()
    input_text = str(input_json or "").lower()
    has_missing_weight_input = "missing weight" in input_text or "patient weight missing" in input_text
    return has_missing_weight and not has_missing_weight_input


def main():
    st.set_page_config(page_title="AI4Quality Recommendations", layout="wide")
    st.title("AI4Quality Recommendations")
    st.caption("What went wrong, why it matters, and what to review in the protocol.")
    if st.sidebar.button("Refresh database"):
        build_database()
        st.rerun()
    data = load_data()
    st.sidebar.header("Case")
    st.sidebar.caption("Recommended local model: qwen2.5:7b")
    patient_ids = set()
    for table in (data["image_quality"], data["rca"]):
        if "ct_id" in table:
            patient_ids.update(table.ct_id.dropna().astype(str))
    patients = sorted(patient_ids)
    if not patients:
        st.warning("No analyzed sequences available. Run preprocessing and quality analysis first.")
        return
    patient_id = st.sidebar.selectbox("Patient", patients)
    rca = data["rca"]
    patient = rca[rca.ct_id.astype(str).eq(patient_id)]
    selected = patient
    quality = data["image_quality"][data["image_quality"].ct_id.astype(str).eq(patient_id)]
    patient_series = data["series"][data["series"].ct_id.astype(str).eq(patient_id)].copy()
    quality_series = quality[["series_folder"]].dropna().drop_duplicates()
    analyzed_series = patient_series.merge(quality_series, on="series_folder", how="inner")
    quality_for_patient = quality.copy()
    if not analyzed_series.empty:
        quality_status = quality_for_patient.groupby("series_folder")["status"].agg(
            lambda values: ", ".join(sorted(set(str(value) for value in values if pd.notna(value))))
        )
        analyzed_series["quality_status"] = analyzed_series["series_folder"].map(quality_status).fillna("not reported")

    st.subheader("Analyzed sequences")
    if analyzed_series.empty:
        st.info("No retained sequence metadata is available for this patient.")
    else:
        st.dataframe(
            analyzed_series[["series_folder", "phase_name", "procedure_code", "scanner", "quality_status"]],
            hide_index=True,
            width="stretch",
        )

    warning_rows = data["patient_warnings"][data["patient_warnings"].ct_id.astype(str).eq(patient_id)]
    if not warning_rows.empty:
        patient_warning = warning_rows.iloc[0]
        warning_priority = str(patient_warning.get("warning_priority", "none"))
        warning_text = str(patient_warning.get("warning", ""))
        if warning_priority != "none" and warning_text.strip().lower() not in {"", "nan", "none"}:
            warning_colors = {
                "low": ("#fff7cc", "#a16207"),
                "medium": ("#ffedd5", "#c2410c"),
                "high": ("#fee2e2", "#b91c1c"),
            }
            background, foreground = warning_colors.get(warning_priority, ("#fef3c7", "#92400e"))
            st.markdown(
                f"<div style='background:{background};color:{foreground};padding:0.75rem 1rem;"
                f"border-radius:0.5rem;border-left:5px solid {foreground};'>"
                f"<strong>{warning_priority.title()} priority warning:</strong> {warning_text}<br>"
                f"<small>Evidence: {patient_warning.get('warning_evidence', '')}</small></div>",
                unsafe_allow_html=True,
            )
        segmentation_text = str(patient_warning.get("segmentation_warning", ""))
        if segmentation_text.strip().lower() not in {"", "nan", "none"}:
            st.markdown(
                f"<div style='background:#f3e8ff;color:#6b21a8;padding:0.75rem 1rem;"
                f"border-radius:0.5rem;border-left:5px solid #9333ea;'>"
                f"<strong>{segmentation_text}</strong><br>"
                f"<small>Evidence: {patient_warning.get('segmentation_warning_evidence', '')}</small></div>",
                unsafe_allow_html=True,
            )

    findings = []
    for _, row in selected.iterrows():
        diagnosis_text = row.get("rca_diagnoses")
        if pd.isna(diagnosis_text) or not str(diagnosis_text).strip():
            diagnosis_text = row.get("rca_label", "")
        labels = str(diagnosis_text).split(" | ")
        explanations = [item.strip() for item in str(row.get("rca_explanation", "")).splitlines() if item.strip()]
        recommendations = [item.strip() for item in str(row.get("rca_recommendations", "")).split(" | ") if item.strip()]
        for index, diagnosis in enumerate(labels):
            if diagnosis and diagnosis != "nan":
                findings.append({"Schema": row.get("rca_schema"), "Series": row.get("series_folder"), "Finding": FINDING_LABELS.get(diagnosis, diagnosis), "Explanation": explanations[index] if index < len(explanations) else row.get("rca_explanation", ""), "Recommendations": recommendations[index] if index < len(recommendations) else row.get("rca_recommendations", "")})
    for _, row in quality.iterrows():
        findings.extend(image_quality_findings(row.to_dict()))

    metric_columns = st.columns(3)
    metric_columns[0].metric("Series", analyzed_series.series_folder.nunique())
    metric_columns[1].metric("Findings", len(findings))
    metric_columns[2].metric("Schemas", selected.rca_schema.nunique() if not selected.empty else 0)

    st.subheader("Findings")
    if findings:
        st.dataframe(pd.DataFrame(findings), hide_index=True, width="stretch")
    else:
        st.success("No findings recorded for this selection.")

    st.subheader("Plain-language recommendation")
    source_rows = analyzed_series
    source = {"ct_id": patient_id, "series": source_rows.to_dict("records")}
    if not warning_rows.empty:
        source["patient_warning"] = warning_rows.iloc[0].to_dict()
    exam_findings = rca[rca.ct_id.astype(str).eq(patient_id)].to_dict("records")
    exam_quality = data["image_quality"][data["image_quality"].ct_id.astype(str).eq(patient_id)].to_dict("records")
    injector_rows = data["injector_data"][data["injector_data"].ct_id.astype(str).eq(patient_id)]
    if not injector_rows.empty:
        source["injector_data"] = injector_rows.iloc[0].to_dict()
    exam_findings.extend(exam_quality)
    notes = selected.get("rca_notes", pd.Series(dtype=str)).fillna("")
    notes = notes[notes.str.strip().ne("")].map(
        lambda note: "; ".join(part.strip() for part in re.split(r"[|;]", str(note)) if part.strip())
    ).drop_duplicates()
    source["notes"] = notes.tolist()
    if st.button("Generate recommendation", type="primary"):
        try:
            text, source_name = generate_recommendation(source, findings, exam_findings, model=DEFAULT_MODEL)
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            input_json = json.dumps({"findings": findings, "source": source}, default=str)
            st.session_state["recommendation"] = (text, source_name, input_json)
            with sqlite3.connect(DB_PATH) as db:
                db.execute(
                    "INSERT OR REPLACE INTO recommendations VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                    (patient_id, None, "exam", DEFAULT_MODEL,
                     source_name, text, input_json),
                )
                db.commit()
    if "recommendation" not in st.session_state:
        with sqlite3.connect(DB_PATH) as db:
            stored = db.execute(
                "SELECT recommendation, source, input_json FROM recommendations "
                "WHERE ct_id = ? AND scope = 'exam' ORDER BY created_at DESC LIMIT 1",
                (patient_id,),
            ).fetchone()
        if stored:
            st.session_state["recommendation"] = (stored[0], stored[1], stored[2])
    if "recommendation" in st.session_state:
        text, source_name, input_json = st.session_state["recommendation"]
        if _stored_recommendation_is_stale(patient_id, input_json, data):
            st.warning("The stored LLM report predates the current missing-weight dose logic. Regenerate recommendations before using this narrative summary.")
        else:
            st.info(f"Source: {source_name}\n\n{text}")

    if not notes.empty:
        st.subheader("Recorded notes")
        for note in notes:
            st.warning(note)

    st.download_button("Download patient RCA data", data=selected.to_csv(index=False), file_name=f"patient_{patient_id}_rca.csv", mime="text/csv")

    st.subheader("Database")
    st.caption(f"SQLite file: {DB_PATH}")
    st.download_button("Download SQLite database", data=DB_PATH.read_bytes(), file_name="ai4quality_recommendations.sqlite", mime="application/vnd.sqlite3")
    with sqlite3.connect(DB_PATH) as db:
        sql_dump = "\n".join(db.iterdump())
    st.download_button("Download SQL dump", data=sql_dump, file_name="ai4quality_recommendations.sql", mime="application/sql")


if __name__ == "__main__":
    main()

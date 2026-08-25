"""Simple visual recommendations dashboard."""
import sqlite3
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from build_database import DB_PATH, build_database
from llm_recommendations import DEFAULT_MODEL, generate_recommendation


def load_data():
    if not DB_PATH.exists():
        build_database()
    with sqlite3.connect(DB_PATH) as db:
        return {name: pd.read_sql_query(f"SELECT * FROM {name}", db) for name in ("exams", "series", "image_quality", "rca", "injector_data")}


def main():
    st.set_page_config(page_title="AI4Quality Recommendations", layout="wide")
    st.title("AI4Quality Recommendations")
    st.caption("What went wrong, why it matters, and what to review in the protocol.")
    if st.sidebar.button("Refresh database"):
        build_database()
        st.rerun()
    data = load_data()
    rca = data["rca"]
    if rca.empty:
        st.warning("No RCA results available. Run the RCA batch analysis first.")
        return

    st.sidebar.header("Case")
    st.sidebar.caption("Recommended local model: qwen2.5:7b")
    patients = sorted(rca.ct_id.dropna().astype(str).unique())
    patient_id = st.sidebar.selectbox("Patient", patients)
    patient = rca[rca.ct_id.astype(str).eq(patient_id)]
    series_options = sorted(patient.series_folder.dropna().astype(str).unique())
    selected_series = st.sidebar.selectbox("Scope", ["Whole exam"] + series_options)
    selected = patient if selected_series == "Whole exam" else patient[patient.series_folder.astype(str).eq(selected_series)]
    quality = data["image_quality"][data["image_quality"].ct_id.astype(str).eq(patient_id)]
    if selected_series != "Whole exam":
        quality = quality[quality.series_folder.astype(str).eq(selected_series)]

    findings = []
    for _, row in selected.iterrows():
        labels = str(row.get("rca_diagnoses", row.get("rca_label", ""))).split(" | ")
        for diagnosis in labels:
            if diagnosis and diagnosis != "nan":
                findings.append({"Schema": row.get("rca_schema"), "Series": row.get("series_folder"), "Finding": diagnosis, "Explanation": row.get("rca_explanation", ""), "Recommendations": row.get("rca_recommendations", "")})
    for _, row in quality.iterrows():
        if str(row.get("status", "")).lower() not in {"optimal", "acceptable_low", "acceptable_high", "nan"}:
            findings.append({"Schema": "image_quality", "Series": row.get("series_folder"), "Finding": f"{row.get('roi_name')} {row.get('status')}", "Explanation": f"{row.get('metric_name')}: evaluated value {row.get('evaluated_value')}", "Recommendations": "Review image-quality measurement and acquisition protocol."})

    metric_columns = st.columns(3)
    metric_columns[0].metric("Series", selected.series_folder.nunique())
    metric_columns[1].metric("Findings", len(findings))
    metric_columns[2].metric("Schemas", selected.rca_schema.nunique())

    st.subheader("Findings")
    if findings:
        st.dataframe(pd.DataFrame(findings), hide_index=True, width="stretch")
    else:
        st.success("No findings recorded for this selection.")

    st.subheader("Plain-language recommendation")
    source_rows = data["series"][data["series"].ct_id.astype(str).eq(patient_id)]
    if selected_series != "Whole exam":
        source_rows = source_rows[source_rows.series_folder.astype(str).eq(selected_series)]
    source = source_rows.iloc[0].to_dict() if not source_rows.empty else {"series_folder": selected_series}
    exam_findings = rca[rca.ct_id.astype(str).eq(patient_id)].to_dict("records")
    exam_quality = data["image_quality"][data["image_quality"].ct_id.astype(str).eq(patient_id)].to_dict("records")
    injector_rows = data["injector_data"][data["injector_data"].ct_id.astype(str).eq(patient_id)]
    if not injector_rows.empty:
        source["injector_data"] = injector_rows.iloc[0].to_dict()
    exam_findings.extend(exam_quality)
    if st.button("Generate recommendation", type="primary"):
        text, source_name = generate_recommendation(source, findings, exam_findings, model=DEFAULT_MODEL)
        st.session_state["recommendation"] = (text, source_name)
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO recommendations VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (patient_id, None if selected_series == "Whole exam" else selected_series,
                 "exam" if selected_series == "Whole exam" else "series", DEFAULT_MODEL,
                 source_name, text, json.dumps({"findings": findings}, default=str)),
            )
            db.commit()
    if "recommendation" in st.session_state:
        text, source_name = st.session_state["recommendation"]
        st.info(f"Source: {source_name}\n\n{text}")

    notes = selected.get("rca_notes", pd.Series(dtype=str)).fillna("")
    notes = notes[notes.str.strip().ne("")].drop_duplicates()
    if not notes.empty:
        st.subheader("Recorded notes")
        for note in notes:
            st.warning(note)

    st.download_button("Download selected RCA data", data=selected.to_csv(index=False), file_name=f"patient_{patient_id}_rca.csv", mime="text/csv")


if __name__ == "__main__":
    main()

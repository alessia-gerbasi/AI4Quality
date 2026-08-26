"""Build the consolidated AI4Quality recommendation database."""
import json
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RCA = ROOT / "_03_RootCauseAnalysis"
DB_PATH = Path(__file__).resolve().parent / "data" / "ai4quality_recommendations.sqlite"


def clean(value):
    return None if pd.isna(value) else value


def build_database(output_path: Path = DB_PATH) -> Path:
    qc = pd.read_csv(ROOT / "_02_QualityCheck/OUTPUTS/roi_hu_qc_results.csv")
    rca = pd.read_csv(RCA / "rca_results_all.csv") if (RCA / "rca_results_all.csv").exists() else pd.DataFrame()
    patient_warnings = pd.read_csv(ROOT / "_02_QualityCheck/OUTPUTS/patient_hu_qc_summary.csv") if (ROOT / "_02_QualityCheck/OUTPUTS/patient_hu_qc_summary.csv").exists() else pd.DataFrame()
    injection = pd.read_excel(ROOT.parent / "DATA/CDI_NEXO_072026/0_files/Injection History Anonymized.xlsx")
    link = pd.read_excel(ROOT.parent / "DATA/CDI_NEXO_072026/0_files/link_anonymization.xlsx")
    series = pd.read_csv(ROOT / "_00_Preprocessing/OUTPUTS/retained_series_unified_filtered.csv")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_path) as db:
        db.executescript("""
        DROP TABLE IF EXISTS exams;
        DROP TABLE IF EXISTS series;
        DROP TABLE IF EXISTS image_quality;
        DROP TABLE IF EXISTS rca;
        DROP TABLE IF EXISTS injector_data;
        DROP TABLE IF EXISTS patient_warnings;
        CREATE TABLE exams (ct_id TEXT PRIMARY KEY, ct_folder TEXT, patient_name TEXT, injection_index TEXT, patient_data_json TEXT);
        CREATE TABLE series (ct_id TEXT, series_folder TEXT, phase_name TEXT, procedure_code TEXT, scanner TEXT, series_data_json TEXT, PRIMARY KEY (ct_id, series_folder));
        CREATE TABLE image_quality (ct_id TEXT, series_folder TEXT, roi_name TEXT, metric_name TEXT, status TEXT, evaluated_value REAL, mean_hu REAL, mean_hu_precontrast REAL, qc_data_json TEXT);
        CREATE TABLE rca (ct_id TEXT, series_folder TEXT, rca_schema TEXT, rca_label TEXT, rca_diagnoses TEXT, rca_explanation TEXT, rca_notes TEXT, rca_recommendations TEXT, rca_data_json TEXT);
        CREATE TABLE injector_data (ct_id TEXT, injection_index TEXT, data_json TEXT);
        CREATE TABLE patient_warnings (ct_id TEXT PRIMARY KEY, warning_priority TEXT, warning TEXT, warning_evidence TEXT, segmentation_warning TEXT, segmentation_warning_evidence TEXT, warning_data_json TEXT);
        CREATE TABLE IF NOT EXISTS recommendations (ct_id TEXT, series_folder TEXT, scope TEXT, model TEXT, source TEXT, recommendation TEXT, input_json TEXT, created_at TEXT);
        CREATE INDEX IF NOT EXISTS idx_series_ct ON series (ct_id);
        CREATE INDEX IF NOT EXISTS idx_quality_ct_series ON image_quality (ct_id, series_folder);
        CREATE INDEX IF NOT EXISTS idx_rca_ct_series ON rca (ct_id, series_folder);
        CREATE INDEX IF NOT EXISTS idx_injector_ct ON injector_data (ct_id);
        CREATE INDEX IF NOT EXISTS idx_recommendations_ct ON recommendations (ct_id, scope, model, created_at);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_recommendations_current ON recommendations (ct_id, scope, model);
        """)

        link_by_index = {str(clean(row.get("index"))): str(clean(row.get("ID"))).replace("CT_QUALITY_", "") for _, row in link.iterrows() if clean(row.get("index")) is not None}
        for _, row in injection.iterrows():
            idx = clean(row.get("index"))
            patient_id = str(idx) if idx is not None else None
            ct_id = link_by_index.get(patient_id)
            if ct_id is None:
                continue
            data_json = json.dumps({k: clean(v) for k, v in row.to_dict().items()}, default=str)
            db.execute("INSERT OR REPLACE INTO exams VALUES (?, ?, ?, ?, ?)", (ct_id, f"CT_QUALITY_{ct_id}" if ct_id else None, clean(row.get("Patient (Surname, Name)")), patient_id, data_json))
            db.execute("INSERT INTO injector_data VALUES (?, ?, ?)", (ct_id, patient_id, data_json))

        for _, row in series.iterrows():
            db.execute("INSERT OR REPLACE INTO series VALUES (?, ?, ?, ?, ?, ?)", (str(row.get("ct_id")), clean(row.get("series_folder")), clean(row.get("phase_name")), clean(row.get("procedure_code_value")), clean(row.get("scanner")), json.dumps({k: clean(v) for k, v in row.to_dict().items()}, default=str)))
        for _, row in qc.iterrows():
            db.execute("INSERT INTO image_quality VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(row.get("ct_id")), clean(row.get("series_folder")), clean(row.get("roi_name")), clean(row.get("metric_name")), clean(row.get("status")), clean(row.get("evaluated_value")), clean(row.get("mean_hu")), clean(row.get("mean_hu_precontrast")), json.dumps({k: clean(v) for k, v in row.to_dict().items()}, default=str)))
        for _, row in rca.iterrows():
            db.execute("INSERT INTO rca VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(row.get("ct_id")), clean(row.get("series_folder")), clean(row.get("rca_schema")), clean(row.get("rca_label")), clean(row.get("rca_diagnoses")), clean(row.get("rca_explanation")), clean(row.get("rca_notes")), clean(row.get("rca_recommendations")), json.dumps({k: clean(v) for k, v in row.to_dict().items()}, default=str)))
        for _, row in patient_warnings.iterrows():
            ct_id = str(row.get("ct_id"))
            db.execute(
                "INSERT OR REPLACE INTO patient_warnings VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ct_id, clean(row.get("warning_priority", "none")), clean(row.get("warning", "")), clean(row.get("warning_evidence", "")), clean(row.get("segmentation_warning", "")), clean(row.get("segmentation_warning_evidence", "")), json.dumps({k: clean(v) for k, v in row.to_dict().items()}, default=str)),
            )
        db.commit()
    return output_path


if __name__ == "__main__":
    print(build_database())

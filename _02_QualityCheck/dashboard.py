#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _dependency_error_message(missing_module: str) -> str:
    python_ctq = "/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python"
    return (
        f"Missing Python module '{missing_module}'.\n\n"
        f"Run the dashboard with the ctq environment, for example:\n"
        f"  {python_ctq} -m streamlit run _02_QualityCheck/dashboard.py\n"
    )


try:
    import pandas as pd
    import streamlit as st
    import yaml

    from _02_QualityCheck.reporting import (
        build_aggregate_stats_dataframe,
        build_markdown_report,
        build_patient_summary_dataframe,
    )
    from _02_QualityCheck.visualization import STATUS_COLORS
except ModuleNotFoundError as exc:
    print(_dependency_error_message(exc.name or "unknown"), file=sys.stderr)
    raise SystemExit(1) from exc


RESULTS_FOLDER_GLOB = "OUTPUTS*"
PREPROCESSING_CSV_PATH = _REPO_ROOT / "_00_Preprocessing" / "OUTPUTS" / "retained_series_unified_filtered.csv"
PROTOCOLS_CONFIG_PATH = _REPO_ROOT / "config" / "common" / "ct_protocols.yaml"


def _resolve_path(path_str: str | None) -> Path | None:
    if not path_str or str(path_str).strip() == "":
        return None
    path = Path(path_str)
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    return path


def _discover_output_dirs() -> list[Path]:
    candidates: list[Path] = []
    for path in sorted(_SCRIPT_DIR.glob(RESULTS_FOLDER_GLOB)):
        if not path.is_dir():
            continue
        if (path / "roi_hu_qc_results.csv").exists() and (path / "roi_hu_qc_summary.csv").exists():
            candidates.append(path)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def _load_ct_type_lookup() -> pd.DataFrame:
    if not PREPROCESSING_CSV_PATH.exists():
        return pd.DataFrame(columns=["ct_id", "series_folder", "CT_type"])

    df = pd.read_csv(PREPROCESSING_CSV_PATH)
    columns = ["ct_id", "series_folder", "CT_type"]
    missing = [column for column in columns if column not in df.columns]
    if missing:
        return pd.DataFrame(columns=columns)

    lookup = df[columns].copy()
    lookup["CT_type"] = lookup["CT_type"].fillna("").astype(str)
    lookup = lookup.drop_duplicates(subset=["ct_id", "series_folder"], keep="first")
    return lookup


def _load_procedure_description_lookup() -> dict[str, str]:
    if not PROTOCOLS_CONFIG_PATH.exists():
        return {}

    with PROTOCOLS_CONFIG_PATH.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream) or {}

    procedures = config.get("procedures", {})
    if not isinstance(procedures, dict):
        return {}

    lookup: dict[str, str] = {}
    for code, item in procedures.items():
        if not isinstance(item, dict):
            continue
        description = str(item.get("description", "") or "").strip()
        code_str = str(code or "").strip()
        if code_str:
            lookup[code_str] = description
    return lookup


def _ensure_procedure_description_columns(detail_df: pd.DataFrame, series_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = _load_procedure_description_lookup()
    detail_df = detail_df.copy()
    series_df = series_df.copy()

    for dataframe in (detail_df, series_df):
        if "procedure_description" not in dataframe.columns:
            if "procedure_code" in dataframe.columns:
                dataframe["procedure_description"] = dataframe["procedure_code"].map(lookup).fillna("")
            else:
                dataframe["procedure_description"] = ""
        else:
            dataframe["procedure_description"] = dataframe["procedure_description"].fillna("").astype(str)

        dataframe["procedure_description"] = dataframe["procedure_description"].fillna("").astype(str)

    return detail_df, series_df


def _normalize_phase_name(phase_name: object) -> str:
    if pd.isna(phase_name):
        return ""
    return str(phase_name).strip().lower().replace(" ", "_")


def _phase_prediction_matches(actual_phase: str, predicted_phase: str) -> bool:
    if not actual_phase or not predicted_phase:
        return False
    if actual_phase == predicted_phase:
        return True
    if actual_phase == "venosa" and "venous" in predicted_phase:
        return True
    if actual_phase == "arteriosa" and "arterial" in predicted_phase:
        return True
    return False


def _load_phase_prediction(series_dir_str: object) -> dict[str, object]:
    phase_json_path = _resolve_path(str(series_dir_str)) if pd.notna(series_dir_str) else None
    if phase_json_path is None:
        return {}

    phase_json_path = phase_json_path / "phase.json"
    if not phase_json_path.exists():
        return {}

    try:
        with phase_json_path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}
    return data


def _build_phase_prediction_columns(series_df: pd.DataFrame) -> pd.DataFrame:
    if series_df.empty:
        series_df = series_df.copy()
        series_df["predicted_phase"] = ""
        series_df["predicted_phase_probability"] = pd.NA
        series_df["phase_prediction_matches"] = pd.NA
        return series_df

    series_df = series_df.copy()
    predictions = series_df.get("series_dir", pd.Series(index=series_df.index, dtype=object)).apply(_load_phase_prediction)
    series_df["predicted_phase"] = predictions.apply(lambda value: str(value.get("phase", "") or ""))
    series_df["predicted_phase_probability"] = pd.to_numeric(
        predictions.apply(lambda value: value.get("probability") if value else pd.NA),
        errors="coerce",
    )

    actual_phase = series_df.get("phase_name", pd.Series(index=series_df.index, dtype=object)).apply(_normalize_phase_name)
    predicted_phase = series_df["predicted_phase"].apply(_normalize_phase_name)
    has_prediction = predicted_phase != ""
    series_df["phase_prediction_matches"] = pd.Series(pd.NA, index=series_df.index, dtype=object)
    series_df.loc[has_prediction, "phase_prediction_matches"] = [
        _phase_prediction_matches(actual, predicted)
        for actual, predicted in zip(actual_phase[has_prediction], predicted_phase[has_prediction], strict=False)
    ]
    return series_df


def _ensure_ct_type_columns(detail_df: pd.DataFrame, series_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = _load_ct_type_lookup()
    if lookup.empty:
        detail_df = detail_df.copy()
        series_df = series_df.copy()
        if "CT_type" not in detail_df.columns:
            detail_df["CT_type"] = ""
        if "CT_type" not in series_df.columns:
            series_df["CT_type"] = ""
        return detail_df, series_df

    detail_df = detail_df.copy()
    series_df = series_df.copy()

    if "CT_type" not in detail_df.columns:
        detail_df = detail_df.merge(lookup, on=["ct_id", "series_folder"], how="left")
    else:
        detail_df["CT_type"] = detail_df["CT_type"].fillna("").astype(str)

    if "CT_type" not in series_df.columns:
        series_df = series_df.merge(lookup, on=["ct_id", "series_folder"], how="left")
    else:
        series_df["CT_type"] = series_df["CT_type"].fillna("").astype(str)

    detail_df["CT_type"] = detail_df["CT_type"].fillna("").astype(str)
    series_df["CT_type"] = series_df["CT_type"].fillna("").astype(str)
    return detail_df, series_df


@st.cache_data(show_spinner=False)
def load_results(output_dir_str: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output_dir = _resolve_path(output_dir_str)
    if output_dir is None or not output_dir.exists():
        raise FileNotFoundError(f"Results folder not found: {output_dir_str}")

    detail_path = output_dir / "roi_hu_qc_results.csv"
    series_path = output_dir / "roi_hu_qc_summary.csv"
    patient_path = output_dir / "patient_hu_qc_summary.csv"
    aggregate_path = output_dir / "aggregate_hu_qc_stats.csv"

    if not detail_path.exists() or not series_path.exists():
        raise FileNotFoundError("Expected roi_hu_qc_results.csv and roi_hu_qc_summary.csv in the selected folder")

    detail_df = pd.read_csv(detail_path)
    series_df = pd.read_csv(series_path)
    detail_df, series_df = _ensure_ct_type_columns(detail_df, series_df)
    detail_df, series_df = _ensure_procedure_description_columns(detail_df, series_df)
    series_df = _build_phase_prediction_columns(series_df)

    if "output_image_path" in detail_df.columns:
        detail_df["output_image_abs"] = detail_df["output_image_path"].apply(lambda v: str(_resolve_path(v)) if pd.notna(v) else "")
    else:
        detail_df["output_image_abs"] = ""

    if "image_path" in series_df.columns:
        series_df["image_abs"] = series_df["image_path"].apply(lambda v: str(_resolve_path(v)) if pd.notna(v) else "")
    else:
        series_df["image_abs"] = ""

    if patient_path.exists():
        patient_df = pd.read_csv(patient_path)
    else:
        patient_df = build_patient_summary_dataframe(detail_df, series_df)

    if aggregate_path.exists():
        aggregate_df = pd.read_csv(aggregate_path)
    else:
        aggregate_df = build_aggregate_stats_dataframe(detail_df, series_df, patient_df)

    return detail_df, series_df, patient_df, aggregate_df


def _status_color(status: str) -> str:
    return STATUS_COLORS.get(status, "#6c757d")


def _format_float(value: object) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value):.1f}"


def _metric_card(row: pd.Series) -> str:
    status = str(row.get("status", "missing"))
    color = _status_color(status)
    value_label = _format_float(row.get("evaluated_value"))
    mean_label = f"{_format_float(row.get('mean_hu'))} +/- {_format_float(row.get('std_hu'))}"
    median_label = f"{_format_float(row.get('median_hu'))} +/- {_format_float(row.get('median_std_hu'))}"
    baseline_label = ""
    if pd.notna(row.get("mean_hu_precontrast")):
        baseline_label = (
            f"<div><strong>Precontrast mean:</strong> {_format_float(row.get('mean_hu_precontrast'))} "
            f"+/- {_format_float(row.get('std_hu_precontrast'))}</div>"
        )
    delta_label = ""
    if pd.notna(row.get("delta_hu")):
        delta_label = f"<div><strong>Delta mean:</strong> {_format_float(row.get('delta_hu'))}</div>"
    threshold_label = ""
    if pd.notna(row.get("threshold_min_opt")):
        threshold_label = (
            f"<div><strong>Optimal:</strong> {_format_float(row.get('threshold_min_opt'))} to {_format_float(row.get('threshold_max_opt'))}</div>"
            f"<div><strong>Tolerance:</strong> {_format_float(row.get('threshold_min_with_threshold'))} to {_format_float(row.get('threshold_max_with_threshold'))}</div>"
        )

    warning = row.get("warning")
    warning_html = ""
    if isinstance(warning, str) and warning.strip():
        warning_html = f"<div style='margin-top:0.4rem;color:#7f1d1d;'><strong>Warning:</strong> {warning}</div>"

    attenuation_html = ""
    attenuation_message = row.get("attenuation_message")
    if isinstance(attenuation_message, str) and attenuation_message.strip():
        incoherent = str(row.get("attenuation_consistency", "")) == "incoherent"
        attenuation_color = "#b91c1c" if incoherent else "#0369a1"
        edge_slice_count = row.get("edge_slice_count")
        slice_label = f"first/last {int(edge_slice_count)} vessel slices" if pd.notna(edge_slice_count) else "vessel endpoints"
        attenuation_html = (
            f"<div style='margin-top:0.75rem;padding:0.65rem 0.75rem;border-left:4px solid {attenuation_color};"
            f"background:{attenuation_color}0d;color:#1e293b;'><strong>Attenuation consistency "
            f"({slice_label}):</strong><br>{attenuation_message}</div>"
        )

    return f"""
    <div style="background:{color}14;border-left:6px solid {color};padding:0.9rem 1rem;border-radius:0.6rem;margin-bottom:0.75rem;">
      <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
        <div>
          <div style="font-size:1.05rem;font-weight:700;">{row['roi_name']}</div>
          <div style="font-size:0.92rem;color:#334155;">{row.get('metric_name', '')}</div>
        </div>
        <div style="background:{color};color:white;padding:0.2rem 0.55rem;border-radius:999px;font-size:0.82rem;">{row.get('status_label', status)}</div>
      </div>
      <div style="margin-top:0.7rem;font-size:1.35rem;font-weight:700;color:{color};">{value_label}</div>
      <div style="margin-top:0.45rem;"><strong>Mean HU:</strong> {mean_label}</div>
      <div><strong>Median HU:</strong> {median_label}</div>
      {baseline_label}
      {delta_label}
      {threshold_label}
    {attenuation_html}
      {warning_html}
    </div>
    """


def _download_bytes(path_str: str | None) -> bytes | None:
    path = _resolve_path(path_str)
    if path is None or not path.exists():
        return None
    return path.read_bytes()


def _format_percentage(value: object) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value) * 100.0:.1f}%"


def _render_series_metadata(row: pd.Series) -> None:
    procedure_code = str(row.get("procedure_code", "") or "")
    procedure_description = str(row.get("procedure_description", "") or "")
    actual_phase = str(row.get("phase_name", "") or "")
    predicted_phase = str(row.get("predicted_phase", "") or "")
    prediction_probability = _format_percentage(row.get("predicted_phase_probability")) if predicted_phase else "n/a"
    prediction_matches = row.get("phase_prediction_matches")

    phase_badge = ""
    if pd.notna(prediction_matches):
        if bool(prediction_matches):
            phase_badge = "<span style='display:inline-block;margin-left:0.45rem;padding:0.1rem 0.45rem;border-radius:999px;background:#dcfce7;color:#166534;font-size:0.8rem;font-weight:700;'>Match</span>"
        else:
            phase_badge = "<span style='display:inline-block;margin-left:0.45rem;padding:0.1rem 0.45rem;border-radius:999px;background:#fee2e2;color:#991b1b;font-size:0.8rem;font-weight:700;'>Mismatch</span>"

    predicted_phase_html = "<span style='color:#64748b;'>No phase prediction found</span>"
    if predicted_phase:
        predicted_color = "#166534" if bool(prediction_matches) else "#991b1b"
        predicted_phase_html = (
            f"<span style='font-weight:700;color:{predicted_color};'>{predicted_phase}</span>"
            f" <span style='color:#475569;'>({prediction_probability})</span>{phase_badge}"
        )

    procedure_html = procedure_code or "n/a"
    if procedure_description:
        procedure_html = f"<span style='font-weight:700;'>{procedure_code}</span> <span style='color:#475569;'>- {procedure_description}</span>"

    st.markdown(
        f"""
        <div style="margin:0.25rem 0 1rem 0;padding:0.9rem 1rem;border:1px solid #e2e8f0;border-radius:0.6rem;background:#f8fafc;">
          <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.75rem 1.5rem;">
            <div><strong>Procedure:</strong> {procedure_html}</div>
            <div><strong>Actual phase:</strong> {actual_phase or 'n/a'}</div>
            <div><strong>Series folder:</strong> <span style="color:#475569;">{row.get('series_folder', '')}</span></div>
            <div><strong>Predicted phase:</strong> {predicted_phase_html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="AI4Quality HU Dashboard", layout="wide")
    st.title("AI4Quality HU Quality Dashboard")
    st.caption("Review per-series HU measurements, warnings, images, and cohort summaries.")

    discovered_dirs = _discover_output_dirs()
    default_output_dir = discovered_dirs[0] if discovered_dirs else _SCRIPT_DIR / "OUTPUTS"
    output_dir_options = [str(path) for path in discovered_dirs]
    if str(default_output_dir) not in output_dir_options:
        output_dir_options = [str(default_output_dir)] + output_dir_options

    with st.sidebar:
        st.header("Data Source")
        if output_dir_options:
            output_dir_input = st.selectbox("Results folder", output_dir_options, index=0)
        else:
            output_dir_input = st.text_input("Results folder", value=str(default_output_dir))
        st.caption("The dashboard auto-detects valid HU output folders in _02_QualityCheck/.")
        if st.button("Reload data", width="stretch"):
            st.cache_data.clear()

    try:
        detail_df, series_df, patient_df, aggregate_df = load_results(output_dir_input)
    except Exception as exc:
        st.error(str(exc))
        st.info("Run the HU pipeline first, for example: python _02_QualityCheck/main.py --output-dir _02_QualityCheck/OUTPUTS")
        return

    st.sidebar.header("Filters")
    ct_types = sorted(detail_df["CT_type"].dropna().astype(str).unique().tolist())
    procedures = sorted(detail_df["procedure_code"].dropna().astype(str).unique().tolist())
    phases = sorted(detail_df["phase_name"].dropna().astype(str).unique().tolist())
    statuses = sorted(detail_df["status"].dropna().astype(str).unique().tolist())
    metrics = sorted(detail_df["metric_name"].dropna().astype(str).unique().tolist())

    selected_ct_types = st.sidebar.multiselect("CT Type", ct_types, default=ct_types)
    selected_procedures = st.sidebar.multiselect("Procedure code", procedures, default=procedures)
    selected_phases = st.sidebar.multiselect("Phase", phases, default=phases)
    selected_statuses = st.sidebar.multiselect("Status", statuses, default=statuses)
    selected_metrics = st.sidebar.multiselect("Metric", metrics, default=metrics)
    warning_priority_labels = {
        "none": "No warning",
        "low": "Low priority warning",
        "medium": "Medium priority warning",
        "high": "High priority warning",
    }
    segmentation_warning_label = "Segmentation warning"
    selected_warning_labels = st.sidebar.multiselect(
        "Patient warning",
        [*warning_priority_labels.values(), segmentation_warning_label],
        default=[*warning_priority_labels.values(), segmentation_warning_label],
    )
    selected_warning_priorities = [
        priority for priority, label in warning_priority_labels.items()
        if label in selected_warning_labels
    ]
    only_warning_series = st.sidebar.checkbox("Only series with warnings", value=False)

    filtered_detail = detail_df[
        detail_df["CT_type"].isin(selected_ct_types)
        & detail_df["procedure_code"].isin(selected_procedures)
        & detail_df["phase_name"].isin(selected_phases)
        & detail_df["status"].isin(selected_statuses)
        & detail_df["metric_name"].isin(selected_metrics)
    ].copy()

    if "warning_priority" in patient_df.columns:
        patient_warning_mask = patient_df["warning_priority"].fillna("none").isin(selected_warning_priorities)
        if segmentation_warning_label in selected_warning_labels and "segmentation_warning" in patient_df.columns:
            segmentation_mask = patient_df["segmentation_warning"].fillna("").astype(str).str.strip().ne("")
            patient_warning_mask |= segmentation_mask
        warning_patient_ids = patient_df.loc[patient_warning_mask, "ct_id"].unique()
        filtered_detail = filtered_detail[filtered_detail["ct_id"].isin(warning_patient_ids)]

    if only_warning_series and not series_df.empty:
        warning_keys = series_df[series_df["n_warnings"] > 0][["ct_id", "series_folder"]].drop_duplicates()
        filtered_detail = filtered_detail.merge(warning_keys, on=["ct_id", "series_folder"], how="inner")

    filtered_series = series_df[
        series_df["ct_id"].isin(filtered_detail["ct_id"].unique())
        & series_df["series_folder"].isin(filtered_detail["series_folder"].unique())
    ].copy()
    filtered_patient = build_patient_summary_dataframe(filtered_detail, filtered_series)
    filtered_aggregate = build_aggregate_stats_dataframe(filtered_detail, filtered_series, filtered_patient)

    top = filtered_aggregate[filtered_aggregate["dimension"] == "overall"]
    top_row = top.iloc[0] if not top.empty else pd.Series(dtype=object)
    metric_cols = st.columns(5)
    metric_cols[0].metric("Patients", int(top_row.get("n_patients", len(filtered_patient)) or 0))
    metric_cols[1].metric("Series", int(top_row.get("n_series", len(filtered_series)) or 0))
    metric_cols[2].metric("ROI Evaluations", int(top_row.get("n_rois", len(filtered_detail)) or 0))
    metric_cols[3].metric("Warning Series", int(top_row.get("n_warning_series", 0) or 0))
    metric_cols[4].metric("Critical ROIs", int(top_row.get("n_critical_rois", 0) or 0))

    if filtered_patient.empty:
        st.warning("No patients match the current filters.")
        return

    patient_options = filtered_patient.sort_values(["ct_id"])[["ct_id", "ct_name"]].drop_duplicates().to_dict("records")
    option_labels = [f"CT {int(item['ct_id'])} | {item['ct_name']}" for item in patient_options]

    if "patient_idx" not in st.session_state:
        st.session_state.patient_idx = 0
    st.session_state.patient_idx = max(0, min(st.session_state.patient_idx, len(option_labels) - 1))

    nav_cols = st.columns([1, 3, 1])
    if nav_cols[0].button("Previous patient", width="stretch", disabled=st.session_state.patient_idx == 0):
        st.session_state.patient_idx -= 1
    selected_label = nav_cols[1].selectbox("Patient", option_labels, index=st.session_state.patient_idx)
    st.session_state.patient_idx = option_labels.index(selected_label)
    if nav_cols[2].button("Next patient", width="stretch", disabled=st.session_state.patient_idx >= len(option_labels) - 1):
        st.session_state.patient_idx += 1

    selected_patient = patient_options[st.session_state.patient_idx]
    ct_id = int(selected_patient["ct_id"])
    patient_series = filtered_series[filtered_series["ct_id"] == ct_id].copy().sort_values(["phase_name", "series_folder"])
    patient_detail = filtered_detail[filtered_detail["ct_id"] == ct_id].copy().sort_values(["phase_name", "series_folder", "roi_name"])
    patient_summary_row = filtered_patient[filtered_patient["ct_id"] == ct_id].iloc[0]

    st.subheader(f"Patient CT {ct_id} | {selected_patient['ct_name']}")
    patient_cols = st.columns(4)
    patient_cols[0].metric("Patient series", int(patient_summary_row["n_series"]))
    patient_cols[1].metric("Warning series", int(patient_summary_row["n_warning_series"]))
    patient_cols[2].metric("Critical ROIs", int(patient_summary_row["n_critical_rois"]))
    patient_cols[3].metric("Missing ROIs", int(patient_summary_row["n_missing_rois"]))
    patient_warning_priority = str(patient_summary_row.get("warning_priority", "none"))
    patient_warning = str(patient_summary_row.get("warning", ""))
    if patient_warning_priority != "none" and patient_warning:
        warning_colors = {
            "low": ("#fff7cc", "#a16207"),
            "medium": ("#ffedd5", "#c2410c"),
            "high": ("#fee2e2", "#b91c1c"),
        }
        background, foreground = warning_colors.get(patient_warning_priority, ("#fef3c7", "#92400e"))
        st.markdown(
            f"<div style='background:{background};color:{foreground};padding:0.75rem 1rem;"
            f"border-radius:0.5rem;border-left:5px solid {foreground};'>"
            f"<strong>{patient_warning_priority.title()} priority:</strong> {patient_warning}</div>",
            unsafe_allow_html=True,
        )
    segmentation_warning = str(patient_summary_row.get("segmentation_warning", ""))
    if segmentation_warning and segmentation_warning.lower() != "nan":
        segmentation_evidence = str(patient_summary_row.get("segmentation_warning_evidence", ""))
        st.markdown(
            f"<div style='background:#f3e8ff;color:#6b21a8;padding:0.75rem 1rem;"
            f"border-radius:0.5rem;border-left:5px solid #9333ea;'>"
            f"<strong>{segmentation_warning}</strong> {segmentation_evidence}</div>",
            unsafe_allow_html=True,
        )

    series_labels = [
        f"{row.phase_name} | {row.metric_name} | {row.series_folder}"
        for row in patient_series.itertuples(index=False)
    ]
    selected_series_label = st.selectbox("Series", series_labels)
    selected_series_row = patient_series.iloc[series_labels.index(selected_series_label)]

    selected_detail = patient_detail[
        (patient_detail["series_folder"] == selected_series_row["series_folder"])
        & (patient_detail["metric_name"] == selected_series_row["metric_name"])
    ].copy()

    viewer_col, roi_col = st.columns([1.15, 1.0])
    with viewer_col:
        st.markdown("### Image Review")
        _render_series_metadata(selected_series_row)
        image_path = selected_series_row.get("image_abs", "")
        if isinstance(image_path, str) and image_path and Path(image_path).exists():
            st.image(image_path, caption=selected_series_label)
        else:
            st.info("QC image not available for this series.")

        warnings_text = selected_series_row.get("warnings", "")
        if isinstance(warnings_text, str) and warnings_text.strip():
            st.error(warnings_text)
        else:
            st.success("No warnings for this series.")

        image_bytes = _download_bytes(selected_series_row.get("image_path"))
        if image_bytes is not None:
            st.download_button(
                "Download image",
                data=image_bytes,
                file_name=Path(str(selected_series_row.get("image_path"))).name,
                mime="image/png",
                width="stretch",
            )

    with roi_col:
        st.markdown("### ROI Indicators")
        for _, row in selected_detail.iterrows():
            st.markdown(_metric_card(row), unsafe_allow_html=True)

    tabs = st.tabs(["Series Table", "Patient Table", "Aggregate Stats", "Downloads"])

    with tabs[0]:
        display_cols = [
            "roi_name",
            "status_label",
            "evaluated_value",
            "mean_hu",
            "std_hu",
            "median_hu",
            "mean_hu_precontrast",
            "std_hu_precontrast",
            "delta_hu",
            "voxel_count",
            "warning",
        ]
        st.dataframe(selected_detail[display_cols], use_container_width=True, hide_index=True)

    with tabs[1]:
        st.dataframe(filtered_patient.sort_values(["ct_id"]), use_container_width=True, hide_index=True)
        status_counts = filtered_detail["status"].value_counts().sort_index()
        if not status_counts.empty:
            st.bar_chart(status_counts)

    with tabs[2]:
        st.dataframe(filtered_aggregate, use_container_width=True, hide_index=True)
        phase_stats = filtered_aggregate[filtered_aggregate["dimension"] == "phase_name"]
        if not phase_stats.empty:
            st.bar_chart(phase_stats.set_index("group_value")["n_rois"])

    with tabs[3]:
        report_md = build_markdown_report(
            filtered_detail,
            filtered_series,
            filtered_patient,
            filtered_aggregate,
            title="AI4Quality HU QC Report",
        )
        st.download_button(
            "Download filtered ROI CSV",
            data=filtered_detail.to_csv(index=False).encode("utf-8"),
            file_name="filtered_roi_hu_qc_results.csv",
            mime="text/csv",
            width="stretch",
        )
        st.download_button(
            "Download filtered series CSV",
            data=filtered_series.to_csv(index=False).encode("utf-8"),
            file_name="filtered_roi_hu_qc_summary.csv",
            mime="text/csv",
            width="stretch",
        )
        st.download_button(
            "Download filtered aggregate CSV",
            data=filtered_aggregate.to_csv(index=False).encode("utf-8"),
            file_name="filtered_aggregate_hu_qc_stats.csv",
            mime="text/csv",
            width="stretch",
        )
        st.download_button(
            "Download markdown report",
            data=report_md.encode("utf-8"),
            file_name="hu_qc_report.md",
            mime="text/markdown",
            width="stretch",
        )


if __name__ == "__main__":
    main()

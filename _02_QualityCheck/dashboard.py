#!/usr/bin/env python3
from __future__ import annotations

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
      {warning_html}
    </div>
    """


def _download_bytes(path_str: str | None) -> bytes | None:
    path = _resolve_path(path_str)
    if path is None or not path.exists():
        return None
    return path.read_bytes()


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
    only_warning_series = st.sidebar.checkbox("Only series with warnings", value=False)

    filtered_detail = detail_df[
        detail_df["CT_type"].isin(selected_ct_types)
        & detail_df["procedure_code"].isin(selected_procedures)
        & detail_df["phase_name"].isin(selected_phases)
        & detail_df["status"].isin(selected_statuses)
        & detail_df["metric_name"].isin(selected_metrics)
    ].copy()

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

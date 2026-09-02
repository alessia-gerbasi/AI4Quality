from __future__ import annotations

from typing import Iterable

import pandas as pd

from .models import SeriesEvaluation


CRITICAL_STATUSES = {"critical_low", "critical_high"}
PARALLEL_REFERENCE_GROUPS = (
    {"liver", "spleen"},
    {"common_carotid_artery_left", "common_carotid_artery_right"},
    {"kidney_left", "kidney_right"},
)


def _direction_phrase(statuses: Iterable[str]) -> str:
    statuses = set(statuses)
    has_low = "critical_low" in statuses
    has_high = "critical_high" in statuses
    if has_low and not has_high:
        return "insufficient"
    if has_high and not has_low:
        return "excessive"
    return "insufficient or excessive"


def _patient_warning(detail_df: pd.DataFrame, patient_id: object) -> tuple[str, str, str]:
    rows = detail_df[detail_df["ct_id"].eq(patient_id)].copy()
    if rows.empty:
        return "none", "", ""

    reference_rows = rows[rows["roi_name"].isin(set().union(*PARALLEL_REFERENCE_GROUPS) | {"aorta"})]

    venous_reference = reference_rows[
        reference_rows["phase_name"].fillna("").astype(str).str.lower().eq("venosa")
        & reference_rows["status"].isin(CRITICAL_STATUSES)
    ]
    if not venous_reference.empty:
        evidence = "; ".join(
            f"{row.roi_name} {row.status} in {row.series_folder}"
            for row in venous_reference.itertuples()
        )
        direction = _direction_phrase(venous_reference["status"])
        return "high", f"Reference-organ enhancement in the venous phase is {direction}.", evidence

    for group in PARALLEL_REFERENCE_GROUPS:
        paired = rows[rows["roi_name"].isin(group)]
        statuses = set(paired["status"].dropna())
        if statuses & CRITICAL_STATUSES and any(status not in CRITICAL_STATUSES for status in statuses):
            evidence = "; ".join(
                f"{row.roi_name} {row.status} in {row.series_folder}"
                for row in paired.itertuples()
            )
            return "low", "One parallel reference organ or vessel is suboptimal while the other is acceptable; segmentation or pathological differences may contribute.", evidence

    medium_rows = rows[
        rows["CT_type"].fillna("").astype(str).str.lower().eq("parenchymal")
        & rows["phase_name"].fillna("").astype(str).str.lower().eq("arteriosa")
        & rows["roi_name"].isin({"aorta", "common_carotid_artery_left", "common_carotid_artery_right"})
        & rows["status"].isin(CRITICAL_STATUSES)
    ]
    if not medium_rows.empty:
        evidence = "; ".join(
            f"{row.roi_name} {row.status} in {row.series_folder}"
            for row in medium_rows.itertuples()
        )
        return "medium", "The arterial phase of a parenchymal examination has suboptimal reference-organ enhancement; the venous phase remains the primary target.", evidence

    critical = reference_rows[reference_rows["status"].isin(CRITICAL_STATUSES)]
    if not critical.empty:
        evidence = "; ".join(
            f"{row.roi_name} {row.status} in {row.series_folder}"
            for row in critical.itertuples()
        )
        direction = _direction_phrase(critical["status"])
        return "high", f"Reference-organ enhancement is {direction}.", evidence

    return "none", "", ""


def _segmentation_warning(detail_df: pd.DataFrame, patient_id: object) -> tuple[str, str]:
    rows = detail_df[
        detail_df["ct_id"].eq(patient_id) & detail_df["status"].eq("missing")
    ]
    if rows.empty:
        return "", ""
    evidence = "; ".join(
        f"{row.roi_name} in {row.series_folder} ({row.warning})"
        for row in rows.itertuples()
    )
    return "Segmentation warning: one or more expected ROIs could not be measured; review segmentation results and consider pathological or acquisition-related causes.", evidence


def build_series_summary_dataframe(results: Iterable[SeriesEvaluation]) -> pd.DataFrame:
    rows = [result.to_summary_row() for result in results]
    return pd.DataFrame(rows)


def build_patient_summary_dataframe(detail_df: pd.DataFrame, series_summary_df: pd.DataFrame) -> pd.DataFrame:
    if series_summary_df.empty:
        return pd.DataFrame(
            columns=[
                "ct_id",
                "ct_name",
                "n_series",
                "n_warning_series",
                "n_critical_rois",
                "n_missing_rois",
                "procedure_codes",
                "phases",
                "warning_priority",
                "warning",
                "warning_evidence",
                "segmentation_warning",
                "segmentation_warning_evidence",
            ]
        )

    detail_df = detail_df.copy()
    if "n_warnings" not in series_summary_df.columns:
        series_summary_df = series_summary_df.copy()
        series_summary_df["n_warnings"] = 0
    detail_df["is_critical"] = detail_df["status"].isin(["critical_low", "critical_high"])
    detail_df["is_missing"] = detail_df["status"].eq("missing")

    critical_counts = detail_df.groupby("ct_id")["is_critical"].sum().rename("n_critical_rois")
    missing_counts = detail_df.groupby("ct_id")["is_missing"].sum().rename("n_missing_rois")

    patient_df = (
        series_summary_df.groupby(["ct_id", "ct_name"], as_index=False)
        .agg(
            n_series=("series_folder", "count"),
            n_warning_series=("n_warnings", lambda s: int((s > 0).sum())),
            procedure_codes=("procedure_code", lambda s: " | ".join(sorted({str(v) for v in s if str(v)}))),
            phases=("phase_name", lambda s: " | ".join(sorted({str(v) for v in s if str(v)}))),
        )
    )

    patient_df = patient_df.merge(critical_counts, on="ct_id", how="left")
    patient_df = patient_df.merge(missing_counts, on="ct_id", how="left")
    patient_df["n_critical_rois"] = patient_df["n_critical_rois"].fillna(0).astype(int)
    patient_df["n_missing_rois"] = patient_df["n_missing_rois"].fillna(0).astype(int)
    warnings = [
        (patient_id, *_patient_warning(detail_df, patient_id))
        for patient_id in patient_df["ct_id"]
    ]
    warning_df = pd.DataFrame(warnings, columns=["ct_id", "warning_priority", "warning", "warning_evidence"])
    patient_df = patient_df.merge(warning_df, on="ct_id", how="left")
    segmentation_warnings = [
        (patient_id, *_segmentation_warning(detail_df, patient_id))
        for patient_id in patient_df["ct_id"]
    ]
    segmentation_df = pd.DataFrame(
        segmentation_warnings,
        columns=["ct_id", "segmentation_warning", "segmentation_warning_evidence"],
    )
    patient_df = patient_df.merge(segmentation_df, on="ct_id", how="left")
    return patient_df.sort_values(["ct_id"]).reset_index(drop=True)


def build_aggregate_stats_dataframe(
    detail_df: pd.DataFrame,
    series_summary_df: pd.DataFrame,
    patient_summary_df: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add_row(dimension: str, value: str, subset_detail: pd.DataFrame, subset_series: pd.DataFrame, subset_patient: pd.DataFrame):
        rows.append(
            {
                "dimension": dimension,
                "group_value": value,
                "n_patients": int(subset_patient["ct_id"].nunique()) if not subset_patient.empty else 0,
                "n_series": int(len(subset_series)),
                "n_rois": int(len(subset_detail)),
                "n_warning_series": int((subset_series.get("n_warnings", pd.Series(dtype=int)) > 0).sum()) if not subset_series.empty else 0,
                "n_critical_rois": int(subset_detail["status"].isin(["critical_low", "critical_high"]).sum()) if not subset_detail.empty else 0,
                "n_missing_rois": int(subset_detail["status"].eq("missing").sum()) if not subset_detail.empty else 0,
                "mean_evaluated_value": float(subset_detail["evaluated_value"].dropna().mean()) if not subset_detail.empty and subset_detail["evaluated_value"].notna().any() else None,
                "median_evaluated_value": float(subset_detail["evaluated_value"].dropna().median()) if not subset_detail.empty and subset_detail["evaluated_value"].notna().any() else None,
            }
        )

    add_row("overall", "all", detail_df, series_summary_df, patient_summary_df)

    for column in ["procedure_code", "phase_name", "metric_name", "status"]:
        if column not in detail_df.columns:
            continue
        for value, subset_detail in detail_df.groupby(column, dropna=False):
            value_str = "" if pd.isna(value) else str(value)
            subset_series = series_summary_df[series_summary_df[column] == value] if column in series_summary_df.columns else series_summary_df.iloc[0:0]
            subset_patient = patient_summary_df[patient_summary_df["ct_id"].isin(subset_detail["ct_id"].unique())]
            add_row(column, value_str, subset_detail, subset_series, subset_patient)

    return pd.DataFrame(rows)


def build_markdown_report(
    detail_df: pd.DataFrame,
    series_summary_df: pd.DataFrame,
    patient_summary_df: pd.DataFrame,
    aggregate_stats_df: pd.DataFrame,
    title: str,
) -> str:
    overall = aggregate_stats_df[aggregate_stats_df["dimension"] == "overall"]
    overall_row = overall.iloc[0].to_dict() if not overall.empty else {}

    lines = [f"# {title}", "", "## Overview", ""]
    lines.append(f"- Patients: {int(overall_row.get('n_patients', len(patient_summary_df)) or 0)}")
    lines.append(f"- Series: {int(overall_row.get('n_series', len(series_summary_df)) or 0)}")
    lines.append(f"- ROI evaluations: {int(overall_row.get('n_rois', len(detail_df)) or 0)}")
    lines.append(f"- Warning series: {int(overall_row.get('n_warning_series', 0) or 0)}")
    lines.append(f"- Critical ROIs: {int(overall_row.get('n_critical_rois', 0) or 0)}")
    lines.append("")

    lines.append("## Status Breakdown")
    lines.append("")
    for _, row in aggregate_stats_df[aggregate_stats_df["dimension"] == "status"].sort_values("group_value").iterrows():
        lines.append(f"- {row['group_value']}: {int(row['n_rois'])} ROIs")
    lines.append("")

    if not patient_summary_df.empty:
        lines.append("## Patients")
        lines.append("")
        for _, row in patient_summary_df.sort_values("ct_id").iterrows():
            lines.append(
                f"- CT {int(row['ct_id'])} ({row['ct_name']}): {int(row['n_series'])} series, "
                f"{int(row['n_warning_series'])} warning series, {int(row['n_critical_rois'])} critical ROIs"
            )
        lines.append("")

    return "\n".join(lines)
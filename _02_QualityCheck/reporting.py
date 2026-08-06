from __future__ import annotations

from typing import Iterable

import pandas as pd

from .models import SeriesEvaluation


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
            ]
        )

    detail_df = detail_df.copy()
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
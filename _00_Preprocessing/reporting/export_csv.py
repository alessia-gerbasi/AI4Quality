from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from reporting.vascular_filter import write_parenchymal_selection_outputs, write_vascular_selection_outputs


def _normalize_ct_type(row: pd.Series) -> str | None:
    text = " ".join(
        str(row.get(field, ""))
        for field in ["series_name", "series_folder", "phase_name", "reason_detail"]
    ).lower()
    if "premonitor" in text:
        return "premonitoring"
    if any(token in text for token in ["base", "basale"]):
        return "base"
    if "monitor" in text:
        return "monitoring"
    return str(row.get("CT_type")) if pd.notna(row.get("CT_type")) else None


def _collapse_unified_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "series_path" not in df.columns:
        return df

    working = df.copy()
    if "CT_type" not in working.columns:
        working["CT_type"] = None

    working["CT_type"] = working.apply(_normalize_ct_type, axis=1)
    priority = {"monitoring": 0, "premonitoring": 1, "base": 2, "parenchymal": 3, "vascular": 4}
    working["_ct_priority"] = working["CT_type"].map(lambda value: priority.get(str(value), 99))
    working = working.sort_values(
        by=["series_path", "_ct_priority", "ct_id", "acquisition_time", "series_name"],
        na_position="last",
    )
    working = working.drop_duplicates(subset=["series_path"], keep="first").drop(columns=["_ct_priority"])
    return working.reset_index(drop=True)


def _build_retained_series(df: pd.DataFrame) -> pd.DataFrame:
    accepted = df[df["status"] == "accepted"].copy()
    if accepted.empty:
        return accepted

    singles = accepted[accepted["merge_status"] != "merged_source"].copy()
    merged_sources = accepted[accepted["merge_status"] == "merged_source"].copy()

    if merged_sources.empty:
        return singles

    merged_rows: list[pd.Series] = []
    for _, group in merged_sources.groupby("merge_group_id", dropna=True):
        if group.empty:
            continue

        group = group.sort_values(by=["merge_part_index", "acquisition_time"], na_position="last")
        representative = group.iloc[0].copy()

        # Collapsed final row: keep representative metadata and aggregate per-group volume information.
        representative["merge_status"] = "merged_final"
        representative["merge_part_index"] = None
        representative["merge_part_count"] = int(group["merge_part_count"].dropna().max()) if group["merge_part_count"].notna().any() else len(group)
        representative["instance_count"] = int(pd.to_numeric(group["instance_count"], errors="coerce").fillna(0).sum())

        merged_rows.append(representative)

    merged_final_df = pd.DataFrame(merged_rows)
    retained = pd.concat([singles, merged_final_df], ignore_index=True)
    return retained


def _support_type_from_row(row: pd.Series) -> str:
    text = " ".join(
        str(row.get(field, ""))
        for field in ["series_name", "series_folder", "phase_name", "reason_detail"]
    ).lower()
    if "premonitor" in text:
        return "premonitoring"
    if any(token in text for token in ["base", "basale"]):
        return "base"
    if "monitor" in text:
        return "monitoring"
    return "other"


def _identify_support_only_cts(retained_df: pd.DataFrame) -> pd.DataFrame:
    """Return CT ids/names whose retained accepted rows are only support phases.

    Support phases are CT_type values: base, monitoring, premonitoring.
    """
    if retained_df.empty or "ct_id" not in retained_df.columns:
        return pd.DataFrame(columns=["ct_id", "ct_name", "reason"])

    support_types = {"base", "monitoring", "premonitoring"}
    work = retained_df.copy()
    work["_support_type"] = work.apply(_support_type_from_row, axis=1)

    ct_type_sets = work.groupby("ct_id", dropna=False)["_support_type"].apply(lambda s: set(s.tolist()))
    support_only_ids = {
        ct_id
        for ct_id, type_set in ct_type_sets.items()
        if type_set and type_set.issubset(support_types)
    }

    if not support_only_ids:
        return pd.DataFrame(columns=["ct_id", "ct_name", "reason"])

    excluded_rows = work[work["ct_id"].isin(support_only_ids)].copy()
    excluded_cts = (
        excluded_rows[["ct_id", "ct_name"]]
        .drop_duplicates()
        .sort_values(by=["ct_id", "ct_name"], na_position="last")
        .reset_index(drop=True)
    )
    excluded_cts["reason"] = "only_base_monitoring_premonitoring"

    return excluded_cts


def _drop_support_only_cts(df: pd.DataFrame, excluded_cts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove CTs from unified output when retained rows were support-only."""
    if df.empty or excluded_cts.empty or "ct_id" not in df.columns:
        return df, excluded_cts

    support_only_ids = set(excluded_cts["ct_id"].tolist())
    kept = df[~df["ct_id"].isin(support_only_ids)].copy()
    kept = kept.reset_index(drop=True)
    return kept, excluded_cts


def _drop_premonitoring_from_unified(df: pd.DataFrame) -> pd.DataFrame:
    """Remove premonitoring rows from unified export output."""
    if df.empty or "CT_type" not in df.columns:
        return df
    kept = df[df["CT_type"].astype(str).str.lower() != "premonitoring"].copy()
    return kept.reset_index(drop=True)


def export_outputs(
    output_dir: str,
    decision_rows: list[dict],
    metadata_issues: list[dict],
    summary: dict,
    vascular_selection: dict | None = None,
    parenchymal_selection: dict | None = None,
) -> dict[str, dict] | None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    all_df = pd.DataFrame(decision_rows)
    all_df.to_csv(out / "decisions.csv", index=False)

    retained_df = _build_retained_series(all_df)
    # order by ct_id, series_name, acquisition_time
    retained_df = retained_df.sort_values(by=["ct_id", "series_name", "acquisition_time"], na_position="last")
    retained_df.to_csv(out / "retained_series.csv", index=False)
    excluded_support_only_cts = _identify_support_only_cts(retained_df)

    merged_df = all_df[all_df["merge_status"] == "merged_source"].copy()
    merged_df.to_csv(out / "merged_lineage.csv", index=False)

    pd.DataFrame(metadata_issues).to_csv(out / "metadata_issues.csv", index=False)
    pd.DataFrame([summary]).to_json(out / "run_summary.json", orient="records", indent=2)

    reports: dict[str, dict] = {}
    unified_exclusions = {"excluded_ct_count": 0, "excluded_cts": []}

    if vascular_selection and bool(vascular_selection.get("enabled", True)):
        reports["vascular"] = write_vascular_selection_outputs(out, retained_df, vascular_selection)

    if parenchymal_selection and bool(parenchymal_selection.get("enabled", True)):
        reports["parenchymal"] = write_parenchymal_selection_outputs(out, retained_df, parenchymal_selection)

    if reports:
        combined_frames: list[pd.DataFrame] = []
        vascular_csv = str((vascular_selection or {}).get("output_csv", "retained_series_vascular_filtered.csv"))
        parenchymal_csv = str((parenchymal_selection or {}).get("output_csv", "retained_series_parenchymal_filtered.csv"))

        vascular_path = out / vascular_csv
        if vascular_path.exists():
            vascular_df = pd.read_csv(vascular_path)
            if not vascular_df.empty:
                vascular_df = vascular_df.copy()
                vascular_df["CT_type"] = "vascular"
                combined_frames.append(vascular_df)

        parenchymal_path = out / parenchymal_csv
        if parenchymal_path.exists():
            parenchymal_df = pd.read_csv(parenchymal_path)
            if not parenchymal_df.empty:
                parenchymal_df = parenchymal_df.copy()
                parenchymal_df["CT_type"] = "parenchymal"
                combined_frames.append(parenchymal_df)

        if combined_frames:
            combined_df = pd.concat(combined_frames, ignore_index=True)
            if "_phase_key" in combined_df.columns:
                combined_df = combined_df.drop(columns=["_phase_key"])
            combined_df = _collapse_unified_rows(combined_df)
            combined_df = _drop_premonitoring_from_unified(combined_df)
            combined_df, excluded_cts = _drop_support_only_cts(combined_df, excluded_support_only_cts)
            sort_cols = [c for c in ["ct_id", "CT_type", "series_name", "acquisition_time"] if c in combined_df.columns]
            if sort_cols:
                combined_df = combined_df.sort_values(by=sort_cols, na_position="last").reset_index(drop=True)
            combined_df.to_csv(out / "retained_series_unified_filtered.csv", index=False)

            excluded_cts.to_csv(out / "retained_series_unified_excluded_support_only_cts.csv", index=False)
            report_payload = {
                "excluded_ct_count": int(len(excluded_cts)),
                "excluded_cts": excluded_cts.to_dict(orient="records"),
            }
            unified_exclusions = report_payload
            (out / "retained_series_unified_excluded_support_only_cts.json").write_text(
                json.dumps(report_payload, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
        else:
            empty_df = retained_df.head(0).copy()
            if "_phase_key" in empty_df.columns:
                empty_df = empty_df.drop(columns=["_phase_key"])
            empty_df.assign(CT_type=pd.Series(dtype="object")).to_csv(out / "retained_series_unified_filtered.csv", index=False)
            pd.DataFrame(columns=["ct_id", "ct_name", "reason"]).to_csv(
                out / "retained_series_unified_excluded_support_only_cts.csv",
                index=False,
            )
            (out / "retained_series_unified_excluded_support_only_cts.json").write_text(
                json.dumps({"excluded_ct_count": 0, "excluded_cts": []}, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
            unified_exclusions = {"excluded_ct_count": 0, "excluded_cts": []}

        reports["unified_exclusions"] = unified_exclusions

        return reports

    return None

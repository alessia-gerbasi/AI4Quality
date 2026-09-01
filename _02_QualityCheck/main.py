#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from contextlib import nullcontext
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _dependency_error_message(missing_module: str, script_name: str) -> str:
    python_ctq = "/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python"
    return (
        f"Missing Python module '{missing_module}'.\n\n"
        f"This command is being executed with a Python environment that does not have the AI4Quality dependencies installed.\n"
        f"Use the ctq environment, for example:\n"
        f"  {python_ctq} {script_name}\n\n"
        f"Or activate the environment first and rerun the command."
    )


try:
    import pandas as pd

    from _02_QualityCheck.config_loader import (
        load_keyword_overrides,
        load_rules,
        normalize_phase,
        resolve_effective_phase,
        resolve_effective_procedure_code,
    )
    from _02_QualityCheck.hu_metrics import (
        load_nifti_array,
        measure_roi_edge_means,
        measure_roi_statistics,
        select_slice_for_visualization,
    )
    from _02_QualityCheck.models import RoiMeasurement, SeriesEvaluation
    from _02_QualityCheck.reporting import (
        build_aggregate_stats_dataframe,
        build_patient_summary_dataframe,
        build_series_summary_dataframe,
    )
    from _02_QualityCheck.rules_engine import score_value
    from _02_QualityCheck.series_index import build_series_dir, find_baseline_for_venous, iter_target_series, load_series_table
    from _02_QualityCheck.visualization import render_series_qc_image
except ModuleNotFoundError as exc:
    print(_dependency_error_message(exc.name or "unknown", "_02_QualityCheck/main.py"), file=sys.stderr)
    raise SystemExit(1) from exc

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    tqdm = None


log = logging.getLogger("hu_quality_check")


def _build_progress(total: int):
    if tqdm is None or total <= 0:
        return nullcontext()
    return tqdm(total=total, desc="QualityCheck", unit="series", dynamic_ncols=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute HU quality for segmented ROIs by exam phase")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("_00_Preprocessing/OUTPUTS/retained_series_unified_filtered.csv"),
        help="CSV with retained series and phase_name",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path("config/common/ct_protocols.yaml"),
        help="YAML with ROI definitions and HU thresholds",
    )
    parser.add_argument(
        "--nii-root",
        type=Path,
        default=Path("/data/alessia.gerbasi/DATA/CDI_NEXO_072026/2_nii"),
        help="Root folder containing CT.nii.gz and ROI masks",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("_02_QualityCheck/OUTPUTS"),
        help="Output folder for tables and images",
    )
    parser.add_argument("--max-cases", type=int, default=None, help="Optional limit for quick tests")
    parser.add_argument("--ct-ids", type=int, nargs="*", default=None, help="Optional list of ct_id to process")
    parser.add_argument(
        "--vascular-edge-slices",
        type=int,
        default=5,
        help="Number of first and last vessel-containing slices used for attenuation consistency (default: 5)",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def _collect_measurements(
    ct_path: Path,
    rois: list[str],
    series_dir: Path,
    edge_slices: int | None = None,
) -> tuple[list[RoiMeasurement], dict[str, object], object]:
    ct = load_nifti_array(ct_path)
    measurements: list[RoiMeasurement] = []
    roi_masks: dict[str, object] = {}

    for roi in rois:
        mask_path = series_dir / f"{roi}.nii.gz"
        if not mask_path.exists():
            measurements.append(RoiMeasurement(roi_name=roi))
            continue

        mask = load_nifti_array(mask_path)
        mean_hu, std_hu, median_hu, n_vox = measure_roi_statistics(ct, mask)
        proximal_mean_hu, distal_mean_hu = (
            measure_roi_edge_means(ct, mask, edge_slices) if edge_slices is not None else (None, None)
        )
        z_idx = select_slice_for_visualization(mask)
        measurements.append(
            RoiMeasurement(
                roi_name=roi,
                mean_hu=mean_hu,
                std_hu=std_hu,
                median_hu=median_hu,
                median_std_hu=std_hu,
                voxel_count=n_vox,
                slice_index=z_idx,
                proximal_mean_hu=proximal_mean_hu,
                distal_mean_hu=distal_mean_hu,
                edge_slice_count=edge_slices,
            )
        )
        roi_masks[roi] = mask

    return measurements, roi_masks, ct


def _index_by_roi(measurements: list[RoiMeasurement]) -> dict[str, RoiMeasurement]:
    return {m.roi_name: m for m in measurements}


def _classify_vascular_attenuation(measurement: RoiMeasurement, threshold) -> bool:
    proximal_score = score_value(measurement.proximal_mean_hu, threshold)
    distal_score = score_value(measurement.distal_mean_hu, threshold)
    measurement.proximal_status = proximal_score.status
    measurement.distal_status = distal_score.status

    critical = {"critical_low", "critical_high"}
    incoherent = proximal_score.status != distal_score.status and bool(
        {proximal_score.status, distal_score.status} & critical
    )
    measurement.attenuation_consistency = "incoherent" if incoherent else "consistent"

    roi_label = measurement.roi_name.replace("_", " ").title()
    values = (
        f"Proximal: {measurement.proximal_mean_hu:.0f} HU ({proximal_score.label}); "
        f"Distal: {measurement.distal_mean_hu:.0f} HU ({distal_score.label})."
    )
    if incoherent:
        measurement.attenuation_message = (
            f"{roi_label} attenuation is incoherent. {values} In the absence of pathological issues, "
            "incoherent attenuation may suggest a timing-related acquisition error."
        )
    elif proximal_score.status == distal_score.status == "critical_low":
        measurement.attenuation_message = f"{roi_label} enhancement is consistently low. {values}"
    elif proximal_score.status == distal_score.status == "critical_high":
        measurement.attenuation_message = f"{roi_label} enhancement is consistently high. {values}"
    else:
        measurement.attenuation_message = f"{roi_label} endpoint attenuation is consistent. {values}"
    return incoherent


def _evaluate_series(
    row: pd.Series,
    df_patient: pd.DataFrame,
    rules,
    nii_root: Path,
    output_dir: Path,
    keyword_overrides: dict[str, str] | None = None,
    vascular_edge_slices: int = 5,
) -> SeriesEvaluation | None:
    phase = resolve_effective_phase(row.get("phase_name", ""), row.get("CT_type", ""))
    ct_type = str(row.get("CT_type", "") or "")
    raw_code = str(row.get("procedure_code_norm", "")).upper()
    series_text = f"{row.get('series_name', '')} {row.get('series_folder', '')}"
    # The procedure code identity is never changed; only the ROI/HU lookup uses the override.
    rule_lookup_code = resolve_effective_procedure_code(raw_code, series_text, keyword_overrides or {})
    code = raw_code
    rule = rules.get(rule_lookup_code)
    if not rule:
        return None

    phase_rule = rule.phases.get(phase)
    if not phase_rule or not phase_rule.rois:
        return None

    override_note = (
        f"ROI/HU thresholds referenced from {rule_lookup_code} due to keyword match" if rule_lookup_code != raw_code else None
    )

    series_dir = build_series_dir(nii_root, row)
    ct_path = series_dir / "CT.nii.gz"
    if not ct_path.exists():
        return SeriesEvaluation(
            ct_id=int(row["ct_id"]),
            ct_name=str(row.get("ct_name", "")),
            ct_folder=str(row.get("ct_folder", "")),
            ct_type=ct_type,
            procedure_code=code,
            phase_name=phase,
            series_folder=str(row.get("series_folder", "")),
            series_dir=str(series_dir),
            reference_series_folder=None,
            metric_name=f"HU_{phase}",
            threshold=phase_rule.hu_threshold,
            measurements=[RoiMeasurement(roi_name=r) for r in phase_rule.rois],
            scores={r: score_value(None, phase_rule.hu_threshold) for r in phase_rule.rois},
            warnings=["CT.nii.gz is missing"] + ([override_note] if override_note else []),
        )

    measurements, roi_masks, ct = _collect_measurements(
        ct_path,
        phase_rule.rois,
        series_dir,
        edge_slices=vascular_edge_slices if ct_type.strip().lower() == "vascular" else None,
    )
    warnings: list[str] = [override_note] if override_note else []
    metric_name = f"HU_{phase}"
    threshold = phase_rule.hu_threshold
    reference_series_folder = None

    if phase == "venosa" and phase_rule.hu_delta_threshold is not None:
        baseline_row = find_baseline_for_venous(df_patient, row)
        if baseline_row is not None:
            baseline_dir = build_series_dir(nii_root, baseline_row)
            baseline_ct_path = baseline_dir / "CT.nii.gz"
            if baseline_ct_path.exists():
                baseline_measurements, _, _ = _collect_measurements(
                    baseline_ct_path,
                    phase_rule.rois,
                    baseline_dir,
                )
                baseline_by_roi = _index_by_roi(baseline_measurements)

                for m in measurements:
                    b = baseline_by_roi.get(m.roi_name)
                    if not b:
                        continue
                    m.mean_hu_precontrast = b.mean_hu
                    m.std_hu_precontrast = b.std_hu
                    m.median_hu_precontrast = b.median_hu
                    m.median_std_hu_precontrast = b.median_std_hu
                    if m.mean_hu is not None and b.mean_hu is not None:
                        m.delta_hu = m.mean_hu - b.mean_hu
                    if m.median_hu is not None and b.median_hu is not None:
                        m.delta_median_hu = m.median_hu - b.median_hu

                metric_name = "HU_delta_venosa"
                threshold = phase_rule.hu_delta_threshold
                reference_series_folder = str(baseline_row.get("series_folder", ""))
            else:
                warnings.append("Baseline CT.nii.gz missing, falling back to HU_venosa")

    scores = {}
    for m in measurements:
        value = m.delta_hu if metric_name == "HU_delta_venosa" else m.mean_hu
        score = score_value(value, threshold)
        scores[m.roi_name] = score
        if score.warning:
            warnings.append(f"{m.roi_name}: {score.warning}")
        if ct_type.strip().lower() == "vascular" and m.proximal_mean_hu is not None and m.distal_mean_hu is not None:
            if _classify_vascular_attenuation(m, phase_rule.hu_threshold):
                warnings.append(m.attenuation_message)

    if phase == "venosa":
        liver = next((m for m in measurements if m.roi_name == "liver"), None)
        if liver and liver.mean_hu is not None and liver.mean_hu < 40:
            warnings.append(
                "Possible hepatic steatosis (liver mean HU < 40): spleen enhancement may be more appropriate"
            )

    result = SeriesEvaluation(
        ct_id=int(row["ct_id"]),
        ct_name=str(row.get("ct_name", "")),
        ct_folder=str(row.get("ct_folder", "")),
        ct_type=ct_type,
        procedure_code=code,
        phase_name=phase,
        series_folder=str(row.get("series_folder", "")),
        series_dir=str(series_dir),
        reference_series_folder=reference_series_folder,
        metric_name=metric_name,
        threshold=threshold,
        measurements=measurements,
        scores=scores,
        warnings=warnings,
    )

    image_name = f"ct{result.ct_id}_{result.series_folder}_qc.png".replace(" ", "_")
    image_path = output_dir / "images" / image_name
    render_series_qc_image(
        ct_volume=ct,
        roi_masks=roi_masks,
        measurements=measurements,
        scores=scores,
        threshold=threshold,
        output_path=image_path,
        title=f"CT {result.ct_id} | {result.series_folder} | {metric_name}",
        series_warnings=warnings,
    )
    result.output_image_path = str(image_path)

    return result


def run() -> int:
    args = _parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s [%(levelname)s] %(message)s")

    rules = load_rules(args.rules)
    keyword_overrides = load_keyword_overrides(args.rules)
    df = load_series_table(args.csv)

    if args.ct_ids:
        df = df[df["ct_id"].isin(args.ct_ids)].copy()
    if args.max_cases is not None:
        df = df.head(args.max_cases).copy()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[SeriesEvaluation] = []
    grouped_targets: list[tuple[int, pd.DataFrame, list[pd.Series]]] = []
    total_targets = 0

    for ct_id, df_patient in df.groupby("ct_id", sort=True):
        targets = list(iter_target_series(df_patient))
        if not targets:
            continue
        grouped_targets.append((ct_id, df_patient, targets))
        total_targets += len(targets)

    with _build_progress(total_targets) as progress:
        for ct_id, df_patient, targets in grouped_targets:
            if progress is not None:
                progress.set_postfix_str(f"ct_id={ct_id} ({len(targets)} series)")

            for row in targets:
                try:
                    evaluation = _evaluate_series(
                        row=row,
                        df_patient=df_patient,
                        rules=rules,
                        nii_root=args.nii_root,
                        output_dir=output_dir,
                        keyword_overrides=keyword_overrides,
                        vascular_edge_slices=args.vascular_edge_slices,
                    )
                    if evaluation is not None:
                        all_results.append(evaluation)
                except Exception as exc:
                    log.exception("Failed HU evaluation for ct_id=%s series=%s", ct_id, row.get("series_folder", ""))
                    raw_code = str(row.get("procedure_code_norm", "")).upper()
                    fallback = SeriesEvaluation(
                        ct_id=int(row["ct_id"]),
                        ct_name=str(row.get("ct_name", "")),
                        ct_folder=str(row.get("ct_folder", "")),
                        ct_type=str(row.get("CT_type", "") or ""),
                        procedure_code=raw_code,
                        phase_name=normalize_phase(row.get("phase_name", "")),
                        series_folder=str(row.get("series_folder", "")),
                        series_dir=str(build_series_dir(args.nii_root, row)),
                        reference_series_folder=None,
                        metric_name="error",
                        threshold=None,
                        measurements=[],
                        scores={},
                        warnings=[f"Exception: {exc}"],
                    )
                    all_results.append(fallback)
                finally:
                    if progress is not None:
                        progress.update(1)

    rows = []
    for result in all_results:
        rows.extend(result.to_rows())

    df_out = pd.DataFrame(rows)
    table_path = output_dir / "roi_hu_qc_results.csv"
    df_out.to_csv(table_path, index=False)

    series_summary_df = build_series_summary_dataframe(all_results)
    patient_summary_df = build_patient_summary_dataframe(df_out, series_summary_df)
    aggregate_stats_df = build_aggregate_stats_dataframe(df_out, series_summary_df, patient_summary_df)

    series_summary_df.to_csv(output_dir / "roi_hu_qc_summary.csv", index=False)
    patient_summary_df.to_csv(output_dir / "patient_hu_qc_summary.csv", index=False)
    aggregate_stats_df.to_csv(output_dir / "aggregate_hu_qc_stats.csv", index=False)

    log.info("Processed %d series", len(all_results))
    log.info("Detailed output: %s", table_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

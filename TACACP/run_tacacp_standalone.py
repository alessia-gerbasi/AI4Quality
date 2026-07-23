from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pydicom

from config.schema import load_config
from dataio.dicom_scanner import scan_series
from domain.models import EnrichedSeriesRecord, SeriesRecord
from merge.collapsed_volume_writer import write_collapsed_volumes
from merge.split_series_resolver import resolve_split_groups
from reporting.export_csv import export_outputs
from reporting.reporter import summarize
from runlog.logger import RunLogger
from series_selectors.keyword_selector import KeywordSelector


def parse_ct_identity(ct_folder: str) -> tuple[str | None, str | None]:
    # Original pattern used in existing pipeline.
    parts = ct_folder.split("_")
    if len(parts) >= 4 and parts[0] == "CT" and parts[1] == "QUALITY":
        ct_id = parts[2]
        ct_name = "_".join(parts[3:]) if len(parts) > 3 else None
        return ct_id, ct_name

    # Flexible fallback for datasets like TACACP_<id>_<name>.
    if len(parts) >= 3 and parts[1].isdigit():
        ct_id = parts[1]
        ct_name = "_".join(parts[2:]) if len(parts) > 2 else None
        return ct_id, ct_name

    return None, None


def _safe_first_dicom(series_path: Path) -> tuple[dict, list[str], int]:
    issues: list[str] = []
    dicom_files = [p for p in series_path.rglob("*") if p.is_file()]

    if not dicom_files:
        return {}, ["empty_series_folder"], 0

    dataset = None
    count = len(dicom_files)
    for fp in dicom_files:
        try:
            ds = pydicom.dcmread(
                str(fp),
                stop_before_pixels=True,
                force=True,
                specific_tags=[
                    "SeriesDescription",
                    "BodyPartExamined",
                    "AcquisitionTime",
                ],
            )
            if dataset is None:
                dataset = ds
                break
        except Exception:
            issues.append("non_readable_dicom_file")

    if dataset is None:
        return {}, ["no_valid_dicom_header"], 0

    return {
        "SeriesDescription": str(getattr(dataset, "SeriesDescription", "") or ""),
        "BodyPartExamined": str(getattr(dataset, "BodyPartExamined", "") or "") or None,
        "AcquisitionTime": str(getattr(dataset, "AcquisitionTime", "") or "") or None,
        "SeriesInstanceUID": None,
    }, sorted(set(issues)), count


def _iter_exam_folders_generic(input_root: Path) -> Iterable[Path]:
    if not input_root.exists():
        return

    if (input_root / "studyinstanceuid").is_dir():
        yield input_root
        return

    for child in sorted(input_root.iterdir()):
        if child.is_dir() and (child / "studyinstanceuid").is_dir():
            yield child


def _scan_series_flexible(input_root: str, max_ct: int | None = None) -> list[SeriesRecord]:
    # First try the original project scanner (CT_QUALITY_* layout).
    records = scan_series([input_root], max_ct=max_ct)
    if records:
        return records

    # Fallback scanner for non CT_QUALITY naming (e.g. TACACP_*).
    root_path = Path(input_root)
    flexible_records: list[SeriesRecord] = []
    ct_seen = 0
    for exam_folder in _iter_exam_folders_generic(root_path):
        ct_seen += 1
        if max_ct is not None and ct_seen > max_ct:
            break

        study_wrapper = exam_folder / "studyinstanceuid"
        for series_dir in sorted(study_wrapper.iterdir()):
            if not series_dir.is_dir():
                continue
            header, issues, count = _safe_first_dicom(series_dir)
            series_name = header.get("SeriesDescription") or series_dir.name
            flexible_records.append(
                SeriesRecord(
                    ct_folder=exam_folder.name,
                    study_folder=study_wrapper.name,
                    series_folder=series_dir.name,
                    series_path=str(series_dir),
                    series_name=series_name,
                    body_part_examined=header.get("BodyPartExamined"),
                    acquisition_time=header.get("AcquisitionTime"),
                    series_description=header.get("SeriesDescription"),
                    series_instance_uid=header.get("SeriesInstanceUID"),
                    instance_count=count,
                    metadata_issues=issues,
                )
            )

    return flexible_records


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Standalone CT selection/aggregation runner without Excel/CSV enrichment. "
            "It reuses the same scan, keyword-selection, merge and reporting logic "
            "from the preprocessing pipeline."
        )
    )
    parser.add_argument(
        "--input-root",
        required=True,
        help="Root folder containing CT_QUALITY_* folders (or a single CT_QUALITY_* folder).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output folder for decisions/retained csv and summaries.",
    )
    parser.add_argument(
        "--config",
        default="/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/config/defaults.yaml",
        help="Path to YAML config used for selection/merge/filter rules.",
    )
    parser.add_argument(
        "--procedure-code",
        default="TACACP",
        help="Procedure code assigned to all CTs (default: TACACP).",
    )
    parser.add_argument(
        "--max-ct",
        type=int,
        default=None,
        help="Optional limit on number of CT folders to process.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without writing output files.")
    parser.add_argument(
        "--write-collapsed-volumes",
        action="store_true",
        help="Force-enable collapsed NIfTI writing for merged groups.",
    )
    parser.add_argument(
        "--collapse-overwrite",
        action="store_true",
        help="Overwrite existing *_collapsed.nii.gz files.",
    )
    return parser


def _build_selector(cfg) -> KeywordSelector:
    exclude_keywords = [k.lower() for k in cfg.selection["exclude_keywords"]]
    # TACACP-specific cleanup: exclude VSPP reconstructions from candidate pool.
    if "vspp" not in exclude_keywords:
        exclude_keywords.append("vspp")

    return KeywordSelector(
        accepted_codes=set(cfg.selection["accepted_procedure_codes"]),
        vascular_codes=set(cfg.selection.get("procedure_groups", {}).get("vascular", [])),
        phase_keywords=[k.lower() for k in cfg.selection.get("phase_keywords", cfg.selection["include_keywords"])],
        include_keywords=[k.lower() for k in cfg.selection["include_keywords"]],
        exclude_keywords=exclude_keywords,
        force_accept_keywords=[k.lower() for k in cfg.selection.get("force_accept_keywords", [])],
        exclude_keyword_veto={
            k.lower(): [v.lower() for v in vals]
            for k, vals in cfg.selection.get("exclude_keyword_veto", {}).items()
        },
        procedure_specific_include_only={
            k.upper(): [v.lower() for v in vals]
            for k, vals in cfg.selection.get("procedure_specific_include_only", {}).items()
        },
        precedence=str(cfg.selection["precedence"]).lower(),
    )


def _enrich_without_excel(records, procedure_code: str) -> tuple[list[EnrichedSeriesRecord], list[dict]]:
    enriched: list[EnrichedSeriesRecord] = []
    for rec in records:
        enriched.append(
            EnrichedSeriesRecord(
                base=rec,
                scanner=None,
                procedure_code_value=procedure_code,
            )
        )
    return enriched, []


def _build_vascular_rules_for_tacacp(cfg) -> dict:
    # Local override for TACACP subset: keep the best remaining series and
    # also force-keep one best extra match for angio/embolia names.
    rules = dict(cfg.vascular_selection)
    existing_patterns = [str(p).lower() for p in rules.get("keep_additional_name_patterns", [])]
    # Single pattern avoids duplicate picks when one series matches multiple tokens.
    if "angio" not in existing_patterns:
        existing_patterns.append("angio")
    rules["keep_additional_name_patterns"] = existing_patterns
    # Enforce one angio/embolia candidate per CT by disabling the generic
    # additional "best remaining" slot for this TACACP-specific run.
    rules["select_one_best_remaining"] = False
    return rules


def main() -> int:
    args = build_arg_parser().parse_args()
    cfg = load_config(args.config)

    input_root = str(Path(args.input_root).resolve())
    output_dir = str(Path(args.output_dir).resolve())
    procedure_code = str(args.procedure_code).strip().upper()

    if not procedure_code:
        raise ValueError("--procedure-code cannot be empty")

    logger = RunLogger(
        output_dir=output_dir,
        jsonl_filename=cfg.logging["jsonl_file"],
        console=bool(cfg.logging["console"]),
    )

    logger.log(
        "standalone_pipeline_start",
        config=args.config,
        input_root=input_root,
        procedure_code=procedure_code,
        skip_excel_enrichment=True,
    )

    max_ct = args.max_ct if args.max_ct is not None else cfg.runtime["max_ct"]
    series_records = _scan_series_flexible(input_root, max_ct=max_ct)
    logger.log("scan_completed", series_count=len(series_records))

    enriched, metadata_issues = _enrich_without_excel(series_records, procedure_code=procedure_code)
    logger.log("enrichment_skipped", enriched_count=len(enriched), metadata_issues=len(metadata_issues))

    selector = _build_selector(cfg)
    merge_map = resolve_split_groups(
        enriched,
        require_contiguous_prefixes=bool(cfg.merge["require_contiguous_prefixes"]),
    )

    decision_rows: list[dict] = []
    for idx, item in enumerate(enriched):
        dec = selector.decide(item)
        merge = merge_map.get(idx)
        ct_id, ct_name = parse_ct_identity(item.base.ct_folder)

        decision_rows.append(
            {
                "ct_id": ct_id,
                "ct_name": ct_name,
                "ct_folder": item.base.ct_folder,
                "series_name": item.base.series_name,
                "series_folder": item.base.series_folder,
                "series_path": item.base.series_path,
                "procedure_code_value": item.procedure_code_value,
                "body_part_examined": item.base.body_part_examined,
                "acquisition_time": item.base.acquisition_time,
                "status": dec.status,
                "reason_code": dec.reason_code,
                "reason_detail": dec.reason_detail,
                "phase_name": dec.phase_name,
                "include_hits": "|".join(dec.include_hits),
                "exclude_hits": "|".join(dec.exclude_hits),
                "merge_group_id": merge.merge_group_id if merge else None,
                "merge_status": merge.merge_status if merge else "single",
                "merge_part_index": merge.part_index if merge else None,
                "merge_part_count": merge.part_count if merge else None,
                "scanner": item.scanner,
                "metadata_issues": "|".join(item.base.metadata_issues),
                "instance_count": item.base.instance_count,
            }
        )

    summary = summarize(decision_rows, metadata_issues)
    logger.log("selection_completed", summary=summary)

    if not decision_rows:
        logger.log("no_series_found", input_root=input_root)
        logger.log("standalone_pipeline_end")
        return 0

    if args.dry_run or bool(cfg.runtime["dry_run"]):
        logger.log("dry_run_complete", output_dir=output_dir)
        return 0

    collapse_report = write_collapsed_volumes(
        decision_rows,
        enabled=bool(cfg.merge.get("write_collapsed_volumes", False)) or bool(args.write_collapsed_volumes),
        only_accepted=bool(cfg.merge.get("collapsed_only_accepted", True)),
        skip_existing=(False if bool(args.collapse_overwrite) else bool(cfg.merge.get("collapsed_skip_existing", True))),
        include_ct_ids=None,
        max_groups=cfg.merge.get("collapsed_max_groups"),
    )
    logger.log(
        "collapsed_volumes_completed",
        enabled=collapse_report.get("enabled"),
        groups_detected=collapse_report.get("groups_detected"),
        groups_considered=collapse_report.get("groups_considered"),
        volumes_written=collapse_report.get("volumes_written"),
        volumes_skipped_existing=collapse_report.get("volumes_skipped_existing"),
        errors=len(collapse_report.get("errors", [])),
    )

    selection_reports = export_outputs(
        output_dir,
        decision_rows,
        metadata_issues,
        summary,
        vascular_selection=_build_vascular_rules_for_tacacp(cfg),
        parenchymal_selection=cfg.parenchymal_selection,
    )

    if selection_reports is not None:
        unified_exclusions = selection_reports.get("unified_exclusions")
        if unified_exclusions is not None:
            logger.log(
                "unified_support_only_cts_excluded",
                excluded_ct_count=unified_exclusions.get("excluded_ct_count", 0),
                excluded_cts=unified_exclusions.get("excluded_cts", []),
            )

        vascular_summary = selection_reports.get("vascular")
        if vascular_summary is not None:
            for exam in vascular_summary.get("no_eligible_exams", []):
                logger.log(
                    "vascular_selection_no_eligible_series",
                    ct_id=exam.get("ct_id"),
                    ct_name=exam.get("ct_name"),
                    phase=exam.get("phase_key"),
                    monitoring_rows=exam.get("monitoring_count"),
                )
            logger.log(
                "vascular_selection_completed",
                exam_count=vascular_summary.get("exam_count"),
                group_count=vascular_summary.get("group_count"),
                selected_vascular_count=vascular_summary.get("selected_vascular_count"),
                monitoring_rows_kept=vascular_summary.get("monitoring_rows_kept"),
            )

        parenchymal_summary = selection_reports.get("parenchymal")
        if parenchymal_summary is not None:
            for exam in parenchymal_summary.get("no_eligible_exams", []):
                logger.log(
                    "parenchymal_selection_no_eligible_series",
                    ct_id=exam.get("ct_id"),
                    ct_name=exam.get("ct_name"),
                    phase=exam.get("phase_key"),
                    monitoring_rows=exam.get("monitoring_count"),
                )
            logger.log(
                "parenchymal_selection_completed",
                exam_count=parenchymal_summary.get("exam_count"),
                group_count=parenchymal_summary.get("group_count"),
                selected_parenchymal_count=parenchymal_summary.get("selected_parenchymal_count"),
                monitoring_rows_kept=parenchymal_summary.get("monitoring_rows_kept"),
            )

    logger.log("export_completed", output_dir=output_dir)
    logger.log("standalone_pipeline_end")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

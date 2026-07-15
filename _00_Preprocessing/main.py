from __future__ import annotations

import argparse

from config.schema import load_config
from dataio.dicom_scanner import scan_series
from dataio.excel_loader import enrich_series, load_excel_context
from runlog.logger import RunLogger
from merge.split_series_resolver import resolve_split_groups
from merge.collapsed_volume_writer import write_collapsed_volumes
from reporting.export_csv import export_outputs
from reporting.reporter import summarize
from series_selectors.keyword_selector import KeywordSelector


def parse_ct_identity(ct_folder: str) -> tuple[str | None, str | None]:
    parts = ct_folder.split("_")
    if len(parts) < 4:
        return None, None
    if parts[0] != "CT" or parts[1] != "QUALITY":
        return None, None
    ct_id = parts[2]
    ct_name = "_".join(parts[3:]) if len(parts) > 3 else None
    return ct_id, ct_name


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AI4Quality preprocessing pipeline")
    p.add_argument("--config", required=True, help="Path to YAML config")
    p.add_argument("--dry-run", action="store_true", help="Run without writing outputs")
    p.add_argument("--max-ct", type=int, default=None, help="Limit number of CT folders")
    p.add_argument(
        "--collapse-ct-ids",
        type=str,
        default=None,
        help="Optional comma-separated CT ids for collapsed volume writing",
    )
    p.add_argument(
        "--write-collapsed-volumes",
        action="store_true",
        help="Force-enable collapsed volume writing for this run",
    )
    p.add_argument(
        "--collapse-overwrite",
        action="store_true",
        help="Overwrite existing *_collapsed.nii.gz files for selected groups",
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    cfg = load_config(args.config)

    output_dir = cfg.io["output_dir"]
    logger = RunLogger(
        output_dir=output_dir,
        jsonl_filename=cfg.logging["jsonl_file"],
        console=bool(cfg.logging["console"]),
    )

    logger.log("pipeline_start", config=args.config)

    max_ct = args.max_ct if args.max_ct is not None else cfg.runtime["max_ct"]

    series_records = scan_series(cfg.io["dicom_roots"], max_ct=max_ct)
    logger.log("scan_completed", series_count=len(series_records))

    excel_ctx = load_excel_context(
        link_xlsx=cfg.io["link_anonymization_xlsx"],
        injection_xlsx=cfg.io["injection_history_xlsx"],
    )
    enriched, metadata_issues = enrich_series(series_records, excel_ctx)
    logger.log("enrichment_completed", enriched_count=len(enriched), metadata_issues=len(metadata_issues))

    selector = KeywordSelector(
        accepted_codes=set(cfg.selection["accepted_procedure_codes"]),
        vascular_codes=set(cfg.selection.get("procedure_groups", {}).get("vascular", [])),
        phase_keywords=[k.lower() for k in cfg.selection.get("phase_keywords", cfg.selection["include_keywords"])],
        include_keywords=[k.lower() for k in cfg.selection["include_keywords"]],
        exclude_keywords=[k.lower() for k in cfg.selection["exclude_keywords"]],
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

    merge_map = resolve_split_groups(
        enriched,
        require_contiguous_prefixes=bool(cfg.merge["require_contiguous_prefixes"]),
    )

    decision_rows: list[dict] = []
    for idx, item in enumerate(enriched):
        dec = selector.decide(item)
        merge = merge_map.get(idx)
        ct_id, ct_name = parse_ct_identity(item.base.ct_folder)

        row = {
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
        decision_rows.append(row)

    summary = summarize(decision_rows, metadata_issues)
    logger.log("selection_completed", summary=summary)

    if args.dry_run or bool(cfg.runtime["dry_run"]):
        logger.log("dry_run_complete", output_dir=output_dir)
        return 0

    collapse_ct_ids = None
    if args.collapse_ct_ids:
        collapse_ct_ids = {item.strip() for item in args.collapse_ct_ids.split(",") if item.strip()}

    collapse_report = write_collapsed_volumes(
        decision_rows,
        enabled=bool(cfg.merge.get("write_collapsed_volumes", False)) or bool(args.write_collapsed_volumes),
        only_accepted=bool(cfg.merge.get("collapsed_only_accepted", True)),
        skip_existing=(False if bool(args.collapse_overwrite) else bool(cfg.merge.get("collapsed_skip_existing", True))),
        include_ct_ids=collapse_ct_ids,
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
        vascular_selection=cfg.vascular_selection,
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
            for item in vascular_summary.get("no_eligible_exams", []):
                logger.log(
                    "vascular_selection_no_eligible_series",
                    ct_id=item.get("ct_id"),
                    ct_name=item.get("ct_name"),
                    phase=item.get("phase_key"),
                    monitoring_rows=item.get("monitoring_count"),
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
            for item in parenchymal_summary.get("no_eligible_exams", []):
                logger.log(
                    "parenchymal_selection_no_eligible_series",
                    ct_id=item.get("ct_id"),
                    ct_name=item.get("ct_name"),
                    phase=item.get("phase_key"),
                    monitoring_rows=item.get("monitoring_count"),
                )
            logger.log(
                "parenchymal_selection_completed",
                exam_count=parenchymal_summary.get("exam_count"),
                group_count=parenchymal_summary.get("group_count"),
                selected_parenchymal_count=parenchymal_summary.get("selected_parenchymal_count"),
                monitoring_rows_kept=parenchymal_summary.get("monitoring_rows_kept"),
            )
    logger.log("export_completed", output_dir=output_dir)
    logger.log("pipeline_end")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

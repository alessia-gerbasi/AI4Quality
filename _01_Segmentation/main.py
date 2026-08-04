#!/usr/bin/env python3
"""
Segmentation pipeline: DICOM → CT.nii.gz → phase.json + organ masks + sanity_check.png.

Usage
-----
    python main.py                          # full run with defaults.yaml
    python main.py --config path/to.yaml    # custom config
    python main.py --test-mode --test-max-n 2
    python main.py --dry-run                # print plan, no conversion/segmentation
    python main.py --ct-ids 1 11 17         # run specific patients
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# Make local packages importable when run as a script from _01_Segmentation/
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dataio.dicom_converter import convert_dicom_to_nifti, copy_nifti_as_ct
from dataio.roi_mapper import RoiMapper
from segmentation.phase_predictor import predict_phase
from segmentation.task_router import build_task_calls
from segmentation.runner import run_task_calls
from utils.merged_series_resolver import find_collapsed_nifti, output_folder_name
from visualization.sanity_check import save_sanity_check


# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ── Config helpers ────────────────────────────────────────────────────────────

def _load_config(config_path: Path) -> dict[str, Any]:
    with open(config_path) as fh:
        return yaml.safe_load(fh) or {}


def _apply_cli_overrides(cfg: dict[str, Any], args: argparse.Namespace) -> None:
    if args.test_mode:
        cfg["test_mode"] = True
    if args.test_max_n is not None:
        cfg["test_max_n"] = args.test_max_n
    if args.ct_ids:
        cfg["test_mode"] = True
        cfg["test_ct_ids"] = [int(x) for x in args.ct_ids]
    if args.device:
        cfg["device"] = args.device
    if args.skip_existing:
        cfg["skip_existing"] = True
    if args.reprocess:
        cfg["skip_existing"] = False
        cfg["overwrite"] = False
    if args.overwrite:
        cfg["skip_existing"] = False
        cfg["overwrite"] = True
    if args.dry_run:
        cfg["dry_run"] = True


def _build_device_string(cfg: dict[str, Any]) -> str:
    import re
    device = str(cfg.get("device", "gpu")).strip().lower()
    # Normalize cuda:N → gpu:N so TotalSegmentator receives its expected format
    if device in {"cuda", "cuda:0"}:
        device = "gpu"
    else:
        m = re.fullmatch(r"cuda:(\d+)", device)
        if m:
            device = f"gpu:{m.group(1)}"
    device_id = cfg.get("device_id")
    if device_id is not None and ":" not in device:
        device = f"{device}:{device_id}"
    return device


# ── Series selection ──────────────────────────────────────────────────────────

def _load_series(cfg: dict[str, Any], retry_keys: set[tuple] | None = None) -> pd.DataFrame:
    df = pd.read_csv(cfg["csv_path"])
    df = df[df["status"] == "accepted"].copy()
    # Drop raw merge_source sub-series; keep merged_final (collapsed nii) and singles
    df = df[df["merge_status"] != "merged_source"].reset_index(drop=True)

    if retry_keys is not None:
        # Filter to exact (ct_id, series_folder) pairs that previously failed
        mask = df.apply(
            lambda r: (int(r["ct_id"]), str(r["series_folder"])) in retry_keys, axis=1
        )
        return df[mask].reset_index(drop=True)

    test_mode = cfg.get("test_mode", False)
    test_ids = cfg.get("test_ct_ids", [])
    test_max_n = cfg.get("test_max_n", 3)

    if test_mode:
        if test_ids:
            df = df[df["ct_id"].isin([int(i) for i in test_ids])].copy()
        else:
            df = df.head(int(test_max_n)).copy()

    return df.reset_index(drop=True)


def _load_failed_series(log_file: Path) -> set[tuple]:
    """Return (ct_id, series_folder) pairs whose most-recent log entry is 'failed'."""
    if not log_file.exists():
        return set()
    latest: dict[tuple, str] = {}
    with open(log_file) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (int(entry.get("ct_id", -1)), str(entry.get("series_folder", "")))
            latest[key] = entry.get("status", "")
    return {k for k, v in latest.items() if v == "failed"}


def _print_summary(log_file: Path) -> None:
    """Print a post-run summary of statuses from the log."""
    if not log_file.exists():
        print("Log file not found:", log_file)
        return

    # Most recent entry per series
    latest: dict[tuple, dict] = {}
    with open(log_file) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (int(entry.get("ct_id", -1)), str(entry.get("series_folder", "")))
            latest[key] = entry

    from collections import Counter
    counts: Counter = Counter(e["status"] for e in latest.values())
    total = sum(counts.values())
    print(f"\n{'─'*70}")
    print(f"  Run summary  ({log_file.name})")
    print(f"{'─'*70}")
    print(f"  Total series tracked : {total}")
    for status, n in sorted(counts.items()):
        print(f"  {status:<22}: {n}")

    failed = [e for e in latest.values() if e["status"] == "failed"]
    if failed:
        print(f"\n{'─'*70}")
        print(f"  FAILED series ({len(failed)})")
        print(f"{'─'*70}")
        for e in failed:
            print(f"  ct_id={e.get('ct_id'):<5} {e.get('ct_name','')}  /  {e.get('series_folder','')}")
            print(f"    error : {e.get('error','')}")
            tb = e.get("traceback", "")
            if tb:
                # Print last 3 lines of traceback for quick diagnosis
                lines = [l for l in tb.splitlines() if l.strip()]
                print(f"    trace : {chr(10).join('    ' + l for l in lines[-3:])}")
            print()
    print(f"{'─'*70}")
    print(f"  Re-run only failed:  python main.py --retry-failed")
    print(f"{'─'*70}\n")


# ── Per-series processing ─────────────────────────────────────────────────────

def _outputs_complete(series_dir: Path, expected_structures: list[str]) -> bool:
    if not (series_dir / "CT.nii.gz").exists():
        return False
    return all((series_dir / f"{s}.nii.gz").exists() for s in expected_structures)


def process_series(row: pd.Series, cfg: dict[str, Any], mapper: RoiMapper) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ct_id": row.get("ct_id"),
        "ct_name": row.get("ct_name"),
        "series_folder": row.get("series_folder"),
        "procedure_code": row.get("procedure_code_value"),
        "phase_name": row.get("phase_name"),
        "merge_status": row.get("merge_status"),
        "status": "ok",
        "converter": None,
        "structures_written": [],
        "error": None,
    }

    series_path = Path(str(row["series_path"]))
    series_name = str(row.get("series_name", ""))
    merge_status = str(row.get("merge_status", ""))
    procedure_code = str(row.get("procedure_code_value", ""))
    phase_name = str(row.get("phase_name", "") or "")

    # ── Resolve output directory ──────────────────────────────────────────────
    study_dir_name = series_path.parent.name        # "studyinstanceuid"
    ct_folder = str(row["ct_folder"])
    folder_name = output_folder_name(series_path, series_name, merge_status)
    output_root = Path(cfg["output_root"])
    series_dir = output_root / ct_folder / study_dir_name / folder_name
    result["output_dir"] = str(series_dir)

    # ── Determine structures ──────────────────────────────────────────────────
    structures = mapper.get_structures(procedure_code, phase_name)
    task_calls = build_task_calls(structures, licensed_enabled=cfg.get("licensed_tasks_enabled", True))
    result["structures_planned"] = structures

    # ── Skip check ────────────────────────────────────────────────────────────
    skip = cfg.get("skip_existing", True) and not cfg.get("overwrite", False)
    if skip and _outputs_complete(series_dir, structures):
        result["status"] = "skipped_existing"
        return result

    if cfg.get("dry_run", False):
        result["status"] = "dry_run"
        return result

    series_dir.mkdir(parents=True, exist_ok=True)
    ct_nii = series_dir / "CT.nii.gz"

    try:
        # ── Clean outputs when overwriting (CT rebuild is expensive; only drop if --overwrite) ──
        if cfg.get("overwrite", False):
            for p in series_dir.glob("*.nii.gz"):
                p.unlink(missing_ok=True)
            for p in series_dir.glob("*.json"):
                p.unlink(missing_ok=True)
            for p in series_dir.glob("*.png"):
                p.unlink(missing_ok=True)
        elif not cfg.get("skip_existing", True):  # --reprocess: keep CT, drop masks
            for p in series_dir.glob("*.nii.gz"):
                if p.name != "CT.nii.gz":
                    p.unlink(missing_ok=True)
            for p in series_dir.glob("*.json"):
                p.unlink(missing_ok=True)
            for p in series_dir.glob("*.png"):
                p.unlink(missing_ok=True)

        # ── CT.nii.gz ─────────────────────────────────────────────────────────
        if not ct_nii.exists():
            log.info("  → converting DICOM → CT.nii.gz  (%s slices)", row.get("instance_count", "?"))
            if merge_status == "merged_final":
                collapsed = find_collapsed_nifti(series_path, series_name)
                if collapsed is not None:
                    copy_nifti_as_ct(collapsed, ct_nii)
                    result["converter"] = "collapsed_nifti"
                    log.info("  → used pre-built collapsed nii.gz")
                else:
                    result["converter"] = convert_dicom_to_nifti(
                        series_path, ct_nii,
                        fallback_order=cfg.get("dicom_convert_fallback_order"),
                    )
                    log.info("  → conversion done via %s", result["converter"])
            else:
                result["converter"] = convert_dicom_to_nifti(
                    series_path, ct_nii,
                    fallback_order=cfg.get("dicom_convert_fallback_order"),
                )
                log.info("  → conversion done via %s", result["converter"])
        else:
            log.info("  → CT.nii.gz already exists, skipping conversion")

        # ── Phase prediction ──────────────────────────────────────────────────
        if cfg.get("save_phase_json", True):
            phase_json = series_dir / "phase.json"
            if not phase_json.exists():
                log.info("  → running phase prediction")
                try:
                    predict_phase(ct_nii, phase_json)
                except Exception as exc:
                    log.warning("  → phase prediction failed: %s", exc)

        # ── Segmentation ──────────────────────────────────────────────────────
        if task_calls:
            task_summary = ", ".join(f"{c.task}({c.output_structures})" for c in task_calls)
            log.info("  → segmenting: %s", task_summary)
            written = run_task_calls(
                ct_nii=ct_nii,
                series_out_dir=series_dir,
                task_calls=task_calls,
                device=_build_device_string(cfg),
                fast=cfg.get("fast_mode", True),
                body_seg=cfg.get("body_seg", True),
            )
            result["structures_written"] = written
            log.info("  → done: %s", written)
        else:
            log.info("  → no structures to segment for %s / %s", procedure_code, phase_name)

        # ── Sanity check PNG ──────────────────────────────────────────────────
        if cfg.get("save_sanity_png", True):
            try:
                save_sanity_check(ct_nii, series_dir, series_dir / "sanity_check.png",
                                  structures=structures)
            except Exception as exc:
                log.warning("  → sanity check failed: %s", exc)

    except Exception as exc:
        tb = traceback.format_exc()
        result["status"] = "failed"
        result["error"] = str(exc)
        result["traceback"] = tb
        log.error("FAILED %s: %s\n%s", series_dir, exc, tb)

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DICOM → NIfTI + TotalSegmentator pipeline")
    p.add_argument("--config", default=str(_SCRIPT_DIR / "config" / "defaults.yaml"))
    p.add_argument("--test-mode", action="store_true")
    p.add_argument("--test-max-n", type=int, default=None)
    p.add_argument("--ct-ids", nargs="+", help="Restrict to these ct_id values")
    p.add_argument("--device", default=None, help="Override device (gpu/cpu/gpu:0 ...)")
    p.add_argument("--skip-existing", action="store_true",
                    help="Skip series whose CT + masks already exist (overrides YAML)")
    p.add_argument("--reprocess", action="store_true",
                    help="Re-run segmentation on already-processed series (keeps existing CT.nii.gz)")
    p.add_argument("--overwrite", action="store_true",
                    help="Delete all outputs (including CT.nii.gz) and redo from scratch")
    p.add_argument("--dry-run", action="store_true", help="Print plan without running")
    p.add_argument("--summary", action="store_true",
                    help="Print a status summary from run_log.jsonl and exit")
    p.add_argument("--retry-failed", action="store_true",
                    help="Re-run only series whose most recent log entry is 'failed'")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    cfg = _load_config(Path(args.config))
    _apply_cli_overrides(cfg, args)

    log_file = Path(cfg.get("log_file", _SCRIPT_DIR / "run_log.jsonl"))

    if args.summary:
        _print_summary(log_file)
        return 0

    roi_table_path = _SCRIPT_DIR / "config" / "roi_table.yaml"
    mapper = RoiMapper(roi_table_path)

    retry_keys: set[tuple] | None = None
    if args.retry_failed:
        retry_keys = _load_failed_series(log_file)
        if not retry_keys:
            log.info("No failed series found in %s — nothing to retry.", log_file)
            return 0
        log.info("Retrying %d failed series.", len(retry_keys))

    df = _load_series(cfg, retry_keys=retry_keys)
    log.info("Series to process: %d  |  log → %s", len(df), log_file)

    if cfg.get("dry_run", False):
        log.info("── DRY RUN ── No files will be written.")
        for _, row in df.iterrows():
            code = str(row.get("procedure_code_value", ""))
            phase = str(row.get("phase_name", "") or "")
            structs = mapper.get_structures(code, phase)
            calls = build_task_calls(structs, licensed_enabled=cfg.get("licensed_tasks_enabled", True))
            task_summary = ", ".join(f"{c.task}({c.output_structures})" for c in calls)
            print(
                f"ct_id={row.get('ct_id'):>4}  "
                f"code={code:<8}  phase={phase:<12}  "
                f"merge={str(row.get('merge_status', '')):<14}  "
                f"tasks={task_summary or '(none)'}"
            )
        return 0

    # ── Set up file logger ────────────────────────────────────────────────────
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    log_jsonl = logging.getLogger("jsonl")
    log_jsonl.addHandler(file_handler)
    log_jsonl.setLevel(logging.INFO)
    log_jsonl.propagate = False

    ok = failed = skipped = 0
    for i, (_, row) in enumerate(df.iterrows(), 1):
        log.info("[%d/%d] ct_id=%-4s  %s / %s", i, len(df), row.get("ct_id"), row.get("ct_folder"), row.get("series_folder"))
        result = process_series(row, cfg, mapper)
        log_jsonl.info(json.dumps(result))

        if result["status"] == "ok":
            ok += 1
        elif result["status"] in ("skipped_existing",):
            skipped += 1
        elif result["status"] == "failed":
            failed += 1
            log.error("  → FAILED: %s", result["error"])

    log.info("Done — ok=%d  skipped=%d  failed=%d", ok, skipped, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

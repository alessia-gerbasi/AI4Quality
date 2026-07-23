from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = str(
    SCRIPT_DIR.parent
    / "_00_Preprocessing"
    / "OUTPUTS"
    / "selection_outputs_tacacp"
    / "retained_series_unified_filtered.csv"
)


@dataclass
class SeriesJob:
    ct_folder: str
    series_folder: str
    series_name: str
    series_path: Path
    output_series_dir: Path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create data_nii with TACACP embolia-only series listed in retained_series_unified_filtered.csv, "
            "convert each selected DICOM series to CT.nii.gz, and run TotalSegmentator v2 for "
            "pulmonary_artery, aorta, and skin."
        )
    )
    parser.add_argument(
        "--csv-path",
        default=DEFAULT_CSV,
        help="Path to retained_series_unified_filtered.csv",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help=(
            "Output root folder (default: <csv_parent>/data_nii). "
            "Structure created: <output_root>/<ct_folder>/<series_folder>/"
        ),
    )
    parser.add_argument(
        "--filter-keyword",
        default="embolia",
        help="Case-insensitive keyword used to keep only angio embolia series.",
    )
    parser.add_argument(
        "--device",
        default="gpu",
        help="TotalSegmentator device: gpu, cpu, mps, gpu:X, or cuda:X (cuda alias supported).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip a series if CT.nii.gz and all required masks already exist.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing CT and masks for each selected series.",
    )
    parser.add_argument(
        "--max-series",
        type=int,
        default=None,
        help="Optional cap on selected series count.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only resolve and report selected series without converting/segmenting.",
    )
    return parser


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _build_jobs(
    df: pd.DataFrame,
    keyword: str,
    output_root: Path,
    max_series: int | None,
) -> list[SeriesJob]:
    required_cols = {"ct_folder", "series_folder", "series_name", "series_path"}
    missing = sorted(required_cols - set(df.columns))
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    key = keyword.strip().lower()
    if not key:
        raise ValueError("--filter-keyword cannot be empty")

    selected = df[
        df["series_name"].astype(str).str.lower().str.contains(key, na=False)
        | df["series_folder"].astype(str).str.lower().str.contains(key, na=False)
    ].copy()

    selected = selected.drop_duplicates(subset=["ct_folder", "series_folder", "series_path"]).reset_index(drop=True)
    if max_series is not None:
        selected = selected.head(max_series)

    jobs: list[SeriesJob] = []
    for row in selected.itertuples(index=False):
        ct_folder = str(getattr(row, "ct_folder"))
        series_folder = str(getattr(row, "series_folder"))
        series_name = str(getattr(row, "series_name"))
        series_path = Path(str(getattr(row, "series_path"))).resolve()
        output_series_dir = output_root / ct_folder / series_folder
        jobs.append(
            SeriesJob(
                ct_folder=ct_folder,
                series_folder=series_folder,
                series_name=series_name,
                series_path=series_path,
                output_series_dir=output_series_dir,
            )
        )
    return jobs


def _find_first_nifti(folder: Path) -> Path | None:
    candidates = sorted(folder.glob("*.nii.gz")) + sorted(folder.glob("*.nii"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_size)


def _convert_with_dcm2niix(series_path: Path, out_nii: Path) -> None:
    if shutil.which("dcm2niix") is None:
        raise RuntimeError("dcm2niix not found on PATH")

    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            "dcm2niix",
            "-z",
            "y",
            "-o",
            tmp,
            "-f",
            "CT",
            str(series_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                "dcm2niix failed: "
                f"returncode={proc.returncode}; stderr={proc.stderr.strip()}"
            )
        generated = _find_first_nifti(Path(tmp))
        if generated is None:
            raise RuntimeError("dcm2niix did not produce any NIfTI file")
        shutil.copy2(generated, out_nii)


def _convert_with_dicom2nifti(series_path: Path, out_nii: Path) -> None:
    try:
        import dicom2nifti  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "dicom2nifti is not available in this environment"
        ) from exc

    with tempfile.TemporaryDirectory() as tmp:
        dicom2nifti.convert_directory(
            str(series_path),
            tmp,
            compression=True,
            reorient=True,
        )
        generated = _find_first_nifti(Path(tmp))
        if generated is None:
            raise RuntimeError("dicom2nifti did not produce any NIfTI file")
        shutil.copy2(generated, out_nii)


def _convert_with_simpleitk(series_path: Path, out_nii: Path) -> None:
    try:
        import SimpleITK as sitk  # type: ignore
    except Exception as exc:
        raise RuntimeError("SimpleITK is not available in this environment") from exc

    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(str(series_path))
    if not dicom_names:
        raise RuntimeError(f"SimpleITK found no readable DICOM slices in {series_path}")

    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    sitk.WriteImage(image, str(out_nii), useCompression=True)


def _validate_nifti(out_nii: Path) -> None:
    try:
        import nibabel as nib  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("nibabel/numpy are required to validate converted NIfTI") from exc

    if not out_nii.exists() or out_nii.stat().st_size == 0:
        raise RuntimeError(f"Output NIfTI missing or empty: {out_nii}")

    img = nib.load(str(out_nii))
    data = img.get_fdata(dtype=np.float32)
    finite = np.isfinite(data)
    if not finite.any():
        raise RuntimeError("Converted NIfTI has no finite voxel values")

    vox = data[finite]
    if float(np.max(vox) - np.min(vox)) <= 0.0:
        raise RuntimeError("Converted NIfTI appears constant (invalid intensity range)")


def convert_dicom_series_to_nifti(series_path: Path, out_nii: Path) -> str:
    out_nii.parent.mkdir(parents=True, exist_ok=True)

    attempts: list[str] = []
    converters = [
        ("dcm2niix", _convert_with_dcm2niix),
        ("dicom2nifti", _convert_with_dicom2nifti),
        ("simpleitk", _convert_with_simpleitk),
    ]

    for name, fn in converters:
        try:
            if out_nii.exists():
                out_nii.unlink()
            fn(series_path, out_nii)
            _validate_nifti(out_nii)
            return name
        except Exception as exc:
            attempts.append(f"{name}_error={exc}")

    raise RuntimeError("All DICOM->NIfTI converters failed. " + "; ".join(attempts))


def _copy_mask(src: Path, dst: Path, missing_label_msg: str) -> None:
    if not src.exists():
        raise RuntimeError(missing_label_msg)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _assert_exists(path: Path, err_msg: str) -> None:
    if not path.exists():
        raise RuntimeError(err_msg)


def run_totalsegmentator_v2(nii_path: Path, seg_out_dir: Path, device: str) -> None:
    try:
        from totalsegmentator.python_api import totalsegmentator  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "TotalSegmentator is not available in this environment"
        ) from exc

    seg_out_dir.mkdir(parents=True, exist_ok=True)

    # aorta + pulmonary_artery using v2 task heartchambers_highres.
    totalsegmentator(
        str(nii_path),
        str(seg_out_dir),
        task="heartchambers_highres",
        device=device,
    )

    # skin proxy from body mask. TotalSegmentator does not expose a direct skin class,
    # so body_trunc is exported and saved as skin.nii.gz.
    with tempfile.TemporaryDirectory() as tmp:
        body_dir = Path(tmp) / "body"
        totalsegmentator(
            str(nii_path),
            str(body_dir),
            task="body",
            device=device,
        )
        _copy_mask(
            body_dir / "body_trunc.nii.gz",
            seg_out_dir / "skin.nii.gz",
            "TotalSegmentator body task did not produce body_trunc.nii.gz",
        )

    _assert_exists(
        seg_out_dir / "aorta.nii.gz",
        "TotalSegmentator heartchambers_highres did not produce aorta.nii.gz",
    )
    _assert_exists(
        seg_out_dir / "pulmonary_artery.nii.gz",
        "TotalSegmentator heartchambers_highres did not produce pulmonary_artery.nii.gz",
    )


def _outputs_exist(series_dir: Path) -> bool:
    ct = series_dir / "CT.nii.gz"
    seg = series_dir / "segmentations"
    req = [
        ct,
        seg / "aorta.nii.gz",
        seg / "pulmonary_artery.nii.gz",
        seg / "skin.nii.gz",
    ]
    return all(p.exists() for p in req)


def normalize_device(device: str) -> str:
    value = device.strip().lower()
    if value in {"cuda", "cuda:0"}:
        return "gpu"
    match = re.fullmatch(r"cuda:(\d+)", value)
    if match:
        return f"gpu:{match.group(1)}"
    return value


def process_job(job: SeriesJob, device: str, overwrite: bool, skip_existing: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ct_folder": job.ct_folder,
        "series_folder": job.series_folder,
        "series_name": job.series_name,
        "series_path": str(job.series_path),
        "output_series_dir": str(job.output_series_dir),
        "status": "ok",
        "conversion_engine": None,
        "error": None,
    }

    if not job.series_path.exists():
        result["status"] = "failed"
        result["error"] = f"Series path not found: {job.series_path}"
        return result

    if skip_existing and _outputs_exist(job.output_series_dir):
        result["status"] = "skipped_existing"
        return result

    job.output_series_dir.mkdir(parents=True, exist_ok=True)
    ct_nii = job.output_series_dir / "CT.nii.gz"
    seg_dir = job.output_series_dir / "segmentations"

    try:
        if overwrite:
            if ct_nii.exists():
                ct_nii.unlink()
            if seg_dir.exists():
                shutil.rmtree(seg_dir)

        if not ct_nii.exists():
            engine = convert_dicom_series_to_nifti(job.series_path, ct_nii)
            result["conversion_engine"] = engine

        run_totalsegmentator_v2(ct_nii, seg_dir, device=device)

    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)

    return result


def main() -> int:
    args = build_arg_parser().parse_args()

    csv_path = Path(args.csv_path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    output_root = Path(args.output_root).resolve() if args.output_root else (csv_path.parent / "data_nii").resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    device = normalize_device(args.device)

    df = pd.read_csv(csv_path)
    jobs = _build_jobs(
        df=df,
        keyword=args.filter_keyword,
        output_root=output_root,
        max_series=args.max_series,
    )

    summary_path = output_root / "export_summary.json"
    report_path = output_root / "export_report.csv"

    print(f"[INFO] CSV: {csv_path}")
    print(f"[INFO] Output root: {output_root}")
    print(f"[INFO] Device: {device}")
    print(f"[INFO] Selected series (keyword={args.filter_keyword!r}): {len(jobs)}")

    if args.dry_run:
        summary = {
            "csv_path": str(csv_path),
            "output_root": str(output_root),
            "selected_count": len(jobs),
            "dry_run": True,
            "selected_examples": [
                {
                    "ct_folder": j.ct_folder,
                    "series_folder": j.series_folder,
                    "series_name": j.series_name,
                    "series_path": str(j.series_path),
                    "output_series_dir": str(j.output_series_dir),
                }
                for j in jobs[:10]
            ],
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[INFO] Dry-run summary saved: {summary_path}")
        return 0

    results: list[dict[str, Any]] = []
    for idx, job in enumerate(jobs, start=1):
        print(f"[{idx}/{len(jobs)}] {job.ct_folder} | {job.series_folder}")
        res = process_job(
            job,
            device=device,
            overwrite=bool(args.overwrite),
            skip_existing=bool(args.skip_existing),
        )
        if res["status"] == "failed":
            print(f"  [ERROR] {res['error']}")
        elif res["status"] == "skipped_existing":
            print("  [SKIP] outputs already present")
        else:
            print("  [OK] CT and segmentations created")
        results.append(res)

    report_df = pd.DataFrame(results)
    report_df.to_csv(report_path, index=False)

    failed = int((report_df["status"] == "failed").sum()) if not report_df.empty else 0
    skipped = int((report_df["status"] == "skipped_existing").sum()) if not report_df.empty else 0
    ok = int((report_df["status"] == "ok").sum()) if not report_df.empty else 0

    summary = {
        "csv_path": str(csv_path),
        "output_root": str(output_root),
        "selected_count": len(jobs),
        "ok": ok,
        "skipped_existing": skipped,
        "failed": failed,
        "report_csv": str(report_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("[DONE] Export completed")
    print(json.dumps(summary, indent=2))

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

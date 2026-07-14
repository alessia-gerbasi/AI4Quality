from __future__ import annotations

from pathlib import Path
from typing import Any

import pydicom
import SimpleITK as sitk


def _sanitize_filename(name: str) -> str:
    value = (name or "series").strip()
    value = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value)
    value = "_".join(part for part in value.split("_") if part)
    return value or "series"


def _iter_dicom_files(series_dir: Path) -> list[Path]:
    return sorted(p for p in series_dir.rglob("*") if p.is_file())


def _slice_sort_key(ds: pydicom.dataset.FileDataset, idx: int) -> tuple[float, float, int]:
    ipp = getattr(ds, "ImagePositionPatient", None)
    if ipp is not None:
        try:
            return (0.0, float(ipp[2]), idx)
        except Exception:
            pass

    inst = getattr(ds, "InstanceNumber", None)
    if inst is not None:
        try:
            return (1.0, float(inst), idx)
        except Exception:
            pass

    return (2.0, float(idx), idx)


def _load_sorted_dicom_paths(series_dir: Path) -> list[str]:
    loaded: list[tuple[Path, tuple[float, float, int]]] = []
    for idx, fp in enumerate(_iter_dicom_files(series_dir)):
        try:
            ds = pydicom.dcmread(
                str(fp),
                stop_before_pixels=True,
                force=True,
                specific_tags=["ImagePositionPatient", "InstanceNumber"],
            )
        except Exception:
            continue
        loaded.append((fp, _slice_sort_key(ds, idx)))

    loaded.sort(key=lambda item: item[1])
    return [str(path) for path, _ in loaded]


def _write_nifti_from_dicom_paths(sorted_dicom_paths: list[str], out_path: Path) -> None:
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(sorted_dicom_paths)
    image = reader.Execute()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(image, str(out_path), useCompression=True)


def write_collapsed_volumes(
    decision_rows: list[dict[str, Any]],
    enabled: bool = True,
    only_accepted: bool = True,
    skip_existing: bool = True,
    include_ct_ids: set[str] | None = None,
    max_groups: int | None = None,
) -> dict[str, Any]:
    report = {
        "enabled": bool(enabled),
        "groups_detected": 0,
        "groups_considered": 0,
        "volumes_written": 0,
        "volumes_skipped_existing": 0,
        "errors": [],
        "written_files": [],
    }
    if not enabled:
        return report

    merged_rows = [row for row in decision_rows if str(row.get("merge_status", "")) == "merged_source"]
    if only_accepted:
        merged_rows = [row for row in merged_rows if str(row.get("status", "")) == "accepted"]

    if include_ct_ids:
        normalized = {str(ct_id).strip() for ct_id in include_ct_ids if str(ct_id).strip()}
        merged_rows = [row for row in merged_rows if str(row.get("ct_id", "")).strip() in normalized]

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in merged_rows:
        gid = str(row.get("merge_group_id") or "").strip()
        if not gid:
            continue
        groups.setdefault(gid, []).append(row)

    report["groups_detected"] = len(groups)
    group_items = list(groups.items())
    if max_groups is not None and max_groups > 0:
        group_items = group_items[:max_groups]
    report["groups_considered"] = len(group_items)

    for gid, rows in group_items:
        try:
            rows_sorted = sorted(rows, key=lambda r: (int(r.get("merge_part_index") or 0), str(r.get("series_folder") or "")))
            first = rows_sorted[0]
            series_name = str(first.get("series_name") or "series")
            parent_dir = Path(str(first.get("series_path"))).parent
            out_name = f"{_sanitize_filename(series_name)}_collapsed.nii.gz"
            out_path = parent_dir / out_name

            if skip_existing and out_path.exists():
                report["volumes_skipped_existing"] += 1
                continue

            all_sorted_dicom_paths: list[str] = []
            for row in rows_sorted:
                series_dir = Path(str(row.get("series_path")))
                all_sorted_dicom_paths.extend(_load_sorted_dicom_paths(series_dir))

            if not all_sorted_dicom_paths:
                report["errors"].append({"merge_group_id": gid, "error": "no_readable_pixel_data"})
                continue

            _write_nifti_from_dicom_paths(all_sorted_dicom_paths, out_path)

            report["volumes_written"] += 1
            report["written_files"].append(str(out_path))
        except Exception as exc:
            report["errors"].append({"merge_group_id": gid, "error": str(exc)})

    return report

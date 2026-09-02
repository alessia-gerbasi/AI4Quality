from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pydicom

from domain.models import SeriesRecord


def _parse_dicom_time_to_seconds(value: object) -> float | None:
    """Parse a DICOM TM value (HHMMSS.ffffff) into seconds since midnight."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        raw = float(text)
    except ValueError:
        return None
    hhmmss = int(raw)
    frac = raw - hhmmss
    hh, mm, ss = hhmmss // 10000, (hhmmss % 10000) // 100, hhmmss % 100
    if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60):
        return None
    return hh * 3600 + mm * 60 + ss + frac


def _compute_scan_duration_seconds(dicom_files: list[Path], max_samples: int = 3) -> float | None:
    """Estimate total scan acquisition duration from the spread of per-slice AcquisitionTime.

    Sampling (instead of reading every file) keeps this cheap for series with hundreds of
    slices; files are acquired in filename/instance order so the first/last samples bound the range.
    """
    ordered = sorted(dicom_files)
    if len(ordered) > max_samples:
        step = (len(ordered) - 1) / (max_samples - 1)
        ordered = [ordered[round(i * step)] for i in range(max_samples)]

    times: list[float] = []
    for fp in ordered:
        try:
            ds = pydicom.dcmread(
                str(fp),
                stop_before_pixels=True,
                force=True,
                specific_tags=["AcquisitionTime"],
            )
        except Exception:
            continue
        seconds = _parse_dicom_time_to_seconds(getattr(ds, "AcquisitionTime", None))
        if seconds is not None:
            times.append(seconds)

    if len(times) < 2:
        return None
    return max(times) - min(times)


def _safe_first_dicom(dicom_files: list[Path]) -> tuple[dict, list[str], int]:
    issues: list[str] = []

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
                    "ContrastBolusStartTime",
                    "KVP",
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
        "ContrastBolusStartTime": str(getattr(dataset, "ContrastBolusStartTime", "") or "") or None,
        "KVP": str(getattr(dataset, "KVP", "") or "") or None,
        "SeriesInstanceUID": None,
    }, sorted(set(issues)), count


def resolve_series_instance_uid(series_path: str | Path) -> str | None:
    path = Path(series_path)
    dicom_files = [p for p in path.rglob("*") if p.is_file()]

    for fp in dicom_files:
        try:
            ds = pydicom.dcmread(
                str(fp),
                stop_before_pixels=True,
                force=True,
                specific_tags=["SeriesInstanceUID"],
            )
        except Exception:
            continue

        series_instance_uid = str(getattr(ds, "SeriesInstanceUID", "") or "").strip()
        if series_instance_uid:
            return series_instance_uid

    return None


def _iter_ct_folders(dicom_roots: Iterable[str]) -> Iterable[Path]:
    for root in dicom_roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        if root_path.name.startswith("CT_QUALITY_"):
            yield root_path
            continue
        for child in sorted(root_path.iterdir()):
            if child.is_dir() and child.name.startswith("CT_QUALITY_"):
                yield child


def scan_series(dicom_roots: list[str], max_ct: int | None = None) -> list[SeriesRecord]:
    records: list[SeriesRecord] = []
    ct_seen = 0

    for ct_folder in _iter_ct_folders(dicom_roots):
        ct_seen += 1
        if max_ct is not None and ct_seen > max_ct:
            break

        study_wrapper = ct_folder / "studyinstanceuid"
        if not study_wrapper.exists() or not study_wrapper.is_dir():
            continue

        for series_dir in sorted(study_wrapper.iterdir()):
            if not series_dir.is_dir():
                continue
            dicom_files = [p for p in series_dir.rglob("*") if p.is_file()]
            header, issues, count = _safe_first_dicom(dicom_files)
            series_name = header.get("SeriesDescription") or series_dir.name
            record = SeriesRecord(
                ct_folder=ct_folder.name,
                study_folder=study_wrapper.name,
                series_folder=series_dir.name,
                series_path=str(series_dir),
                series_name=series_name,
                body_part_examined=header.get("BodyPartExamined"),
                acquisition_time=header.get("AcquisitionTime"),
                contrast_bolus_start=header.get("ContrastBolusStartTime"),
                kvp=header.get("KVP"),
                scan_duration_s=_compute_scan_duration_seconds(dicom_files),
                series_description=header.get("SeriesDescription"),
                series_instance_uid=header.get("SeriesInstanceUID"),
                instance_count=count,
                metadata_issues=issues,
            )
            records.append(record)

    return records

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pydicom

from domain.models import SeriesRecord


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
                    "ContrastBolusStartTime",
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
            header, issues, count = _safe_first_dicom(series_dir)
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
                series_description=header.get("SeriesDescription"),
                series_instance_uid=header.get("SeriesInstanceUID"),
                instance_count=count,
                metadata_issues=issues,
            )
            records.append(record)

    return records

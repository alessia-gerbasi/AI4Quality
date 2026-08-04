from __future__ import annotations

from pathlib import Path


def _sanitize_filename(name: str) -> str:
    """Mirror of collapsed_volume_writer._sanitize_filename to reconstruct nii.gz names."""
    value = (name or "series").strip()
    value = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value)
    value = "_".join(part for part in value.split("_") if part)
    return value or "series"


def find_collapsed_nifti(series_path: Path, series_name: str) -> Path | None:
    """Return the pre-built collapsed nii.gz for a merged series, or None."""
    study_dir = series_path.parent
    expected_name = f"{_sanitize_filename(series_name)}_collapsed.nii.gz"
    candidate = study_dir / expected_name
    if candidate.exists():
        return candidate

    # Fallback: any *_collapsed.nii.gz whose stem matches the sanitized series name prefix
    sanitized = _sanitize_filename(series_name)
    for p in study_dir.glob("*_collapsed.nii.gz"):
        if p.stem.replace("_collapsed", "") == sanitized:
            return p

    return None


def output_folder_name(series_path: Path, series_name: str, merge_status: str) -> str:
    """Return the folder name to use under studyinstanceuid/ in 2_nii."""
    if merge_status == "merged_final":
        stem = f"{_sanitize_filename(series_name)}_collapsed"
        return stem
    return series_path.name

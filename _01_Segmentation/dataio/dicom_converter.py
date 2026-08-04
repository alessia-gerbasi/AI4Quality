from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def _find_largest_nifti(folder: Path) -> Path | None:
    candidates = sorted(folder.glob("*.nii.gz")) + sorted(folder.glob("*.nii"))
    return max(candidates, key=lambda p: p.stat().st_size) if candidates else None


def _convert_with_dcm2niix(series_path: Path, out_nii: Path) -> None:
    if shutil.which("dcm2niix") is None:
        raise RuntimeError("dcm2niix not found on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            ["dcm2niix", "-z", "y", "-o", tmp, "-f", "CT", str(series_path)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"dcm2niix failed: {proc.stderr.strip()}")
        nii = _find_largest_nifti(Path(tmp))
        if nii is None:
            raise RuntimeError("dcm2niix produced no NIfTI file")
        shutil.copy2(nii, out_nii)


def _convert_with_dicom2nifti(series_path: Path, out_nii: Path) -> None:
    try:
        import dicom2nifti  # type: ignore
    except ImportError as exc:
        raise RuntimeError("dicom2nifti not available") from exc
    with tempfile.TemporaryDirectory() as tmp:
        dicom2nifti.convert_directory(str(series_path), tmp, compression=True, reorient=True)
        nii = _find_largest_nifti(Path(tmp))
        if nii is None:
            raise RuntimeError("dicom2nifti produced no NIfTI file")
        shutil.copy2(nii, out_nii)


def _convert_with_simpleitk(series_path: Path, out_nii: Path) -> None:
    try:
        import SimpleITK as sitk  # type: ignore
    except ImportError as exc:
        raise RuntimeError("SimpleITK not available") from exc
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(str(series_path))
    if not dicom_names:
        raise RuntimeError(f"SimpleITK found no DICOM slices in {series_path}")
    reader.SetFileNames(dicom_names)
    sitk.WriteImage(reader.Execute(), str(out_nii), useCompression=True)


def _validate_nifti(path: Path) -> None:
    import nibabel as nib  # type: ignore
    import numpy as np  # type: ignore

    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"NIfTI missing or empty: {path}")
    data = nib.load(str(path)).get_fdata(dtype=np.float32)
    finite = np.isfinite(data)
    if not finite.any():
        raise RuntimeError("NIfTI has no finite voxels")
    if float(data[finite].max() - data[finite].min()) <= 0.0:
        raise RuntimeError("NIfTI appears constant")


_CONVERTERS = {
    "dcm2niix": _convert_with_dcm2niix,
    "dicom2nifti": _convert_with_dicom2nifti,
    "simpleitk": _convert_with_simpleitk,
}


def convert_dicom_to_nifti(
    series_path: Path,
    out_nii: Path,
    fallback_order: list[str] | None = None,
) -> str:
    """Convert DICOM series to CT.nii.gz; returns name of converter used."""
    out_nii.parent.mkdir(parents=True, exist_ok=True)
    order = fallback_order or ["dcm2niix", "dicom2nifti", "simpleitk"]
    errors: list[str] = []
    for name in order:
        fn = _CONVERTERS.get(name)
        if fn is None:
            continue
        try:
            if out_nii.exists():
                out_nii.unlink()
            fn(series_path, out_nii)
            _validate_nifti(out_nii)
            return name
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError("All converters failed — " + "; ".join(errors))


def copy_nifti_as_ct(src: Path, out_nii: Path) -> None:
    """Copy a pre-built collapsed nii.gz as CT.nii.gz without re-converting."""
    out_nii.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out_nii)

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np


def load_nifti_array(path: Path) -> np.ndarray:
    data = nib.load(str(path)).get_fdata(dtype=np.float32)
    return np.asarray(data, dtype=np.float32)


def measure_roi_statistics(ct_volume: np.ndarray, roi_mask: np.ndarray) -> tuple[float | None, float | None, float | None, int]:
    mask = roi_mask > 0
    n_vox = int(mask.sum())
    if n_vox == 0:
        return None, None, None, 0
    values = ct_volume[mask]
    mean_hu = float(values.mean())
    std_hu = float(values.std(ddof=0))
    median_hu = float(np.median(values))
    return mean_hu, std_hu, median_hu, n_vox


def measure_roi_edge_means(
    ct_volume: np.ndarray,
    roi_mask: np.ndarray,
    n_slices: int = 5,
) -> tuple[float | None, float | None]:
    if n_slices < 1:
        raise ValueError("n_slices must be at least 1")

    mask = roi_mask > 0
    populated_slices = np.flatnonzero(mask.any(axis=(0, 1)))
    if populated_slices.size == 0:
        return None, None

    proximal_slices = populated_slices[:n_slices]
    distal_slices = populated_slices[-n_slices:]
    proximal_mask = mask[:, :, proximal_slices]
    distal_mask = mask[:, :, distal_slices]
    proximal_mean = float(ct_volume[:, :, proximal_slices][proximal_mask].mean())
    distal_mean = float(ct_volume[:, :, distal_slices][distal_mask].mean())
    return proximal_mean, distal_mean


def select_slice_for_visualization(roi_mask: np.ndarray) -> int | None:
    mask = roi_mask > 0
    if not mask.any():
        return None
    z_counts = mask.sum(axis=(0, 1))
    return int(np.argmax(z_counts))


def build_roi_border(roi_slice_mask: np.ndarray) -> np.ndarray:
    m = roi_slice_mask.astype(bool)
    if not m.any():
        return np.zeros_like(m, dtype=bool)

    eroded = m.copy()
    eroded[:-1, :] &= m[1:, :]
    eroded[1:, :] &= m[:-1, :]
    eroded[:, :-1] &= m[:, 1:]
    eroded[:, 1:] &= m[:, :-1]

    border = m & ~eroded
    return border

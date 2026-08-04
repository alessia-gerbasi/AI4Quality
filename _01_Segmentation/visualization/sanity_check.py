from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np


def _load_volume(path: Path) -> np.ndarray:
    vol = nib.load(str(path)).get_fdata(dtype=np.float32)
    return vol[..., 0] if vol.ndim == 4 else vol


def _best_axial_slice(mask: np.ndarray) -> int:
    """Return the axial index with the most foreground voxels."""
    counts = mask.astype(bool).sum(axis=(0, 1))
    best = int(counts.argmax())
    # Fall back to middle if mask is empty
    return best if counts[best] > 0 else mask.shape[2] // 2


def _window_ct(arr: np.ndarray, wl: float = 60.0, ww: float = 400.0) -> np.ndarray:
    lo, hi = wl - ww / 2, wl + ww / 2
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0)


def save_sanity_check(
    ct_nii: Path,
    seg_dir: Path,
    out_png: Path,
    structures: list[str] | None = None,
    wl: float = 60.0,
    ww: float = 400.0,
) -> None:
    """Save a PNG with per-structure panels, each on its own best axial slice."""
    ct_vol = _load_volume(ct_nii)

    # Restrict to explicitly requested structures only
    if structures:
        seg_files = [seg_dir / f"{s}.nii.gz" for s in structures
                     if (seg_dir / f"{s}.nii.gz").exists()]
    else:
        seg_files = sorted(seg_dir.glob("*.nii.gz"))

    n_segs = len(seg_files)
    n_cols = max(1, n_segs + 1)          # +1 for the plain CT panel
    fig, axes = plt.subplots(1, n_cols, figsize=(4 * n_cols, 4))
    if n_cols == 1:
        axes = [axes]

    # Left panel: CT at the slice best covering the first (or only) structure
    if seg_files:
        first_mask = _load_volume(seg_files[0])
        ref_slice = _best_axial_slice(first_mask)
    else:
        ref_slice = ct_vol.shape[2] // 2

    axes[0].imshow(_window_ct(ct_vol[:, :, ref_slice].T, wl, ww), cmap="gray", origin="lower")
    axes[0].set_title("CT", fontsize=9)
    axes[0].axis("off")

    cmap = plt.get_cmap("tab10")
    for i, seg_path in enumerate(seg_files):
        mask = _load_volume(seg_path)
        best = _best_axial_slice(mask)

        ax = axes[i + 1]
        ax.imshow(_window_ct(ct_vol[:, :, best].T, wl, ww), cmap="gray", origin="lower")
        contour_mask = (mask[:, :, best] > 0).astype(np.uint8)
        if contour_mask.any():
            ax.contour(contour_mask.T, levels=[0.5], colors=[cmap(i % 10)], linewidths=1.5)
        ax.set_title(seg_path.stem.replace(".nii", ""), fontsize=8)
        ax.axis("off")

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_png), dpi=120, bbox_inches="tight")
    plt.close(fig)


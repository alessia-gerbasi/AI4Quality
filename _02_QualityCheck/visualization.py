from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .hu_metrics import build_roi_border
from .models import RoiMeasurement, ScoreResult, ThresholdBand


STATUS_COLORS = {
    "optimal": "#0f5132",
    "acceptable_low": "#67b56e",
    "acceptable_high": "#67b56e",
    "critical_low": "#c1121f",
    "critical_high": "#f48c06",
    "not_evaluated": "#6c757d",
    "missing": "#6c757d",
}


def _window_image(slice_data: np.ndarray, center: float = 50.0, width: float = 400.0) -> np.ndarray:
    lo = center - width / 2.0
    hi = center + width / 2.0
    clipped = np.clip(slice_data, lo, hi)
    scaled = (clipped - lo) / max(width, 1e-6)
    return scaled


def _draw_gauge(ax, value: float | None, threshold: ThresholdBand | None, title: str, status: str):
    ax.set_aspect("equal")
    ax.axis("off")

    if threshold is None:
        ax.text(0.5, 0.5, "No thresholds", ha="center", va="center", fontsize=10)
        ax.set_title(title, fontsize=10)
        return

    start, stop = 180.0, 0.0

    span = max(threshold.max_with_threshold - threshold.min_with_threshold, 1e-6)
    pad = max(span * 0.25, 1.0)
    display_min = threshold.min_with_threshold - pad
    display_max = threshold.max_with_threshold + pad

    angles = np.linspace(np.deg2rad(start), np.deg2rad(stop), 400)

    def color_for_v(v: float) -> str:
        if v < threshold.min_with_threshold:
            return "#c1121f"
        if v < threshold.min_opt:
            return "#67b56e"
        if v <= threshold.max_opt:
            return "#0f5132"
        if v <= threshold.max_with_threshold:
            return "#67b56e"
        return "#f48c06"

    vals = np.linspace(display_min, display_max, len(angles))

    for i in range(len(angles) - 1):
        a0 = angles[i]
        a1 = angles[i + 1]
        x = [np.cos(a0), np.cos(a1)]
        y = [np.sin(a0), np.sin(a1)]
        ax.plot(x, y, color=color_for_v(vals[i]), linewidth=10, solid_capstyle="butt")

    if value is not None:
        clamped = float(np.clip(value, display_min, display_max))
        ratio = (clamped - display_min) / max(display_max - display_min, 1e-6)
        theta = np.deg2rad(start + (stop - start) * ratio)
        ax.plot([0, 0.85 * np.cos(theta)], [0, 0.85 * np.sin(theta)], color="black", linewidth=2)
        ax.scatter([0], [0], c="black", s=25)

    color = STATUS_COLORS.get(status, "#6c757d")
    value_txt = "n/a" if value is None else f"{value:.1f}"
    ax.text(0, -0.2, value_txt, ha="center", va="center", fontsize=11, color=color, fontweight="bold")
    if status in {"critical_low", "critical_high", "missing"}:
        warning_text = {
            "critical_low": "Warning: below threshold",
            "critical_high": "Warning: above threshold",
            "missing": "Warning: missing ROI",
        }[status]
        ax.text(0, -0.35, warning_text, ha="center", va="center", fontsize=9, color=color)
    ax.set_title(title, fontsize=10)


def render_series_qc_image(
    ct_volume: np.ndarray,
    roi_masks: dict[str, np.ndarray],
    measurements: list[RoiMeasurement],
    scores: dict[str, ScoreResult],
    threshold: ThresholdBand | None,
    output_path: Path,
    title: str,
    series_warnings: list[str] | None = None,
) -> None:
    n = max(len(measurements), 1)
    fig, axes = plt.subplots(nrows=n, ncols=2, figsize=(10, 4.5 * n))
    if n == 1:
        axes = np.array([axes])

    for row_idx, m in enumerate(measurements):
        ax_img = axes[row_idx, 0]
        ax_gauge = axes[row_idx, 1]
        mask = roi_masks.get(m.roi_name)

        if mask is None or m.slice_index is None:
            ax_img.text(0.5, 0.5, f"Missing ROI {m.roi_name}", ha="center", va="center")
            ax_img.axis("off")
            _draw_gauge(ax_gauge, None, threshold, m.roi_name, "missing")
            continue

        ct_slice = ct_volume[:, :, m.slice_index]
        mask_slice = mask[:, :, m.slice_index] > 0
        border = build_roi_border(mask_slice)

        ax_img.imshow(_window_image(ct_slice).T, cmap="gray", origin="lower")
        yy, xx = np.where(border.T)
        if len(xx) > 0:
            ax_img.scatter(xx, yy, s=1.0, c="#ff2d55")

        ax_img.set_title(f"{m.roi_name} | slice {m.slice_index}")
        ax_img.axis("off")

        score = scores.get(m.roi_name)
        _draw_gauge(
            ax=ax_gauge,
            value=score.value if score else None,
            threshold=threshold,
            title=f"{m.roi_name} quality",
            status=score.status if score else "missing",
        )

    fig.suptitle(title, fontsize=13)
    if series_warnings:
        warning_text = " | ".join(series_warnings)
        fig.text(0.5, 0.015, warning_text, ha="center", va="bottom", fontsize=9, color="#a61e1e", wrap=True)
        fig.tight_layout(rect=(0, 0.04, 1, 0.98))
    else:
        fig.tight_layout(rect=(0, 0.02, 1, 0.98))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ThresholdBand:
    min_opt: float
    max_opt: float
    min_with_threshold: float
    max_with_threshold: float

    @classmethod
    def from_list(cls, values: list[float] | tuple[float, ...] | None) -> "ThresholdBand | None":
        if not values:
            return None
        if len(values) < 2:
            raise ValueError(f"Threshold list must have at least 2 values, got {values}")

        min_opt = float(values[0])
        max_opt = float(values[1])
        min_with_threshold = float(values[2]) if len(values) >= 3 else min_opt
        max_with_threshold = float(values[3]) if len(values) >= 4 else max_opt

        return cls(
            min_opt=min_opt,
            max_opt=max_opt,
            min_with_threshold=min_with_threshold,
            max_with_threshold=max_with_threshold,
        )


@dataclass(frozen=True)
class PhaseRule:
    rois: list[str] = field(default_factory=list)
    hu_threshold: ThresholdBand | None = None
    hu_delta_threshold: ThresholdBand | None = None


@dataclass(frozen=True)
class ProcedureRule:
    procedure_code: str
    phases: dict[str, PhaseRule]


@dataclass
class RoiMeasurement:
    roi_name: str
    mean_hu: float | None = None
    std_hu: float | None = None
    median_hu: float | None = None
    median_std_hu: float | None = None
    voxel_count: int = 0
    slice_index: int | None = None
    mean_hu_precontrast: float | None = None
    std_hu_precontrast: float | None = None
    median_hu_precontrast: float | None = None
    median_std_hu_precontrast: float | None = None
    delta_hu: float | None = None
    delta_median_hu: float | None = None


@dataclass
class ScoreResult:
    value: float | None
    status: str
    label: str
    warning: str | None


@dataclass
class SeriesEvaluation:
    ct_id: int
    ct_name: str
    ct_folder: str
    ct_type: str
    procedure_code: str
    phase_name: str
    series_folder: str
    series_dir: str
    reference_series_folder: str | None
    metric_name: str
    threshold: ThresholdBand | None
    measurements: list[RoiMeasurement]
    scores: dict[str, ScoreResult]
    warnings: list[str]
    output_image_path: str | None = None

    def to_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for m in self.measurements:
            score = self.scores.get(m.roi_name)
            rows.append(
                {
                    "ct_id": self.ct_id,
                    "ct_name": self.ct_name,
                    "ct_folder": self.ct_folder,
                    "CT_type": self.ct_type,
                    "procedure_code": self.procedure_code,
                    "phase_name": self.phase_name,
                    "series_folder": self.series_folder,
                    "reference_series_folder": self.reference_series_folder,
                    "metric_name": self.metric_name,
                    "roi_name": m.roi_name,
                    "mean_hu": m.mean_hu,
                    "std_hu": m.std_hu,
                    "median_hu": m.median_hu,
                    "median_std_hu": m.median_std_hu,
                    "mean_hu_precontrast": m.mean_hu_precontrast,
                    "std_hu_precontrast": m.std_hu_precontrast,
                    "median_hu_precontrast": m.median_hu_precontrast,
                    "median_std_hu_precontrast": m.median_std_hu_precontrast,
                    "delta_hu": m.delta_hu,
                    "delta_median_hu": m.delta_median_hu,
                    "evaluated_value": score.value if score else None,
                    "voxel_count": m.voxel_count,
                    "slice_index": m.slice_index,
                    "status": score.status if score else "missing",
                    "status_label": score.label if score else "Missing",
                    "warning": score.warning if score else "Missing ROI measurement",
                    "series_warnings": " | ".join(self.warnings),
                    "threshold_min_opt": self.threshold.min_opt if self.threshold else None,
                    "threshold_max_opt": self.threshold.max_opt if self.threshold else None,
                    "threshold_min_with_threshold": self.threshold.min_with_threshold if self.threshold else None,
                    "threshold_max_with_threshold": self.threshold.max_with_threshold if self.threshold else None,
                    "output_image_path": self.output_image_path,
                }
            )
        return rows

    def to_summary_row(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for score in self.scores.values():
            status_counts[score.status] = status_counts.get(score.status, 0) + 1

        return {
            "ct_id": self.ct_id,
            "ct_name": self.ct_name,
            "ct_folder": self.ct_folder,
            "CT_type": self.ct_type,
            "procedure_code": self.procedure_code,
            "phase_name": self.phase_name,
            "series_folder": self.series_folder,
            "series_dir": self.series_dir,
            "reference_series_folder": self.reference_series_folder,
            "metric_name": self.metric_name,
            "n_rois": len(self.measurements),
            "status_counts": status_counts,
            "n_warnings": len(self.warnings),
            "warnings": " | ".join(self.warnings),
            "image_path": self.output_image_path,
            "threshold_min_opt": self.threshold.min_opt if self.threshold else None,
            "threshold_max_opt": self.threshold.max_opt if self.threshold else None,
            "threshold_min_with_threshold": self.threshold.min_with_threshold if self.threshold else None,
            "threshold_max_with_threshold": self.threshold.max_with_threshold if self.threshold else None,
        }

from __future__ import annotations

from .models import ScoreResult, ThresholdBand


def score_value(value: float | None, threshold: ThresholdBand | None) -> ScoreResult:
    if value is None:
        return ScoreResult(value=None, status="missing", label="Missing", warning="No measurement available")
    if threshold is None:
        return ScoreResult(value=value, status="not_evaluated", label="Not evaluated", warning=None)

    if threshold.min_opt <= value <= threshold.max_opt:
        return ScoreResult(value=value, status="optimal", label="Optimal", warning=None)

    if threshold.min_with_threshold <= value < threshold.min_opt:
        return ScoreResult(
            value=value,
            status="acceptable_low",
            label="Acceptable low",
            warning=None,
        )

    if threshold.max_opt < value <= threshold.max_with_threshold:
        return ScoreResult(
            value=value,
            status="acceptable_high",
            label="Acceptable high",
            warning=None,
        )

    if value < threshold.min_with_threshold:
        return ScoreResult(
            value=value,
            status="critical_low",
            label="Critical low",
            warning="Value is below threshold",
        )

    return ScoreResult(
        value=value,
        status="critical_high",
        label="Critical high",
        warning="Value is above threshold",
    )

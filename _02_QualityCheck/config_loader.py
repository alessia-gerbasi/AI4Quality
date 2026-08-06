from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import PhaseRule, ProcedureRule, ThresholdBand


SUPPORTED_PHASES = {"arteriosa", "venosa"}
BASELINE_PHASES = {"basale", ""}


def normalize_phase(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text.lower()


def resolve_effective_phase(phase_name: str | None, ct_type: str | None) -> str:
    phase = normalize_phase(phase_name)
    ct_type_norm = (str(ct_type).strip().lower() if ct_type is not None else "")

    # In vascular studies, an unlabeled retained target series is arterial by default.
    if phase == "" and ct_type_norm == "vascular":
        return "arteriosa"

    return phase


def load_rules(yaml_path: Path) -> dict[str, ProcedureRule]:
    with open(yaml_path) as fh:
        raw: dict[str, dict[str, Any]] = yaml.safe_load(fh) or {}

    rules: dict[str, ProcedureRule] = {}
    for code, entry in raw.items():
        code_norm = (code or "").strip().upper()
        arteriosa_rois = list(entry.get("arteriosa") or [])
        venosa_rois = list(entry.get("venosa") or [])

        phase_rules: dict[str, PhaseRule] = {
            "arteriosa": PhaseRule(
                rois=arteriosa_rois,
                hu_threshold=ThresholdBand.from_list(entry.get("HU_arteriosa")),
            ),
            "venosa": PhaseRule(
                rois=venosa_rois,
                hu_threshold=ThresholdBand.from_list(entry.get("HU_venosa")),
                hu_delta_threshold=ThresholdBand.from_list(entry.get("HU_delta_venosa")),
            ),
        }
        rules[code_norm] = ProcedureRule(procedure_code=code_norm, phases=phase_rules)

    return rules

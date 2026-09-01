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


def load_keyword_overrides(yaml_path: Path) -> dict[str, str]:
    """Return {keyword: override_procedure_code}, e.g. {'embolia': 'TACACP'}."""
    with open(yaml_path) as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    overrides: dict[str, str] = {}
    for keyword, entry in (raw.get("keyword_overrides") or {}).items():
        code = (entry or {}).get("override_procedure_code")
        if keyword and code:
            overrides[str(keyword).strip().lower()] = str(code).strip().upper()
    return overrides


def resolve_effective_procedure_code(procedure_code: str, series_text: str, overrides: dict[str, str]) -> str:
    """Return the procedure code to use for rule lookup, applying keyword overrides."""
    text = (series_text or "").strip().lower()
    for keyword, override_code in overrides.items():
        if keyword in text:
            return override_code
    return procedure_code


def load_rules(yaml_path: Path) -> dict[str, ProcedureRule]:
    with open(yaml_path) as fh:
        raw: dict[str, dict[str, Any]] = yaml.safe_load(fh) or {}

    # Unified format support:
    # procedures:
    #   TACXXX:
    #     phases:
    #       arteriosa: { rois: [...], HU: [...] }
    #       venosa:    { rois: [...], HU: [...], HU_delta: [...] }
    if "procedures" in raw:
        rules: dict[str, ProcedureRule] = {}
        procedures = raw.get("procedures") or {}
        for code, entry in procedures.items():
            code_norm = (code or "").strip().upper()
            phases = (entry or {}).get("phases") or {}

            art = phases.get("arteriosa") or {}
            ven = phases.get("venosa") or {}

            phase_rules: dict[str, PhaseRule] = {
                "arteriosa": PhaseRule(
                    rois=list(art.get("rois") or []),
                    hu_threshold=ThresholdBand.from_list(art.get("HU")),
                ),
                "venosa": PhaseRule(
                    rois=list(ven.get("rois") or []),
                    hu_threshold=ThresholdBand.from_list(ven.get("HU")),
                    hu_delta_threshold=ThresholdBand.from_list(ven.get("HU_delta")),
                ),
            }
            rules[code_norm] = ProcedureRule(procedure_code=code_norm, phases=phase_rules)

        return rules

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

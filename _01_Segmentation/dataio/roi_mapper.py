from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


# Phase names treated as "run both arteriosa and venosa structures"
_NEUTRAL_PHASES = {"monitoring", "basale", "base", "vascular", ""}


def _load_table(roi_table_path: Path) -> dict[str, dict[str, list[str]]]:
    with open(roi_table_path) as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)

    # Unified format:
    # procedures:
    #   TACXXX:
    #     phases:
    #       arteriosa: { rois: [...] }
    #       venosa:    { rois: [...] }
    if isinstance(raw, dict) and "procedures" in raw:
        procedures = raw.get("procedures") or {}
        table: dict[str, dict[str, list[str]]] = {}
        for code, entry in procedures.items():
            phases = (entry or {}).get("phases") or {}
            arteriosa = (phases.get("arteriosa") or {}).get("rois") or []
            venosa = (phases.get("venosa") or {}).get("rois") or []
            table[(code or "").strip().upper()] = {
                "arteriosa": list(arteriosa),
                "venosa": list(venosa),
            }
        return table

    table: dict[str, dict[str, list[str]]] = {}
    for code, phases in (raw or {}).items():
        table[(code or "").strip().upper()] = {
            "arteriosa": list(phases.get("arteriosa") or []),
            "venosa": list(phases.get("venosa") or []),
        }
    return table


class RoiMapper:
    def __init__(self, roi_table_path: Path) -> None:
        self._table = _load_table(roi_table_path)

    def get_structures(self, procedure_code: str, phase_name: str) -> list[str]:
        """Return deduplicated list of TotalSegmentator structure names to segment."""
        code = (procedure_code or "").strip().upper()
        phase = (phase_name or "").strip().lower()

        entry = self._table.get(code)
        if entry is None:
            return []

        arteriosa = entry["arteriosa"]
        venosa = entry["venosa"]

        if phase == "arteriosa":
            structures = arteriosa
        elif phase == "venosa":
            structures = venosa
        else:
            # monitoring / basale / vascular / unknown → both
            seen: dict[str, None] = {}
            for s in arteriosa + venosa:
                seen[s] = None
            structures = list(seen)

        return [s for s in structures if s]

    def known_codes(self) -> list[str]:
        return list(self._table.keys())

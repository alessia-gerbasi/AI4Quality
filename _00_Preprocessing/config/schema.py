from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    pass


@dataclass
class PipelineConfig:
    raw: dict[str, Any]

    @property
    def io(self) -> dict[str, Any]:
        return self.raw["io"]

    @property
    def selection(self) -> dict[str, Any]:
        return self.raw["selection"]

    @property
    def merge(self) -> dict[str, Any]:
        return self.raw["merge"]

    @property
    def runtime(self) -> dict[str, Any]:
        return self.raw["runtime"]

    @property
    def logging(self) -> dict[str, Any]:
        return self.raw["logging"]

    @property
    def vascular_selection(self) -> dict[str, Any]:
        return self.raw["vascular_selection"]

    @property
    def parenchymal_selection(self) -> dict[str, Any]:
        return self.raw["parenchymal_selection"]


def _require_keys(container: dict[str, Any], keys: list[str], section: str) -> None:
    for key in keys:
        if key not in container:
            raise ConfigError(f"Missing key '{key}' in section '{section}'")


def load_config(config_path: str) -> PipelineConfig:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ConfigError("Config root must be a mapping")

    for section in ["io", "selection", "merge", "runtime", "logging", "vascular_selection", "parenchymal_selection"]:
        if section not in data or not isinstance(data[section], dict):
            raise ConfigError(f"Missing or invalid section: {section}")

    _require_keys(data["io"], ["dicom_roots", "injection_history_xlsx", "link_anonymization_xlsx", "output_dir"], "io")
    _require_keys(data["selection"], ["accepted_procedure_codes", "include_keywords", "exclude_keywords", "precedence"], "selection")
    _require_keys(data["vascular_selection"], ["group_field", "keep_monitoring", "candidate_status", "output_csv", "summary_file", "monitoring", "criteria"], "vascular_selection")
    _require_keys(data["parenchymal_selection"], ["group_field", "candidate_status", "output_csv", "summary_file", "criteria"], "parenchymal_selection")

    phase_keywords = data["selection"].get("phase_keywords")
    if phase_keywords is not None and not isinstance(phase_keywords, list):
        raise ConfigError("selection.phase_keywords must be a list when provided")

    if not isinstance(data["vascular_selection"].get("criteria"), list) or not data["vascular_selection"]["criteria"]:
        raise ConfigError("vascular_selection.criteria must be a non-empty list")

    if not isinstance(data["parenchymal_selection"].get("criteria"), list) or not data["parenchymal_selection"]["criteria"]:
        raise ConfigError("parenchymal_selection.criteria must be a non-empty list")

    _require_keys(data["merge"], ["enable_split_detection", "require_contiguous_prefixes"], "merge")
    _require_keys(data["runtime"], ["max_workers", "max_ct", "dry_run"], "runtime")
    _require_keys(data["logging"], ["level", "jsonl_file", "console"], "logging")

    if data["selection"]["precedence"] not in {"exclude", "include"}:
        raise ConfigError("selection.precedence must be one of: exclude, include")

    if not isinstance(data["io"]["dicom_roots"], list) or not data["io"]["dicom_roots"]:
        raise ConfigError("io.dicom_roots must be a non-empty list")

    return PipelineConfig(raw=data)

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CTIdentity:
    ct_folder: str
    ct_id: str | None
    ct_name: str | None


@dataclass
class SeriesRecord:
    ct_folder: str
    study_folder: str
    series_folder: str
    series_path: str
    series_name: str
    body_part_examined: str | None
    acquisition_time: str | None
    series_description: str | None
    series_instance_uid: str | None
    instance_count: int
    metadata_issues: list[str] = field(default_factory=list)


@dataclass
class EnrichedSeriesRecord:
    base: SeriesRecord
    scanner: str | None
    procedure_code_value: str | None


@dataclass
class SelectionDecision:
    status: str
    reason_code: str
    reason_detail: str
    include_hits: list[str]
    exclude_hits: list[str]
    phase_name: str | None = None


@dataclass
class MergeResult:
    merge_group_id: str | None
    part_index: int | None
    part_count: int | None
    merge_status: str


@dataclass
class OutputRow:
    ct_id: str | None
    ct_name: str | None
    ct_folder: str
    series_name: str
    series_folder: str
    procedure_code_value: str | None
    body_part_examined: str | None
    acquisition_time: str | None
    status: str
    reason_code: str
    reason_detail: str
    merge_group_id: str | None
    merge_status: str
    scanner: str | None
    metadata_issues: str


def to_flat_dict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "__dict__"):
        return obj.__dict__.copy()
    raise TypeError(f"Unsupported object type: {type(obj)}")

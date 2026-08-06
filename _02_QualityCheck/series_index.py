from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config_loader import BASELINE_PHASES, SUPPORTED_PHASES, normalize_phase, resolve_effective_phase


@dataclass(frozen=True)
class SeriesRow:
    ct_id: int
    ct_name: str
    ct_folder: str
    series_name: str
    series_folder: str
    procedure_code: str
    phase_name: str
    acquisition_time_seconds: float | None
    merge_status: str


def _sanitize_filename(value: str) -> str:
    candidate = (value or "series").strip()
    candidate = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in candidate)
    candidate = "_".join(part for part in candidate.split("_") if part)
    return candidate or "series"


def _output_folder_name(series_name: str, series_folder: str, merge_status: str) -> str:
    if merge_status == "merged_final":
        return f"{_sanitize_filename(series_name)}_collapsed"
    return series_folder


def _parse_acquisition_time_to_seconds(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None

    try:
        raw = float(text)
    except ValueError:
        return None

    hhmmss = int(raw)
    frac = raw - hhmmss
    hh = hhmmss // 10000
    mm = (hhmmss % 10000) // 100
    ss = hhmmss % 100
    if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60):
        return None
    return hh * 3600 + mm * 60 + ss + frac


def load_series_table(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df[df["status"] == "accepted"].copy()
    df["phase_norm"] = df["phase_name"].fillna("").astype(str).str.strip().str.lower()
    df["phase_effective"] = df.apply(
        lambda row: resolve_effective_phase(row.get("phase_name", ""), row.get("CT_type", "")),
        axis=1,
    )
    df["procedure_code_norm"] = df["procedure_code_value"].fillna("").astype(str).str.strip().str.upper()
    return df


def build_series_dir(root_nii: Path, row: pd.Series) -> Path:
    folder_name = _output_folder_name(
        str(row.get("series_name", "")),
        str(row.get("series_folder", "")),
        str(row.get("merge_status", "")),
    )
    return root_nii / str(row["ct_folder"]) / "studyinstanceuid" / folder_name


def iter_target_series(df: pd.DataFrame):
    for _, row in df.iterrows():
        phase = str(row.get("phase_effective", "") or "")
        if phase in SUPPORTED_PHASES:
            yield row


def find_baseline_for_venous(df_patient: pd.DataFrame, venous_row: pd.Series) -> pd.Series | None:
    candidates = df_patient[df_patient["phase_norm"].isin(BASELINE_PHASES)].copy()
    if candidates.empty:
        return None

    venous_t = _parse_acquisition_time_to_seconds(venous_row.get("acquisition_time"))
    if venous_t is None:
        return candidates.iloc[0]

    candidates["_t"] = candidates["acquisition_time"].apply(_parse_acquisition_time_to_seconds)
    with_time = candidates[candidates["_t"].notna()].copy()
    if with_time.empty:
        return candidates.iloc[0]

    before = with_time[with_time["_t"] <= venous_t].copy()
    if not before.empty:
        before["_dt"] = venous_t - before["_t"]
        return before.sort_values("_dt").iloc[0]

    with_time["_dt"] = (with_time["_t"] - venous_t).abs()
    return with_time.sort_values("_dt").iloc[0]

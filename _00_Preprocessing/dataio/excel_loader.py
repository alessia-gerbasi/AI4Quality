from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from domain.models import EnrichedSeriesRecord, SeriesRecord


@dataclass
class ExcelContext:
    link_df: pd.DataFrame
    inj_df: pd.DataFrame


def _normalize_colnames(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def load_excel_context(link_xlsx: str, injection_xlsx: str) -> ExcelContext:
    link_df = _normalize_colnames(pd.read_excel(link_xlsx))
    inj_df = _normalize_colnames(pd.read_excel(injection_xlsx))
    return ExcelContext(link_df=link_df, inj_df=inj_df)


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def _extract_ct_id(ct_folder: str) -> str | None:
    parts = ct_folder.split("_")
    if len(parts) < 3:
        return None
    if parts[0] != "CT" or parts[1] != "QUALITY":
        return None
    return parts[2]


def _normalize_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _pick_first_non_empty(rows: list[dict], field: str) -> str | None:
    for row in rows:
        v = _normalize_value(row.get(field))
        if v is not None:
            return v
    return None


def _build_lookup(df: pd.DataFrame, key_col: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for _, row in df.iterrows():
        key = _normalize_value(row.get(key_col))
        if key is None:
            continue
        out.setdefault(key, []).append(row.to_dict())
    return out


def enrich_series(records: list[SeriesRecord], ctx: ExcelContext) -> tuple[list[EnrichedSeriesRecord], list[dict]]:
    issues: list[dict] = []

    link_id_col = _find_col(ctx.link_df, ["ID", "id"])
    link_pat_col = _find_col(ctx.link_df, ["PAT_N", "pat_n", "Patient Id"])
    link_index_col = _find_col(ctx.link_df, ["index", "IDX", "idx"])

    inj_order_col = _find_col(ctx.inj_df, ["Order Procedure", "OrderProcedure", "order_procedure"])
    inj_scanner_col = _find_col(ctx.inj_df, ["Scanner", "scanner"])
    inj_pat_col = _find_col(ctx.inj_df, ["Patient Id", "PatientID", "PAT_N"])
    inj_index_col = _find_col(ctx.inj_df, ["index", "IDX", "idx"])

    if inj_order_col is None:
        issues.append({"scope": "excel", "issue": "missing_order_procedure_column"})
    if inj_scanner_col is None:
        issues.append({"scope": "excel", "issue": "missing_scanner_column"})
    if link_id_col is None:
        issues.append({"scope": "excel", "issue": "missing_link_id_column"})
    if link_pat_col is None:
        issues.append({"scope": "excel", "issue": "missing_link_pat_column"})
    if link_index_col is None:
        issues.append({"scope": "excel", "issue": "missing_link_index_column"})
    if inj_pat_col is None:
        issues.append({"scope": "excel", "issue": "missing_injection_patient_id_column"})
    if inj_index_col is None:
        issues.append({"scope": "excel", "issue": "missing_injection_index_column"})

    link_lookup_by_id: dict[str, list[dict]] = {}
    if link_id_col is not None:
        link_lookup_by_id = _build_lookup(ctx.link_df, link_id_col)

    inj_by_index: dict[str, list[dict]] = {}
    inj_by_pat: dict[str, list[dict]] = {}
    if inj_index_col is not None:
        inj_by_index = _build_lookup(ctx.inj_df, inj_index_col)
    if inj_pat_col is not None:
        inj_by_pat = _build_lookup(ctx.inj_df, inj_pat_col)

    enriched: list[EnrichedSeriesRecord] = []

    for rec in records:
        ct_id = _extract_ct_id(rec.ct_folder)
        scanner = None
        procedure = None

        if ct_id and link_id_col is not None:
            ct_key = f"CT_QUALITY_{ct_id}"
            link_rows = link_lookup_by_id.get(ct_key, [])

            if not link_rows:
                issues.append({
                    "scope": "ct",
                    "ct_folder": rec.ct_folder,
                    "series_folder": rec.series_folder,
                    "issue": "missing_link_mapping",
                    "ct_key": ct_key,
                })
                enriched.append(EnrichedSeriesRecord(base=rec, scanner=scanner, procedure_code_value=procedure))
                continue

            if len(link_rows) > 1:
                issues.append({
                    "scope": "ct",
                    "ct_folder": rec.ct_folder,
                    "series_folder": rec.series_folder,
                    "issue": "duplicate_link_mapping",
                    "ct_key": ct_key,
                    "match_count": len(link_rows),
                })

            link_row = link_rows[0]
            idx_key = _normalize_value(link_row.get(link_index_col)) if link_index_col else None
            pat_key = _normalize_value(link_row.get(link_pat_col)) if link_pat_col else None

            idx_rows = inj_by_index.get(idx_key, []) if idx_key else []
            pat_rows = inj_by_pat.get(pat_key, []) if pat_key else []

            chosen_rows: list[dict] = []
            source = None
            if idx_rows:
                chosen_rows = idx_rows
                source = "index"
            elif pat_rows:
                chosen_rows = pat_rows
                source = "patient_id"

            if not chosen_rows:
                issues.append({
                    "scope": "ct",
                    "ct_folder": rec.ct_folder,
                    "series_folder": rec.series_folder,
                    "issue": "missing_injection_mapping",
                    "ct_key": ct_key,
                    "index": idx_key,
                    "patient_id": pat_key,
                })
                enriched.append(EnrichedSeriesRecord(base=rec, scanner=scanner, procedure_code_value=procedure))
                continue

            if len(chosen_rows) > 1:
                issues.append({
                    "scope": "ct",
                    "ct_folder": rec.ct_folder,
                    "series_folder": rec.series_folder,
                    "issue": "duplicate_injection_mapping",
                    "source": source,
                    "match_count": len(chosen_rows),
                    "index": idx_key,
                    "patient_id": pat_key,
                })

            if idx_rows and pat_rows:
                idx_order = _pick_first_non_empty(idx_rows, inj_order_col) if inj_order_col else None
                pat_order = _pick_first_non_empty(pat_rows, inj_order_col) if inj_order_col else None
                if idx_order is not None and pat_order is not None and idx_order != pat_order:
                    issues.append({
                        "scope": "ct",
                        "ct_folder": rec.ct_folder,
                        "series_folder": rec.series_folder,
                        "issue": "index_patient_mapping_conflict",
                        "index_order_procedure": idx_order,
                        "patient_order_procedure": pat_order,
                    })

            chosen = chosen_rows[0]
            if inj_scanner_col:
                scanner = _normalize_value(chosen.get(inj_scanner_col))
            if inj_order_col:
                procedure = _normalize_value(chosen.get(inj_order_col))

            if procedure is None:
                issues.append({
                    "scope": "ct",
                    "ct_folder": rec.ct_folder,
                    "series_folder": rec.series_folder,
                    "issue": "empty_order_procedure",
                    "source": source,
                    "index": idx_key,
                    "patient_id": pat_key,
                })
        else:
            issues.append({
                "scope": "ct",
                "ct_folder": rec.ct_folder,
                "series_folder": rec.series_folder,
                "issue": "missing_ct_identity_for_join",
            })

        enriched.append(EnrichedSeriesRecord(base=rec, scanner=scanner, procedure_code_value=procedure))

    return enriched, issues

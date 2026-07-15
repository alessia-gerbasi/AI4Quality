from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd
import yaml


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return text.lower()


def _row_haystack(row: pd.Series, fields: list[str]) -> str:
    parts = [_normalize_text(row.get(field)) for field in fields]
    return " ".join(part for part in parts if part)


def _match_ordered_label(haystack: str, ordered_labels: list[dict[str, Any]]) -> tuple[int, str]:
    fallback_label = "other"
    for index, spec in enumerate(ordered_labels):
        label = str(spec.get("label", f"option_{index}"))
        patterns = spec.get("patterns", [])
        if label.lower() == "other" and not patterns:
            fallback_label = label
            continue
        for pattern in patterns:
            if re.search(pattern, haystack):
                return index, label
    return len(ordered_labels), fallback_label


def _extract_number(haystack: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, haystack)
        if not match:
            continue
        for group in match.groups():
            if group is None:
                continue
            try:
                return float(group.replace(",", "."))
            except ValueError:
                continue
        try:
            return float(match.group(0).replace(",", "."))
        except ValueError:
            continue
    return None


def _extract_bucket_index(haystack: str, ordered_labels: list[dict[str, Any]]) -> int:
    label_index, _ = _match_ordered_label(haystack, ordered_labels)
    return label_index


def _match_flag(haystack: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, haystack) for pattern in patterns)


def _classify_phase(haystack: str, ordered_labels: list[dict[str, Any]]) -> tuple[int, str]:
    return _match_ordered_label(haystack, ordered_labels)


def _classify_named_phase(row: pd.Series, rules: dict[str, Any]) -> str:
    phase_field = str(rules.get("phase_field", "phase_name"))
    raw_phase = _normalize_text(row.get(phase_field))
    aliases: dict[str, list[str]] = rules.get("phase_aliases", {})

    if raw_phase:
        for canonical, patterns in aliases.items():
            for pattern in patterns:
                if re.search(pattern, raw_phase):
                    return str(canonical)

    haystack_fields = list(rules.get("phase_source_fields", ["phase_name", "series_name", "series_folder"]))
    haystack = _row_haystack(row, haystack_fields)
    for canonical, patterns in aliases.items():
        for pattern in patterns:
            if re.search(pattern, haystack):
                return str(canonical)

    return str(rules.get("default_phase", "unknown"))


def _normalize_series_name(value: Any) -> str:
    text = _normalize_text(value)
    text = re.sub(r"\s+", " ", text)
    return text


def _criterion_score(row: pd.Series, criterion: dict[str, Any]) -> tuple[Any, str, dict[str, Any]]:
    fields = list(criterion.get("fields", ["series_name", "series_folder"]))
    haystack = _row_haystack(row, fields)
    name = str(criterion["name"])

    if name in {"vascular_phase", "kernel", "thickness", "dose"}:
        ordered_labels = list(criterion.get("ordered_labels", []))
        rank, label = _match_ordered_label(haystack, ordered_labels)
        return (rank, 0.0), label, {f"{name}_label": label}

    if name in {"reconstruction_family", "matrix", "acquisition_size"}:
        ordered_labels = list(criterion.get("ordered_labels", []))
        rank, label = _match_ordered_label(haystack, ordered_labels)
        return (rank, 0.0), label, {f"{name}_label": label}

    if name == "phase":
        ordered_labels = list(criterion.get("ordered_labels", []))
        rank, label = _match_ordered_label(haystack, ordered_labels)
        return (rank, 0.0), label, {"phase_label": label}

    if name == "hr":
        hr_patterns = list(criterion.get("hr_patterns", []))
        hr = _match_flag(haystack, hr_patterns)
        rank = 1 if hr else 0
        label = "hr" if hr else "non_hr"
        return (rank, 0.0), label, {"hr_label": label}

    if name == "non_bone":
        ordered_labels = list(criterion.get("ordered_labels", []))
        rank, label = _match_ordered_label(haystack, ordered_labels)
        return (rank, 0.0), label, {"non_bone_label": label}

    if name == "dose":
        ordered_labels = list(criterion.get("ordered_labels", []))
        rank, label = _match_ordered_label(haystack, ordered_labels)
        return (rank, 0.0), label, {"dose_label": label}

    if name == "rr":
        rr_value = _extract_number(haystack, list(criterion.get("rr_extraction_patterns", [])))
        if rr_value is None:
            return (999.0, 0.0), "missing_rr", {"rr_value": None}

        phase_criterion = next((item for item in criterion.get("all_criteria", []) if item.get("name") == "phase"), None)
        phase_label = "other"
        rr_targets = dict(criterion.get("rr_targets", {}))
        if phase_criterion is not None:
            rr_targets.update(dict(phase_criterion.get("rr_targets", {})))
        if phase_criterion is not None:
            phase_label = _classify_phase(haystack, list(phase_criterion.get("ordered_labels", [])))[1]

        midpoint_distances: list[float] = []
        if phase_label in rr_targets:
            target = rr_targets.get(phase_label)
            if isinstance(target, list) and len(target) == 2:
                low, high = float(target[0]), float(target[1])
                midpoint = (low + high) / 2.0
                midpoint_distances.append(abs(rr_value - midpoint))
        else:
            for target in rr_targets.values():
                if not isinstance(target, list) or len(target) != 2:
                    continue
                low, high = float(target[0]), float(target[1])
                midpoint = (low + high) / 2.0
                midpoint_distances.append(abs(rr_value - midpoint))

        rr_score = min(midpoint_distances) if midpoint_distances else 999.0
        return (rr_score, 0.0), f"rr={rr_value:g}", {"rr_value": rr_value, "phase_label": phase_label, "rr_score": rr_score}

    raise ValueError(f"Unsupported criterion: {name}")


def _candidate_mask(df: pd.DataFrame, rules: dict[str, Any]) -> pd.Series:
    status_value = rules.get("candidate_status", "accepted")
    mask = df["status"].astype(str).eq(status_value)
    allowed_codes = {str(code).strip().upper() for code in rules.get("allowed_procedure_codes", []) if str(code).strip()}
    if allowed_codes:
        mask = mask & df["procedure_code_value"].astype(str).str.upper().isin(allowed_codes)
    if rules.get("exclude_monitoring", True):
        mask = mask & ~_monitoring_mask(df, rules)
    return mask


def _apply_phase_policy_filters(work_df: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    if work_df.empty:
        return work_df

    phase_allowlist = set(rules.get("phase_allowlist", []))
    if phase_allowlist:
        work_df = work_df[work_df["_phase_key"].isin(phase_allowlist)].copy()

    if bool(rules.get("exclude_unknown_phase", False)):
        work_df = work_df[work_df["_phase_key"] != str(rules.get("default_phase", "unknown"))].copy()

    # If both arterial and venous exist for an exam, drop pre-contrast groups for parenchymal quantification.
    drop_cfg = rules.get("drop_precontrast_when_arterial_and_venous", {})
    if isinstance(drop_cfg, dict) and bool(drop_cfg.get("enabled", False)):
        group_field = str(rules.get("group_field", "ct_id"))
        arterial_key = str(drop_cfg.get("arterial_key", "arterial"))
        venous_key = str(drop_cfg.get("venous_key", "venous"))
        precontrast_key = str(drop_cfg.get("precontrast_key", "pre_contrast"))

        phase_sets = work_df.groupby(group_field, dropna=False)["_phase_key"].apply(lambda s: set(s.tolist()))
        ct_with_both = {
            ct for ct, phases in phase_sets.items() if arterial_key in phases and venous_key in phases
        }
        if ct_with_both:
            work_df = work_df[
                ~(
                    work_df[group_field].isin(ct_with_both)
                    & work_df["_phase_key"].eq(precontrast_key)
                )
            ].copy()

    return work_df


def _monitoring_mask(df: pd.DataFrame, rules: dict[str, Any]) -> pd.Series:
    monitoring_rules = rules.get("monitoring", {})
    fields = list(monitoring_rules.get("fields", ["series_name", "series_folder", "phase_name"]))
    patterns = list(monitoring_rules.get("patterns", []))
    if not patterns:
        return pd.Series(False, index=df.index)

    haystacks = df.apply(lambda row: _row_haystack(row, fields), axis=1)
    return haystacks.apply(lambda text: _match_flag(text, patterns))


def _score_row(row: pd.Series, rules: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    score_parts: list[Any] = []

    for criterion in rules.get("criteria", []):
        criterion_with_context = dict(criterion)
        criterion_with_context["all_criteria"] = rules.get("criteria", [])
        score, label, metadata = _criterion_score(row, criterion_with_context)
        score_parts.append(score)
        details[str(criterion["name"])] = {"score": score, "label": label, **metadata}

    score_parts.append(_normalize_text(row.get("acquisition_time")) or "zzzz")
    score_parts.append(_normalize_text(row.get("series_folder")) or "zzzz")

    return {
        "score_tuple": tuple(score_parts),
        "details": details,
    }


def _describe_difference(selected: dict[str, Any], alternative: dict[str, Any], rules: dict[str, Any]) -> str:
    criterion_names = [str(criterion["name"]) for criterion in rules.get("criteria", [])]
    for name in criterion_names:
        selected_score = selected["details"][name]["score"]
        alternative_score = alternative["details"][name]["score"]
        if selected_score == alternative_score:
            continue

        selected_label = selected["details"][name]["label"]
        alternative_label = alternative["details"][name]["label"]
        if name == "rr":
            selected_rr = selected["details"][name].get("rr_value")
            alternative_rr = alternative["details"][name].get("rr_value")
            return (
                "wins on RR tie-breaker: "
                f"{selected_rr if selected_rr is not None else 'missing'} is closer to the configured target than "
                f"{alternative_rr if alternative_rr is not None else 'missing'}"
            )
        if selected_score < alternative_score:
            return f"wins on {name}: {selected_label} beats {alternative_label}"
        return f"loses on {name}: {selected_label} vs {alternative_label}"

    if selected["score_tuple"] < alternative["score_tuple"]:
        return "wins on deterministic tie-breakers"
    if selected["score_tuple"] > alternative["score_tuple"]:
        return "loses on deterministic tie-breakers"
    return "ties exactly"


def _render_rule_summary(rules: dict[str, Any]) -> str:
    policy_name = str(rules.get("policy_name", "series")).strip().lower()
    title = f"# {policy_name.capitalize()} Series Selection Summary"
    lines = [title, "", "## Configurable Rules", ""]
    lines.append("```yaml")
    lines.append(yaml.safe_dump(rules, sort_keys=False).rstrip())
    lines.append("```")
    lines.append("")
    lines.append("## Selection Logic")
    lines.append("")
    lines.append("- Group rows by the configured exam field.")
    lines.append("- Keep any monitoring rows unchanged when they match the configured monitoring patterns.")
    lines.append("- Rank the remaining eligible vascular series lexicographically by the configured criteria order.")
    lines.append("- Use RR% only as a late tie-breaker, with target ranges configured per phase.")
    lines.append("- Break exact ties deterministically using acquisition time and series folder.")
    lines.append("")
    return "\n".join(lines)


def _series_summary_row(row: pd.Series) -> dict[str, Any]:
    return {
        "ct_id": row.get("ct_id"),
        "ct_name": row.get("ct_name"),
        "series_name": row.get("series_name"),
        "series_folder": row.get("series_folder"),
        "phase_name": row.get("phase_name"),
        "acquisition_time": row.get("acquisition_time"),
        "procedure_code_value": row.get("procedure_code_value"),
        "scanner": row.get("scanner"),
        "merge_status": row.get("merge_status"),
    }


def _render_exam_section(report: dict[str, Any]) -> str:
    lines = [f"### Exam {report['ct_id']} - {report['ct_name']}", ""]

    selected_series = report.get("selected_series", [])
    if not selected_series:
        lines.append("No eligible series was identified.")
        lines.append("")
        return "\n".join(lines)

    lines.append("Selected series:")
    for row in selected_series:
        phase_suffix = f" [phase={row.get('phase_key')}]" if row.get("phase_key") else ""
        lines.append(f"- {row['series_name']} ({row['series_folder']}){phase_suffix}")
    lines.append("")

    missing_required = report.get("missing_required_phases", [])
    if missing_required:
        lines.append(f"Missing required phase buckets: {', '.join(missing_required)}")
        lines.append("")

    lines.append("")
    return "\n".join(lines)


def _select_series(retained_df: pd.DataFrame, rules: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    group_field = str(rules.get("group_field", "ct_id"))
    group_by_phase = bool(rules.get("group_by_phase", False))
    policy_name = str(rules.get("policy_name", "series")).strip().lower()
    required_phase_buckets = [str(x) for x in rules.get("required_phase_buckets", [])]
    keep_additional_distinct_names = bool(rules.get("keep_additional_distinct_names", True))
    keep_one_per_additional_phase = bool(rules.get("keep_one_per_additional_phase", False))
    select_one_best_remaining = bool(rules.get("select_one_best_remaining", False))
    keep_additional_name_patterns: list[str] = [
        str(p).lower() for p in rules.get("keep_additional_name_patterns", [])
    ]

    work_df = retained_df.copy()
    if group_by_phase:
        work_df["_phase_key"] = work_df.apply(lambda row: _classify_named_phase(row, rules), axis=1)
        work_df = _apply_phase_policy_filters(work_df, rules)
    else:
        # Even without full phase grouping, tag monitoring/premonitoring/aorta from series text
        # so required_phase_buckets matching works for those special series.
        def _support_phase_key(row: pd.Series) -> str:
            text = _row_haystack(row, ["phase_name", "series_name", "series_folder"])
            if "aorta" in text:
                return "aorta"
            if "premonitor" in text:
                return "premonitoring"
            if "monitor" in text:
                return "monitoring"
            return ""
        work_df["_phase_key"] = work_df.apply(_support_phase_key, axis=1)

    output_rows: list[dict[str, Any]] = []
    exam_reports: list[dict[str, Any]] = []
    no_eligible_exams: list[dict[str, Any]] = []

    monitoring_mask = _monitoring_mask(work_df, rules)
    candidate_mask = _candidate_mask(work_df, rules)

    for group_value, group in work_df.groupby(group_field, dropna=False, sort=True):
        ct_name = group["ct_name"].iloc[0] if "ct_name" in group.columns and not group.empty else None
        group_candidates = group[candidate_mask.loc[group.index]].copy()

        scored_candidates: list[dict[str, Any]] = []
        for _, row in group_candidates.iterrows():
            scored = _score_row(row, rules)
            scored_candidates.append({
                "row": row,
                "score_tuple": scored["score_tuple"],
                "details": scored["details"],
                "phase_key": str(row.get("_phase_key", "")),
                "name_key": _normalize_series_name(row.get("series_name")),
            })

        selected_items: list[dict[str, Any]] = []
        seen_paths: set[str] = set()
        missing_required: list[str] = []

        for phase_bucket in required_phase_buckets:
            phase_items = [item for item in scored_candidates if item["phase_key"] == phase_bucket]
            if not phase_items:
                missing_required.append(phase_bucket)
                continue
            best = min(phase_items, key=lambda item: item["score_tuple"])
            series_path = str(best["row"].get("series_path", ""))
            if series_path and series_path in seen_paths:
                continue
            seen_paths.add(series_path)
            selected_items.append(best)

        additional_items = [item for item in scored_candidates if item["phase_key"] not in required_phase_buckets]
        if select_one_best_remaining:
            if additional_items:
                best = min(additional_items, key=lambda item: item["score_tuple"])
                series_path = str(best["row"].get("series_path", ""))
                if not series_path or series_path not in seen_paths:
                    if series_path:
                        seen_paths.add(series_path)
                    selected_items.append(best)

            # After the single best pick, also keep one best per extra name pattern (e.g. lung).
            if keep_additional_name_patterns:
                remaining = [item for item in additional_items
                             if str(item["row"].get("series_path", "")) not in seen_paths]
                for pattern in keep_additional_name_patterns:
                    matches = [item for item in remaining
                               if pattern in item["name_key"]]
                    if matches:
                        best_extra = min(matches, key=lambda item: item["score_tuple"])
                        extra_path = str(best_extra["row"].get("series_path", ""))
                        if extra_path:
                            seen_paths.add(extra_path)
                        selected_items.append(best_extra)
        elif keep_additional_distinct_names:
            grouped_by_name: dict[str, list[dict[str, Any]]] = {}
            for item in additional_items:
                grouped_by_name.setdefault(item["name_key"], []).append(item)
            for _, items in grouped_by_name.items():
                best = min(items, key=lambda item: item["score_tuple"])
                series_path = str(best["row"].get("series_path", ""))
                if series_path and series_path in seen_paths:
                    continue
                seen_paths.add(series_path)
                selected_items.append(best)
        elif keep_one_per_additional_phase:
            grouped_by_phase: dict[str, list[dict[str, Any]]] = {}
            for item in additional_items:
                grouped_by_phase.setdefault(item["phase_key"], []).append(item)
            for _, items in grouped_by_phase.items():
                best = min(items, key=lambda item: item["score_tuple"])
                series_path = str(best["row"].get("series_path", ""))
                if series_path and series_path in seen_paths:
                    continue
                seen_paths.add(series_path)
                selected_items.append(best)

        if not selected_items:
            no_eligible_exams.append({"ct_id": group_value, "ct_name": ct_name, "phase_key": None, "monitoring_count": 0})

        for item in selected_items:
            output_rows.append(item["row"].to_dict())

        exam_reports.append({
            "ct_id": group_value,
            "ct_name": ct_name,
            "phase_key": None,
            "selected_series": [
                {
                    **_series_summary_row(item["row"]),
                    "phase_key": item["phase_key"],
                }
                for item in sorted(selected_items, key=lambda x: (x["phase_key"], x["score_tuple"]))
            ],
            "missing_required_phases": missing_required,
            "candidate_count": len(group_candidates),
        })

    output_df = pd.DataFrame(output_rows)
    if output_df.empty and not retained_df.empty:
        output_df = retained_df.head(0).copy()
    elif not output_df.empty:
        sort_columns = [column for column in [group_field, "series_name", "acquisition_time"] if column in output_df.columns]
        if sort_columns:
            output_df = output_df.sort_values(by=sort_columns, na_position="last").reset_index(drop=True)

    report_key = f"selected_{policy_name}_count"
    report = {
        "rules": rules,
        "exam_count": int(work_df[group_field].nunique(dropna=False)) if group_field in work_df.columns else 0,
        "group_count": int(len(exam_reports)),
        report_key: int(sum(len(item.get("selected_series", [])) for item in exam_reports)),
        "monitoring_rows_kept": int(
            sum(
                1
                for exam in exam_reports
                for row in exam.get("selected_series", [])
                if str(row.get("phase_key", "")) in {"monitoring", "premonitoring"}
            )
        ),
        "no_eligible_exams": no_eligible_exams,
        "exam_reports": exam_reports,
        "policy_name": policy_name,
    }

    report[report_key] = int(sum(len(exam.get("selected_series", [])) for exam in exam_reports))

    return output_df, report


def write_selection_outputs(output_dir: str | Path, retained_df: pd.DataFrame, rules: dict[str, Any]) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    selected_df, report = _select_series(retained_df, rules)
    if "_phase_key" in selected_df.columns:
        selected_df = selected_df.drop(columns=["_phase_key"])
    policy_name = str(rules.get("policy_name", "series")).strip().lower()
    csv_name = str(rules.get("output_csv", f"retained_series_{policy_name}_filtered.csv"))
    summary_name = str(rules.get("summary_file", f"retained_series_{policy_name}_filtered_summary.md"))
    report_key = f"selected_{policy_name}_count"

    selected_df.to_csv(out / csv_name, index=False)

    lines = [_render_rule_summary(rules)]
    lines.append("## Selection Results")
    lines.append("")
    lines.append(f"- Exams processed: {report['exam_count']}")
    lines.append(f"- Groups processed: {report['group_count']}")
    lines.append(f"- Selected {policy_name} series: {report[report_key]}")
    lines.append(f"- Monitoring rows kept: {report['monitoring_rows_kept']}")
    lines.append(f"- Exams without an eligible vascular series: {len(report['no_eligible_exams'])}")
    lines.append("")

    if report["no_eligible_exams"]:
        lines.append(f"## Exams With No Eligible {policy_name.capitalize()} Series")
        lines.append("")
        for item in report["no_eligible_exams"]:
            phase_suffix = f", phase: {item['phase_key']}" if item.get("phase_key") else ""
            lines.append(f"- {item['ct_id']} {item['ct_name']}{phase_suffix} (monitoring rows kept: {item['monitoring_count']})")
        lines.append("")

    lines.append("## Per-Exam Selection")
    lines.append("")
    for exam_report in report["exam_reports"]:
        lines.append(_render_exam_section(exam_report))

    (out / summary_name).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report


def write_vascular_selection_outputs(output_dir: str | Path, retained_df: pd.DataFrame, rules: dict[str, Any]) -> dict[str, Any]:
    local_rules = dict(rules)
    local_rules.setdefault("policy_name", "vascular")
    return write_selection_outputs(output_dir, retained_df, local_rules)


def write_parenchymal_selection_outputs(output_dir: str | Path, retained_df: pd.DataFrame, rules: dict[str, Any]) -> dict[str, Any]:
    local_rules = dict(rules)
    local_rules.setdefault("policy_name", "parenchymal")
    return write_selection_outputs(output_dir, retained_df, local_rules)
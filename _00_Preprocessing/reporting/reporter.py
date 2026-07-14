from __future__ import annotations

from collections import Counter


def summarize(decisions: list[dict], metadata_issues: list[dict]) -> dict:
    status_counter = Counter(d["status"] for d in decisions)
    reason_counter = Counter(d["reason_code"] for d in decisions)
    merge_counter = Counter(d.get("merge_status", "single") for d in decisions)

    return {
        "total_series": len(decisions),
        "status_counts": dict(status_counter),
        "reason_counts": dict(reason_counter),
        "merge_counts": dict(merge_counter),
        "metadata_issue_count": len(metadata_issues),
    }

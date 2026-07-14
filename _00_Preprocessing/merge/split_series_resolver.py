from __future__ import annotations

import re
from collections import defaultdict

from domain.models import EnrichedSeriesRecord, MergeResult


_SPLIT_RE = re.compile(r"^(\d+)[_\-](.+)$")


def _split_name(name: str) -> tuple[int | None, str]:
    m = _SPLIT_RE.match(name)
    if not m:
        return None, name.lower()
    return int(m.group(1)), m.group(2).lower()


def resolve_split_groups(
    items: list[EnrichedSeriesRecord],
    require_contiguous_prefixes: bool = True,
) -> dict[int, MergeResult]:
    grouped: dict[tuple[str, str], list[tuple[int, int, str]]] = defaultdict(list)

    for idx, it in enumerate(items):
        prefix, suffix = _split_name(it.base.series_folder)
        if prefix is None:
            continue
        grouped[(it.base.ct_folder, suffix)].append((idx, prefix, it.base.series_folder))

    result: dict[int, MergeResult] = {
        i: MergeResult(merge_group_id=None, part_index=None, part_count=None, merge_status="single")
        for i in range(len(items))
    }

    group_counter = 0
    for (_, suffix), members in grouped.items():
        if len(members) <= 1:
            continue

        members = sorted(members, key=lambda x: x[1])
        prefixes = [m[1] for m in members]
        contiguous = all((b - a) == 1 for a, b in zip(prefixes, prefixes[1:]))
        if require_contiguous_prefixes and not contiguous:
            continue

        group_counter += 1
        gid = f"merge_{group_counter:06d}_{suffix[:24]}"
        for part_idx, (global_idx, _, _) in enumerate(members, start=1):
            result[global_idx] = MergeResult(
                merge_group_id=gid,
                part_index=part_idx,
                part_count=len(members),
                merge_status="merged_source",
            )

    return result

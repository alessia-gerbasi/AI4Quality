from __future__ import annotations

from dataclasses import dataclass, field


# Structures that require a licensed task and their task name
_LICENSED: dict[str, str] = {
    "aorta": "heartchambers_highres",
    "pulmonary_artery": "heartchambers_highres",
    "coronary_arteries": "coronary_arteries",
}


@dataclass
class TaskCall:
    task: str
    # None → no subset filter (heartchambers_highres / coronary_arteries run fully)
    roi_subset: list[str] | None
    # which output .nii.gz files to expect / copy to the series dir
    output_structures: list[str] = field(default_factory=list)


def build_task_calls(structures: list[str], licensed_enabled: bool) -> list[TaskCall]:
    """Map a list of structure names to the minimal set of TotalSegmentator calls."""
    licensed_structures: list[str] = []
    total_structures: list[str] = []

    for s in structures:
        if s in _LICENSED:
            licensed_structures.append(s)
        else:
            total_structures.append(s)

    calls: list[TaskCall] = []

    # ── Licensed tasks ───────────────────────────────────────────────────────
    if licensed_enabled:
        # heartchambers_highres covers aorta + pulmonary_artery in one run
        hc_structs = [s for s in licensed_structures if _LICENSED[s] == "heartchambers_highres"]
        if hc_structs:
            calls.append(TaskCall(
                task="heartchambers_highres",
                roi_subset=None,
                output_structures=hc_structs,
            ))

        ca_structs = [s for s in licensed_structures if _LICENSED[s] == "coronary_arteries"]
        if ca_structs:
            calls.append(TaskCall(
                task="coronary_arteries",
                roi_subset=None,
                output_structures=ca_structs,
            ))
    else:
        # Skip licensed; warn caller via empty output
        pass

    # ── Open total task ───────────────────────────────────────────────────────
    if total_structures:
        calls.append(TaskCall(
            task="total",
            roi_subset=total_structures,
            output_structures=total_structures,
        ))

    return calls

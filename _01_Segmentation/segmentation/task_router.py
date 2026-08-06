from __future__ import annotations

from dataclasses import dataclass, field


# Procedure codes where heartchambers_highres is appropriate (ECG-gated cardiac CTs)
_CARDIAC_CODES: frozenset[str] = frozenset({"TACCOR", "TACCRG"})

# 1-slice degenerate/scout series kill TotalSegmentator workers; require at least 5
MIN_SLICES_FOR_SEGMENTATION: int = 5
# Below this, total task uses fast=True; licensed tasks (coronary/heartchambers)
# are skipped entirely — they reject --fast and need a full diagnostic volume
SMALL_VOLUME_THRESHOLD: int = 30


@dataclass
class TaskCall:
    task: str
    # None → no subset filter (heartchambers_highres / coronary_arteries run fully)
    roi_subset: list[str] | None
    # which output .nii.gz files to expect / copy to the series dir
    output_structures: list[str] = field(default_factory=list)
    # force 3mm fast model regardless of global setting (needed for small volumes)
    force_fast: bool = False
    # disable body-seg crop (not useful / harmful for small volumes)
    force_no_body_seg: bool = False


def build_task_calls(
    structures: list[str],
    licensed_enabled: bool,
    procedure_code: str = "",
    instance_count: int = 9999,
) -> list[TaskCall]:
    """Map a list of structure names to the minimal set of TotalSegmentator calls.

    Series with <5 slices (scout/topogram) are skipped.
    Series with <30 slices (monitoring) run with fast=True to work with limited z-context.
    Aorta uses heartchambers_highres only for ECG-gated cardiac protocols.
    """
    if instance_count < MIN_SLICES_FOR_SEGMENTATION:
        return []

    # Small volumes (monitoring): force fast model + no body-seg crop
    is_small = instance_count < SMALL_VOLUME_THRESHOLD
    is_cardiac = procedure_code.upper() in _CARDIAC_CODES
    hc_structs: list[str] = []
    ca_structs: list[str] = []
    total_structs: list[str] = []

    for s in structures:
        if s == "coronary_arteries" and licensed_enabled:
            ca_structs.append(s)
        elif s == "pulmonary_artery" and licensed_enabled:
            # pulmonary_artery only has a dedicated label in heartchambers_highres
            hc_structs.append(s)
        elif s == "aorta" and licensed_enabled and is_cardiac:
            # heartchambers_highres is only better for ECG-gated cardiac scans
            hc_structs.append(s)
        else:
            # aorta on non-cardiac protocols → total task (trained on diverse CTs)
            total_structs.append(s)

    calls: list[TaskCall] = []

    # ── Licensed tasks ────────────────────────────────────────────────────────
    # heartchambers_highres and coronary_arteries reject --fast and require enough
    # z-context to run; skip them on monitoring/bolus tracking volumes (<30 slices).
    if licensed_enabled and not is_small:
        if hc_structs:
            calls.append(TaskCall(
                task="heartchambers_highres",
                roi_subset=None,
                output_structures=hc_structs,
                force_fast=False,
                force_no_body_seg=False,
            ))
        if ca_structs:
            calls.append(TaskCall(
                task="coronary_arteries",
                roi_subset=None,
                output_structures=ca_structs,
                force_fast=False,
                force_no_body_seg=False,
            ))

    # ── Open total task ───────────────────────────────────────────────────────
    if total_structs:
        calls.append(TaskCall(
            task="total",
            roi_subset=total_structs,
            output_structures=total_structs,
            force_fast=is_small,
            force_no_body_seg=is_small,
        ))

    return calls

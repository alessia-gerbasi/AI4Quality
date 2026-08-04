from __future__ import annotations

from pathlib import Path

from segmentation.task_router import TaskCall  # noqa: F401 – used by callers via type hints


def run_task_calls(
    ct_nii: Path,
    series_out_dir: Path,
    task_calls: list[TaskCall],  # noqa: F401 – used by callers via type hints
    device: str,
    fast: bool,
    body_seg: bool = True,
) -> list[str]:
    """Run each TaskCall and write structure files directly to series_out_dir.

    Returns list of structure filenames that were successfully written.
    """
    try:
        from totalsegmentator.python_api import totalsegmentator  # type: ignore
    except ImportError as exc:
        raise RuntimeError("TotalSegmentator Python package not available") from exc

    series_out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for call in task_calls:
        kwargs: dict = dict(
            input=str(ct_nii),
            output=str(series_out_dir),
            task=call.task,
            device=device,
            fast=call.force_fast or fast,        # small volumes always use fast model
            body_seg=False if call.force_no_body_seg else body_seg,
            ml=False,
            nr_thr_saving=1,
        )
        if call.roi_subset is not None:
            kwargs["roi_subset"] = call.roi_subset

        totalsegmentator(**kwargs)

        for struct in call.output_structures:
            dst = series_out_dir / f"{struct}.nii.gz"
            if dst.exists():
                written.append(dst.name)

    return written

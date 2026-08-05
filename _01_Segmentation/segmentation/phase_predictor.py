from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def predict_phase(
    ct_nii: Path,
    out_json: Path,
    *,
    timeout_seconds: int | None = 600,
    device: str | None = None,
    quiet: bool = True,
) -> dict:
    """Run totalseg_get_phase and write phase.json; returns parsed dict."""
    binary = shutil.which("totalseg_get_phase")
    if binary is None:
        raise RuntimeError("totalseg_get_phase not found on PATH")

    cmd = [binary, "-i", str(ct_nii), "-o", str(out_json)]
    if device:
        normalized_device = str(device).strip().lower()
        if normalized_device in {"cuda", "cuda:0"}:
            normalized_device = "gpu"
        else:
            match = re.fullmatch(r"cuda:(\d+)", normalized_device)
            if match:
                normalized_device = f"gpu:{match.group(1)}"
        cmd.extend(["-d", normalized_device])
    if quiet:
        cmd.append("-q")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"totalseg_get_phase timed out after {timeout_seconds}s"
        ) from exc

    if proc.returncode != 0:
        raise RuntimeError(f"totalseg_get_phase failed: {proc.stderr.strip()}")

    if not out_json.exists():
        raise RuntimeError(f"totalseg_get_phase did not write {out_json}")

    with open(out_json) as fh:
        return json.load(fh)

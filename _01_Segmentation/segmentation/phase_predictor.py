from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def predict_phase(ct_nii: Path, out_json: Path) -> dict:
    """Run totalseg_get_phase and write phase.json; returns parsed dict."""
    binary = shutil.which("totalseg_get_phase")
    if binary is None:
        raise RuntimeError("totalseg_get_phase not found on PATH")

    proc = subprocess.run(
        [binary, "-i", str(ct_nii), "-o", str(out_json)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"totalseg_get_phase failed: {proc.stderr.strip()}")

    if not out_json.exists():
        raise RuntimeError(f"totalseg_get_phase did not write {out_json}")

    with open(out_json) as fh:
        return json.load(fh)

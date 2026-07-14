# Preprocessing Instructions

This document summarizes the recommended workflow for `_00_Preprocessing`.

## 1) Environment

Activate your project environment first (example):

```bash
conda activate torch-gpu
```

Run all commands from project root:

```bash
cd /data/alessia.gerbasi/AI4Quality
```

## 2) Main Pipeline Run

Run full preprocessing with default config:

```bash
python _00_Preprocessing/main.py --config _00_Preprocessing/config/defaults.yaml
```

Useful options:

- Limit scanned CT folders:

```bash
python _00_Preprocessing/main.py --config _00_Preprocessing/config/defaults.yaml --max-ct 20
```

- Dry run (no output writes):

```bash
python _00_Preprocessing/main.py --config _00_Preprocessing/config/defaults.yaml --dry-run
```

## 3) Main Artifacts

Written to `_00_Preprocessing/OUTPUTS/`.

Core files:
- `decisions.csv`
- `retained_series.csv`
- `retained_series_vascular_filtered.csv`
- `retained_series_parenchymal_filtered.csv`
- `retained_series_unified_filtered.csv`
- `merged_lineage.csv`
- `run_summary.json`
- `run_log.jsonl`

## 4) Collapsed Split Volumes (QC)

By default, collapsed-volume writing is disabled in config for speed.

Use the standalone tool to generate collapsed volumes from existing `decisions.csv`:

```bash
python _00_Preprocessing/merge/collapse_split_volumes.py \
  --decisions-csv _00_Preprocessing/OUTPUTS/decisions.csv \
  --ct-ids 100 \
  --no-skip-existing
```

Note: the script auto-detects `OUTPUTS/decisions.csv` first and falls back to `artifacts/decisions.csv` for older runs.

Output naming:
- `<series_name>_collapsed.nii.gz`

Output location:
- In the DICOM exam tree, at the same parent folder containing split series folders.

## 5) Optional: Trigger collapse during main run

Normally not recommended for large runs (slower), but available if needed:

```bash
python _00_Preprocessing/main.py \
  --config _00_Preprocessing/config/defaults.yaml \
  --write-collapsed-volumes \
  --collapse-ct-ids 100 \
  --collapse-overwrite
```

## 6) Recommended Workflow

1. Run main preprocessing (fast path, no collapse).
2. Inspect CSV outputs in `_00_Preprocessing/OUTPUTS/`.
3. For selected cases, run standalone collapse QC script.
4. Open generated `_collapsed.nii.gz` in your viewer for visual verification.

## 7) Troubleshooting

- If you suspect stale `_collapsed` output, rerun with `--no-skip-existing`.
- If selection output differs from expectation, check:
  - `_00_Preprocessing/config/defaults.yaml`
  - `_00_Preprocessing/SELECTION_RULES_RECAP.md`
  - `_00_Preprocessing/OUTPUTS/run_log.jsonl`

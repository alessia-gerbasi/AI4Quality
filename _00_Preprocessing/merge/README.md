# Merge Utilities

This folder contains utilities related to split-series detection and collapse.

## Standalone Script: `collapse_split_volumes.py`

Use this script to generate collapsed NIfTI volumes for split DICOM series **without running the full preprocessing pipeline**.

It reads an existing `decisions.csv` and writes one NIfTI per merged group:
- output filename: `<series_name>_collapsed.nii.gz`
- output location: same parent folder that contains the split series folders

### Typical use

From the project root:

```bash
python _00_Preprocessing/merge/collapse_split_volumes.py \
  --decisions-csv _00_Preprocessing/OUTPUTS/decisions.csv \
  --ct-ids 100 \
  --no-skip-existing
```

### Arguments

- `--decisions-csv`:
  Path to input `decisions.csv`.
  Default behavior: auto-detect `_00_Preprocessing/OUTPUTS/decisions.csv` and fallback to `_00_Preprocessing/artifacts/decisions.csv`.

- `--ct-ids`:
  Optional comma-separated CT IDs to process (for example: `100,375`).

- `--max-groups`:
  Optional cap on merge groups to process.

- `--include-rejected`:
  Include rows with rejected status. By default, only accepted rows are used.

- `--no-skip-existing`:
  Overwrite existing `_collapsed.nii.gz` files.

- `--json`:
  Print summary as JSON.

### Fast QC examples

1. Process one exam and overwrite existing file:

```bash
python _00_Preprocessing/merge/collapse_split_volumes.py \
  --ct-ids 100 \
  --no-skip-existing
```

2. Process a short batch of groups:

```bash
python _00_Preprocessing/merge/collapse_split_volumes.py \
  --max-groups 10
```

3. Print machine-readable output:

```bash
python _00_Preprocessing/merge/collapse_split_volumes.py \
  --ct-ids 100 \
  --json
```

### Notes

- The script uses `SimpleITK` for robust DICOM-to-NIfTI conversion.
- It is intended for QC and targeted regeneration of collapsed volumes.
- For full pipeline outputs (selection CSVs and summaries), use `_00_Preprocessing/main.py`.

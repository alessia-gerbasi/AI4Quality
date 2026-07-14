# AI4Quality

Modular repository for CT quality workflows.

## Current scope

- `_00_Preprocessing`: DICOM preprocessing pipeline for metadata extraction, selection, split-series reconstruction metadata, and export artifacts.
- `_01_QC`: Reserved for quality control modules.
- `_02_Reporting`: Reserved for reporting modules.

## Quick start

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install -e .
```

3. Run preprocessing (dry run example):

```bash
python _00_Preprocessing/main.py --config _00_Preprocessing/config/defaults.yaml --dry-run --max-ct 20
```

## Notes

- Business metadata authority (Scanner and Order Procedure) is Excel-based.
- Procedure filtering uses configurable accepted codes.
- Selector precedence is configurable and defaults to exclusion-wins.

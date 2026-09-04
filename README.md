# AI4Quality

Modular repository for CT quality workflows.

## Current scope

- `_00_Preprocessing`: DICOM preprocessing pipeline for metadata extraction, selection, split-series reconstruction metadata, and export artifacts.
- `_01_Segmentation`: DICOM-to-NIfTI conversion plus TotalSegmentator ROI extraction.
- `_02_QualityCheck`: HU quality evaluation per ROI with configurable rules and visual outputs.
- `_06_Dashboard`: Final clinical dashboard combining QC, RCA, warnings, injector data, and pre-generated LLM recommendations.
- `_03_Reporting`: Reserved for reporting modules.

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

4. Run HU quality check (example):

```bash
python _02_QualityCheck/main.py \
	--csv _00_Preprocessing/OUTPUTS/retained_series_unified_filtered.csv \
	--rules config/common/ct_protocols.yaml \
	--nii-root /data/alessia.gerbasi/DATA/CDI_NEXO_072026/2_nii \
	--output-dir _02_QualityCheck/OUTPUTS
```

5. Launch the Streamlit dashboard:

```bash
streamlit run _02_QualityCheck/dashboard.py
```

6. Generate the final LLM recommendations in background, then launch the final clinical dashboard:

```bash
python _04_Recommendations/generate_recommendations.py
streamlit run _06_Dashboard/dashboard.py
```

Generated artifacts:
- `_02_QualityCheck/OUTPUTS/roi_hu_qc_results.csv` (ROI-level details)
- `_02_QualityCheck/OUTPUTS/roi_hu_qc_summary.csv` (series-level summary)
- `_02_QualityCheck/OUTPUTS/patient_hu_qc_summary.csv` (patient-level summary)
- `_02_QualityCheck/OUTPUTS/aggregate_hu_qc_stats.csv` (aggregate statistics)
- `_02_QualityCheck/OUTPUTS/images/*.png` (per-series ROI borders + semicircle quality gauge)

## Notes

- Business metadata authority (Scanner and Order Procedure) is Excel-based.
- Procedure filtering uses configurable accepted codes.
- Selector precedence is configurable and defaults to exclusion-wins.

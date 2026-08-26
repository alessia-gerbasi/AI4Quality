# AI4Quality Pipeline Count Audit

Run the general audit from the repository root:

```bash
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python scripts/pipeline_count_audit.py
```

Use `--json audit.json` to save machine-readable results.

## Current snapshot

| Stage | Rows | Patients | Patient-series entities | Meaning |
|---|---:|---:|---:|---|
| Preprocessing decisions | 6,366 | 387 | 6,366 | Every discovered series decision, accepted or rejected |
| Accepted retained series | 955 | 212 | 955 | Accepted representatives after preprocessing merging/collapse |
| Unified QC input | 521 | 212 | 521 | Final retained series passed to the QC stage |
| QC ROI evaluations | 468 | 204 | 334 | One row per measured ROI; multiple rows can belong to one series |
| QC series summary | 336 | 206 | 336 | One row per QC-evaluated series result |
| QC patient summary | 206 | 206 | n/a | One row per patient represented by QC series results |
| RCA results | 400 | 83 | 100 | 100 critical series evaluated by 4 RCA schemas |
| SQLite `exams` | 384 | 384 | n/a | Linked exams with valid anonymization matches |
| SQLite `series` | 521 | 212 | 521 | Retained preprocessing series |
| SQLite `image_quality` | 468 | 204 | 334 | QC ROI evaluations |
| SQLite `patient_warnings` | 206 | 206 | n/a | Patient-level enhancement and segmentation warnings |
| SQLite `rca` | 400 | 83 | 100 | RCA schema results |
| SQLite `recommendations` | 204 | 204 | n/a | One current stored LLM recommendation per generated patient |

The audit counts a series by `series_path` where available, otherwise by `(ct_id, series_folder)`. This matters because folder names can repeat for different patients.

## Why counts differ

- Preprocessing decisions include rejected data and therefore have more rows than retained outputs.
- Accepted retained series are reduced by preprocessing merge/collapse logic; the unified output applies the final procedure, phase, support-only, and deduplication rules.
- QC does not necessarily evaluate every unified input series. In this snapshot, 187 of 521 retained series have no QC detail row. The QC dashboard and final recommendations use QC-evaluated series where applicable.
- QC detail is at ROI level: 468 ROI rows collapse to 334 patient-series entities. One venous series with liver and spleen evaluations therefore contributes two rows, not two series.
- The QC series summary contains 336 rows because the QC run can retain more than one evaluation row for a patient-series/metric combination. Its 206 patients are the patient-level QC population.
- RCA only processes critical QC series. There are 100 critical patient-series entities and four schema runs, producing 400 RCA rows but only 83 patients.
- The 123 QC patients without RCA results have no critical series requiring RCA; this is expected.
- The database has 384 linked exams because unmatched injection-history indices are excluded. They cannot be associated with an anonymized `ct_id`.
- Recommendations are generated for the union of QC/RCA patient IDs. The current 204 rows mean 204 patients have stored recommendations; patients represented only in a summary but not in QC detail are not automatically generated unless included by the generator's source population.
- Do not combine current outputs with `OUTPUTS_smoke`, `OUTPUTS_old`, or historical RCA snapshots when counting a run.

## Stage commands

From `/data/alessia.gerbasi/AI4Quality`:

```bash
# Quality check, including patient summary and warnings
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python _02_QualityCheck/main.py \
  --output-dir _02_QualityCheck/OUTPUTS

# RCA, one command per schema
for schema in dose_schema_v1 other_schema_v1 protocol_schema_v1 timing_schema_v1; do
  /data/alessia.gerbasi/miniconda3/envs/ctq/bin/python \
    _03_RootCauseAnalysis/batch_analysis.py --schema "$schema"
done

# Rebuild normalized SQLite source tables and generate all LLM recommendations
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python \
  _04_Recommendations/generate_recommendations.py

# Audit the result
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python scripts/pipeline_count_audit.py
```

The recommendation generator rebuilds the source database before generation. It stores no fallback output and stops if Ollama fails.

## Important caveat

The QC summary can include patients/series whose detail rows are absent because summary data is based on completed `SeriesEvaluation` objects. When exact measured ROI counts are required, use `roi_hu_qc_results.csv`; when patient-level warning counts are required, use `patient_hu_qc_summary.csv`.

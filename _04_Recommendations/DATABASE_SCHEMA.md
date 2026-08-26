# Recommendation Database

Database file: `data/ai4quality_recommendations.sqlite`

The database is rebuilt by `build_database.py` from the current QC CSV, RCA aggregate CSV, patient QC summary, preprocessing series CSV, and linked injector spreadsheets. The dashboard is not required to build or refresh the source tables.

## Tables

### `exams`
One row per linked patient exam.

- `ct_id`: anonymized patient/exam identifier; primary key.
- `ct_folder`: source CT folder derived from `ct_id`.
- `patient_name`: anonymized patient name from injection history.
- `injection_index`: linked injection-history identifier.
- `patient_data_json`: complete linked injection-history row for audit/detail fields.

Unmatched injection-history rows are excluded. They are not exams in this database, which prevents meaningless `NULL ct_id` rows.

### `series`
One row per retained preprocessing series.

- `ct_id`, `series_folder`: patient and series identity; together primary key.
- `phase_name`: normalized phase, such as `arteriosa` or `venosa`.
- `procedure_code`: protocol/procedure code.
- `scanner`: scanner description.
- `series_data_json`: complete preprocessing row for fields not promoted to columns.

This table can contain retained series that were not evaluated by QC. Use `image_quality` to restrict queries to QC-evaluated series.

### `image_quality`
One row per QC ROI evaluation.

- `ct_id`, `series_folder`: patient and evaluated series.
- `roi_name`: evaluated organ or vessel.
- `metric_name`: metric used, such as `HU_arteriosa` or `HU_delta_venosa`.
- `status`: QC result: `optimal`, `acceptable_low`, `acceptable_high`, `critical_low`, `critical_high`, or `missing`.
- `evaluated_value`: value used for scoring.
- `mean_hu`, `mean_hu_precontrast`: measured values when available.
- `qc_data_json`: complete QC row, including thresholds, warnings, and image paths.

Multiple rows for one series are expected when several ROIs are evaluated.

### `rca`
One row per RCA schema result for a critical series.

- `ct_id`, `series_folder`: patient and affected series.
- `rca_schema`: schema that produced the result.
- `rca_label`, `rca_diagnoses`: diagnosis label(s).
- `rca_explanation`: evidence-based explanation.
- `rca_notes`: interpretable injection notes.
- `rca_recommendations`: RCA protocol recommendations.
- `rca_data_json`: complete RCA row, including variables and decision path.

### `patient_warnings`
One row per patient-level QC summary.

- `ct_id`: primary key.
- `warning_priority`: enhancement priority: `none`, `low`, `medium`, or `high`.
- `warning`, `warning_evidence`: enhancement warning and supporting series/ROI evidence.
- `segmentation_warning`, `segmentation_warning_evidence`: separate missing-ROI warning and evidence.
- `warning_data_json`: complete patient QC summary row.

### `injector_data`
One row per linked injection-history record.

- `ct_id`, `injection_index`: linked patient and injection identifiers.
- `data_json`: complete injection-history row.

Unmatched injection-history records are excluded because they cannot be associated with an anonymized patient.

### `recommendations`
One current generated recommendation per `(ct_id, scope, model)`.

- `ct_id`, `series_folder`, `scope`: patient and recommendation scope. Current automated generation uses `scope = 'exam'` and `series_folder = NULL`.
- `model`: Ollama model name.
- `source`: LLM source label, for example `llm (qwen2.5:7b)`.
- `recommendation`: generated text.
- `input_json`: exact patient input sent to the LLM.
- `created_at`: generation timestamp.

The unique index prevents repeated dashboard clicks or batch runs from creating duplicate current rows for the same patient/model/scope.

## Useful test queries

Run from the repository root:

```bash
sqlite3 _04_Recommendations/data/ai4quality_recommendations.sqlite
```

Database size and null audit:

```sql
SELECT 'exams' AS table_name, COUNT(*) AS rows FROM exams
UNION ALL SELECT 'series', COUNT(*) FROM series
UNION ALL SELECT 'image_quality', COUNT(*) FROM image_quality
UNION ALL SELECT 'rca', COUNT(*) FROM rca
UNION ALL SELECT 'patient_warnings', COUNT(*) FROM patient_warnings
UNION ALL SELECT 'recommendations', COUNT(*) FROM recommendations;

SELECT COUNT(*) AS orphan_exams FROM exams WHERE ct_id IS NULL;
SELECT COUNT(*) AS duplicate_recommendations
FROM (
  SELECT ct_id, scope, model FROM recommendations
  GROUP BY ct_id, scope, model HAVING COUNT(*) > 1
);
```

Patient warning overview:

```sql
SELECT ct_id, warning_priority, warning, segmentation_warning
FROM patient_warnings
WHERE warning_priority <> 'none'
   OR segmentation_warning IS NOT NULL
ORDER BY CASE warning_priority
  WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, ct_id;
```

QC-evaluated series only, excluding preprocessing-only monitoring series:

```sql
SELECT DISTINCT s.ct_id, s.series_folder, s.phase_name, s.procedure_code
FROM series AS s
JOIN image_quality AS q USING (ct_id, series_folder)
ORDER BY s.ct_id, s.phase_name, s.series_folder;
```

Patient 472 missing segmentation evidence:

```sql
SELECT ct_id, segmentation_warning, segmentation_warning_evidence
FROM patient_warnings
WHERE ct_id = '472';
```

Critical QC findings with patient priority:

```sql
SELECT q.ct_id, q.series_folder, q.roi_name, q.status,
       q.evaluated_value, w.warning_priority
FROM image_quality AS q
JOIN patient_warnings AS w USING (ct_id)
WHERE q.status IN ('critical_low', 'critical_high')
ORDER BY CASE w.warning_priority
  WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END,
  q.ct_id;
```

Latest stored LLM recommendation for one patient:

```sql
SELECT ct_id, model, source, created_at, recommendation
FROM recommendations
WHERE ct_id = '472' AND scope = 'exam'
ORDER BY created_at DESC
LIMIT 1;
```

Exit SQLite with `.quit`.

# Data Selection Rules Recap

This document summarizes the selection logic currently implemented in the preprocessing pipeline.

## 1) Pipeline Stages

The selection flow is applied in this order:

1. Base series eligibility and labeling (accepted/rejected + phase_name).
2. Retained series construction (accepted rows only, with merged groups collapsed).
3. Vascular policy selection.
4. Parenchymal policy selection.
5. Unified output creation with CT_type normalization and deduplication by series_path.

---

## 2) Base Eligibility Rules

Base eligibility is driven by the main selector.

### 2.1 Procedure code acceptance

A series is rejected if:
- Procedure code is missing.
- Procedure code is not in selection.accepted_procedure_codes.

### 2.2 Phase name extraction

phase_name is assigned if one of these keywords appears in series description/folder text:
- venosa
- arteriosa
- monitoring
- base
- basale

### 2.3 Forced-keep override

If any force-accept keyword is found, the series is accepted even if an exclude keyword also matches.

Current forced-keep keywords:
- monitoring

This produces reason_code = forced_keep_keyword.

### 2.4 Exclude keywords

If no forced-keep keyword matched, any exclude keyword match rejects the series.

Current exclude list:
- mpr
- nan
- topogram
- snapshot
- none
- vrt
- encefalo
- mip
- wil
- movie
- tardiva
- tor
- I7
- prona
- neck
- min
- osteo

### 2.5 Include keywords

Current include list is empty, so include-based acceptance is not used.

---

## 3) Retained Series Construction

From accepted rows only:

- merge_status != merged_source: kept as-is.
- merge_status == merged_source: grouped by merge_group_id and collapsed to one merged_final row.

For merged_final rows:
- Representative metadata comes from the first ordered part.
- merge_part_count is set to max detected part count.
- instance_count is summed across all grouped parts.

---

## 4) Procedure Code Groups

Configured in selection.procedure_groups.

### 4.1 Vascular codes
- TACCOR
- TACAAO
- TACAAT
- TACCRG
- TACADI
- TACATD
- TACAGC
- TACCRA
- TACAGE
- TACAGI
- TACACP
- TACCUO
- TACAAR
- TACAGA

### 4.2 Parenchymal codes
- TACPEC
- TACPEM
- TACTCG
- TACADC
- TACBAC
- TACANC
- TACADN
- TACTFA
- TACPEV
- TACPEL
- TACREC
- TACATC
- TACREN
- TACURO

---

## 5) Vascular Selection Policy

Applied to retained series, grouped by ct_id.

### 5.1 Candidate scope

- candidate_status must be accepted.
- procedure_code_value must be in vascular allowed_procedure_codes.
- premonitoring and monitoring are retained as dedicated buckets when present.
- after required buckets, exactly one additional vascular series is selected with the vascular ranking criteria.

### 5.2 Ranking criteria (in order)

1. vascular_phase
   - venosa > arteriosa > other
2. phase
   - bestdiast > bestsyst > explicit RR% > other
3. kernel
   - i26f > i30f > b35f > i36f > i50f > i70f > other
4. thickness
   - 0.6 > 1.5 > 3.0 > other
5. hr
   - non_hr > hr
6. rr
   - tie-breaker using distance to configured RR targets:
     - bestdiast target: 70-80
     - bestsyst target: 30-40
7. dose
   - 20 > 10 > 5 > other

If still tied, deterministic tie-breakers are used:
- acquisition_time
- series_folder

Output files:
- retained_series_vascular_filtered.csv
- retained_series_vascular_filtered_summary.md

---

## 6) Parenchymal Selection Policy

Applied to retained series, grouped by ct_id and by normalized phase.

### 6.1 Candidate scope

- candidate_status must be accepted.
- procedure_code_value must be in parenchymal allowed_procedure_codes.
- monitoring rows are excluded from ranking candidates.
- monitoring rows are still kept unchanged in parenchymal output if present.

### 6.2 Phase normalization

Rows are mapped to canonical phase groups using aliases.

Canonical phases used:
- pre_contrast
- arterial
- venous
- monitoring

Aliases include:
- pre_contrast: pre-contrast, basale, base, non-contrast, addome
- arterial: arteriosa, arterial
- venous: venosa, venous
- monitoring: monitoring

Unknown phases are excluded.

Current setting:
- drop_precontrast_when_arterial_and_venous is disabled.
  - This means pre-contrast is retained even when arterial and venous also exist.

### 6.3 Ranking criteria (in order)

1. kernel
   - br40 > br44 > br48 > br56 > br64 > other
2. reconstruction_family
   - standard > iterative > spectral_mono > material_map > other
3. non_bone
   - non_bone > bone_like
4. matrix
   - 512 > 1024 > other
5. thickness
   - 2.0 > 3.0 > 1.0 > other
6. dose
   - 20 > 10 > 5 > other
7. acquisition_size
   - standard > thin > submillimetric > other

If still tied, deterministic tie-breakers are used:
- acquisition_time
- series_folder

Output files:
- retained_series_parenchymal_filtered.csv
- retained_series_parenchymal_filtered_summary.md

---

## 7) Unified Output Rules

The unified output is built by concatenating:
- vascular filtered rows (CT_type initialized as vascular)
- parenchymal filtered rows (CT_type initialized as parenchymal)

Then series-level normalization/deduplication is applied:

1. CT_type normalization by text content:
   - premonitoring keyword -> CT_type = premonitoring
   - base or basale keyword -> CT_type = base
   - monitoring keyword -> CT_type = monitoring
   - otherwise keep original CT_type (vascular/parenchymal)

2. Deduplication key:
   - series_path

3. If duplicate series_path appears, keep the highest-priority CT_type:
   - monitoring
   - premonitoring
   - base
   - parenchymal
   - vascular

Output file:
- retained_series_unified_filtered.csv

---

## 8) Practical Result of Current Configuration

With current settings:
- Monitoring and premonitoring are force-accepted at base selection level.
- Monitoring is preserved in both policy outputs as kept rows.
- Unified output collapses duplicates by series_path and assigns one final CT_type.
- Basale/base rows are labeled with phase_name basale/base when detected and normalized to CT_type base in unified output.

---

## 9) Main Configuration Anchors

Rules are configured primarily in:
- _00_Preprocessing/config/defaults.yaml

Execution points are in:
- _00_Preprocessing/series_selectors/keyword_selector.py
- _00_Preprocessing/reporting/vascular_filter.py
- _00_Preprocessing/reporting/export_csv.py

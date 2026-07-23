# Vascular Series Selection Summary

## Configurable Rules

```yaml
group_field: ct_id
keep_monitoring: true
candidate_status: accepted
exclude_monitoring: false
keep_additional_distinct_names: false
select_one_best_remaining: false
required_phase_buckets:
- aorta
- premonitoring
- monitoring
allowed_procedure_codes:
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
- TACTON
output_csv: retained_series_vascular_filtered.csv
summary_file: retained_series_vascular_filtered_summary.md
monitoring:
  fields:
  - series_name
  - series_folder
  - phase_name
  patterns:
  - (?i)monitoring
criteria:
- name: vascular_phase
  fields:
  - phase_name
  - series_name
  - series_folder
  ordered_labels:
  - label: venosa
    patterns:
    - (?i)\bvenosa\b
  - label: arteriosa
    patterns:
    - (?i)\barteriosa\b
  - label: other
    patterns: []
- name: phase
  fields:
  - series_name
  - series_folder
  - phase_name
  ordered_labels:
  - label: bestdiast
    patterns:
    - (?i)bestdiast
  - label: bestsyst
    patterns:
    - (?i)bestsyst
  - label: explicit_rr
    patterns:
    - (?i)(?:^|_|\b)\d{1,3}(?:[\.,]\d+)?(?:\s*|_)?%
  - label: other
    patterns: []
  rr_targets:
    bestdiast:
    - 70
    - 80
    bestsyst:
    - 30
    - 40
  rr_extraction_patterns:
  - (?i)(?:^|_|\b)(\d{1,3})(?:[\.,]\d+)?(?:\s*|_)?%
- name: kernel
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: i26f
    patterns:
    - (?i)\bi26f\b
  - label: i30f
    patterns:
    - (?i)\bi30f\b
  - label: b35f
    patterns:
    - (?i)\bb35f\b
  - label: i36f
    patterns:
    - (?i)\bi36f\b
  - label: i50f
    patterns:
    - (?i)\bi50f\b
  - label: i70f
    patterns:
    - (?i)\bi70f\b
  - label: other
    patterns: []
- name: thickness
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: 0.6
    patterns:
    - (?i)(?:^|_|\b)0[,_\.]6(?:_|\b)
  - label: 1.5
    patterns:
    - (?i)(?:^|_|\b)1[,_\.]5(?:_|\b)
  - label: 3.0
    patterns:
    - (?i)(?:^|_|\b)3[,_\.]0(?:_|\b)
  - label: other
    patterns: []
- name: hr
  fields:
  - series_name
  - series_folder
  hr_patterns:
  - (?i)(?:^|_)hr(?:_|$)
- name: rr
  fields:
  - series_name
  - series_folder
  rr_extraction_patterns:
  - (?i)(?:^|_|\b)(\d{1,3})(?:[\.,]\d+)?(?:\s*|_)?%
- name: dose
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: 20
    patterns:
    - (?i)(?:^|_)20(?:_|$)
  - label: 10
    patterns:
    - (?i)(?:^|_)10(?:_|$)
  - label: 5
    patterns:
    - (?i)(?:^|_)5(?:_|$)
  - label: other
    patterns: []
keep_additional_name_patterns:
- angio
policy_name: vascular
```

## Selection Logic

- Group rows by the configured exam field.
- Keep any monitoring rows unchanged when they match the configured monitoring patterns.
- Rank the remaining eligible vascular series lexicographically by the configured criteria order.
- Use RR% only as a late tie-breaker, with target ranges configured per phase.
- Break exact ties deterministically using acquisition time and series folder.

## Selection Results

- Exams processed: 12
- Groups processed: 12
- Selected vascular series: 22
- Monitoring rows kept: 10
- Exams without an eligible vascular series: 0

## Per-Exam Selection

### Exam 1 - ethel_harris

Selected series:
- Angio Embolia  1.0  I26f  3 (11_angio_embolia__1_0__i26f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 10 - alesha_williams

Selected series:
- Angio Embolia 0,80 Bv44 Q4 iMAR Matrix 512 (401_angio_embolia_0_80_bv44_q4_imar_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (301_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (201_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 11 - alfredo_wood

Selected series:
- Angio Embolia 0,80 Bv56 Q4 ax Matrix 541 (701_angio_embolia_0_80_bv56_q4_ax_matrix_541)
- Monitoring 5,00 Br36 Matrix 512 (601_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 12 - julius_dennis

Selected series:
- Angio Embolia  1.0  I26f  3 (7_angio_embolia__1_0__i26f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 2 - brian_hall

Selected series:
- Angio Embolia  1.0  I26f  3 (10_angio_embolia__1_0__i26f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 3 - richard_hodges

Selected series:
- Angio Embolia 0,80 Bv44 Q4 Matrix 768 (901_angio_embolia_0_80_bv44_q4_matrix_768)
- Monitoring 5,00 Br36 Matrix 512 (801_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 4 - john_palma

Selected series:
- Angio Embolia  1.0  I26f  3 (8_angio_embolia__1_0__i26f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 5 - anthony_shoemaker

Selected series:
- Angio Embolia  1.0  I26f  3 (9_angio_embolia__1_0__i26f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 6 - joseph_lee

Selected series:
- Angio Embolia 0,80 Bv44 Q4 Matrix 512 (801_angio_embolia_0_80_bv44_q4_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (701_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (201_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 7 - diane_ashley

Selected series:
- Angio Embolia  1.0  I26f  3 (9_angio_embolia__1_0__i26f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 8 - peter_gonzalez

Selected series:
- Angio Embolia  1.0  I26f  3 (10_angio_embolia__1_0__i26f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 9 - james_vargas

Selected series:
- Angio Embolia 0,80 Bv44 Q4 Matrix 512 (401_angio_embolia_0_80_bv44_q4_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (301_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (201_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta

# Parenchymal Series Selection Summary

## Configurable Rules

```yaml
enabled: true
group_field: ct_id
group_by_phase: true
keep_monitoring: true
exclude_monitoring: false
keep_additional_distinct_names: false
required_phase_buckets:
- pre_contrast
- premonitoring
- monitoring
- venous
- arterial
phase_field: phase_name
phase_allowlist:
- pre_contrast
- basale
- premonitoring
- arterial
- arteriosa
- venous
- venosa
- monitoring
exclude_unknown_phase: true
drop_precontrast_when_arterial_and_venous:
  enabled: false
  precontrast_key: pre_contrast
  arterial_key: arterial
  venous_key: venous
phase_order:
- pre_contrast
- arterial
- venous
phase_aliases:
  pre_contrast:
  - (?i)pre[\s_\-]?contrast
  - (?i)basale
  - (?i)base
  - (?i)non[\s_\-]?contrast
  - (?i)(?<![a-zA-Z])addome(?![a-zA-Z])
  basale:
  - (?i)basale
  - (?i)base
  premonitoring:
  - (?i)premonitoring
  arterial:
  - (?i)arteriosa
  - (?i)arterial
  arteriosa:
  - (?i)arteriosa
  venous:
  - (?i)venosa
  - (?i)venous
  venosa:
  - (?i)venosa
  monitoring:
  - (?i)monitoring
candidate_status: accepted
monitoring:
  fields:
  - series_name
  - series_folder
  - phase_name
  patterns:
  - (?i)monitoring
allowed_procedure_codes:
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
output_csv: retained_series_parenchymal_filtered.csv
summary_file: retained_series_parenchymal_filtered_summary.md
criteria:
- name: kernel
  description: Prefer softer kernels (lower kernel number).
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: br40
    patterns:
    - (?i)\bbr40\b
  - label: br44
    patterns:
    - (?i)\bbr44\b
  - label: br48
    patterns:
    - (?i)\bbr48\b
  - label: br56
    patterns:
    - (?i)\bbr56\b
  - label: br64
    patterns:
    - (?i)\bbr64\b
  - label: other
    patterns: []
- name: reconstruction_family
  description: Standard > iterative > spectral/monoenergetic > material maps.
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: standard
    patterns:
    - (?i)\bstandard\b
    - (?i)\bstd\b
  - label: iterative
    patterns:
    - (?i)\b(admire|asir|asir-v|mbir|iterative)\b
  - label: spectral_mono
    patterns:
    - (?i)\b(me|monoe|monoenergetic)\b
  - label: material_map
    patterns:
    - (?i)\b(vnc|iodine|zeff|electron[\s_\-]?density)\b
  - label: other
    patterns: []
- name: non_bone
  description: non-osteo > osteo/bone/sharp.
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: non_bone
    patterns:
    - ^(?!.*(?i:(osteo|bone|sharp))).*$
  - label: bone_like
    patterns:
    - (?i)\b(osteo|bone|sharp)\b
- name: matrix
  description: Prefer 512 over 1024.
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: 512
    patterns:
    - (?i)\b512\b
  - label: 1024
    patterns:
    - (?i)\b1024\b
  - label: other
    patterns: []
- name: thickness
  description: Prefer moderate thickness for parenchymal HU.
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: 2.0
    patterns:
    - (?i)(?:^|_|\b)2[,_\.]0?(?:_|\b)
  - label: 3.0
    patterns:
    - (?i)(?:^|_|\b)3[,_\.]0?(?:_|\b)
  - label: 1.0
    patterns:
    - (?i)(?:^|_|\b)1[,_\.]0?(?:_|\b)
  - label: other
    patterns: []
- name: dose
  description: 20_ > 10_ > 5_.
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
- name: acquisition_size
  description: standard > thin > submillimetric.
  fields:
  - series_name
  - series_folder
  ordered_labels:
  - label: standard
    patterns:
    - (?i)\bstandard\b
  - label: thin
    patterns:
    - (?i)\bthin\b
  - label: submillimetric
    patterns:
    - (?i)\bsub[\s_\-]?milli\w*\b
    - (?i)\bsubmm\b
  - label: other
    patterns: []
policy_name: parenchymal
```

## Selection Logic

- Group rows by the configured exam field.
- Keep any monitoring rows unchanged when they match the configured monitoring patterns.
- Rank the remaining eligible vascular series lexicographically by the configured criteria order.
- Use RR% only as a late tie-breaker, with target ranges configured per phase.
- Break exact ties deterministically using acquisition time and series folder.

## Selection Results

- Exams processed: 6
- Groups processed: 6
- Selected parenchymal series: 0
- Monitoring rows kept: 0
- Exams without an eligible vascular series: 6

## Exams With No Eligible Parenchymal Series

- 10 alesha_williams (monitoring rows kept: 0)
- 11 alfredo_wood (monitoring rows kept: 0)
- 3 richard_hodges (monitoring rows kept: 0)
- 6 joseph_lee (monitoring rows kept: 0)
- 7 diane_ashley (monitoring rows kept: 0)
- 9 james_vargas (monitoring rows kept: 0)

## Per-Exam Selection

### Exam 10 - alesha_williams

No eligible series was identified.

### Exam 11 - alfredo_wood

No eligible series was identified.

### Exam 3 - richard_hodges

No eligible series was identified.

### Exam 6 - joseph_lee

No eligible series was identified.

### Exam 7 - diane_ashley

No eligible series was identified.

### Exam 9 - james_vargas

No eligible series was identified.

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

- Exams processed: 162
- Groups processed: 162
- Selected parenchymal series: 438
- Monitoring rows kept: 56
- Exams without an eligible vascular series: 31

## Exams With No Eligible Parenchymal Series

- 113 mary_robinson (monitoring rows kept: 0)
- 116 george_romero (monitoring rows kept: 0)
- 147 miguel_salas (monitoring rows kept: 0)
- 15 marcos_atkins (monitoring rows kept: 0)
- 162 tammy_moran (monitoring rows kept: 0)
- 172 donald_starks (monitoring rows kept: 0)
- 199 james_parker (monitoring rows kept: 0)
- 207 dwayne_martin (monitoring rows kept: 0)
- 223 ryan_smith (monitoring rows kept: 0)
- 224 roger_beverly (monitoring rows kept: 0)
- 24 frances_erlandson (monitoring rows kept: 0)
- 252 robert_ward (monitoring rows kept: 0)
- 253 teresa_rosenzweig (monitoring rows kept: 0)
- 289 mabel_martinez (monitoring rows kept: 0)
- 300 juanita_loveland (monitoring rows kept: 0)
- 372 eric_mills (monitoring rows kept: 0)
- 375 rachael_mullikin (monitoring rows kept: 0)
- 377 william_burden (monitoring rows kept: 0)
- 411 johnnie_kutscher (monitoring rows kept: 0)
- 413 margaret_cooper (monitoring rows kept: 0)
- 426 pearlie_simms (monitoring rows kept: 0)
- 429 robert_crook (monitoring rows kept: 0)
- 446 harriet_nick (monitoring rows kept: 0)
- 451 billy_estey (monitoring rows kept: 0)
- 457 richard_ayers (monitoring rows kept: 0)
- 467 marcella_lejeune (monitoring rows kept: 0)
- 468 shani_pless (monitoring rows kept: 0)
- 485 jennie_wilson (monitoring rows kept: 0)
- 495 yong_khoury (monitoring rows kept: 0)
- 62 raymond_smith (monitoring rows kept: 0)
- 79 carl_osburn (monitoring rows kept: 0)

## Per-Exam Selection

### Exam 1 - andre_clark

Selected series:
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (201_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]

Missing required phase buckets: pre_contrast, premonitoring, monitoring, arterial


### Exam 100 - lacy_kirk

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 103 - ryan_hanna

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 107 - jennifer_clouston

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 11 - doris_perez

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (601_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (701_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]

Missing required phase buckets: pre_contrast


### Exam 111 - salvador_doyle

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 113 - mary_robinson

No eligible series was identified.

### Exam 116 - george_romero

No eligible series was identified.

### Exam 117 - helen_gaskill

Selected series:
- Arteriosa  2.0  I30f  3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 12 - john_greenberg

Selected series:
- Arteriosa  2.0  I30f  3 (16_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (17_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 127 - vicky_sutton

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 13 - rachel_edwards

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (701_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (601_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Add Basale 2,00 Br40 Q3 Matrix 512 (401_add_basale_2_00_br40_q3_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (501_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (801_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]


### Exam 135 - dennis_king

Selected series:
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (3_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring, arterial


### Exam 137 - gloria_rea

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 138 - brendan_wallace

Selected series:
- Arteriosa 2,00 Br40 Q4 iMAR Matrix 512 (501_arteriosa_2_00_br40_q4_imar_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 3,00 Br40 Q4 iMAR Matrix 512 (201_basale_3_00_br40_q4_imar_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 iMAR Matrix 512 (601_venosa_2_00_br40_q4_imar_matrix_512) [phase=venous]


### Exam 139 - barbara_buckner

Selected series:
- Arteriosa  2.0  I30f  3 (19_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (4_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (20_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 140 - kerri_warren

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 147 - miguel_salas

No eligible series was identified.

### Exam 15 - marcos_atkins

No eligible series was identified.

### Exam 155 - erin_hopper

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 156 - gregory_love

Selected series:
- Arteriosa  2.0  I30f  3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 159 - linda_crawford

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 16 - dwayne_smith

Selected series:
- 701_add_arteriosa_2_00_br40_q3_matrix_512 (701_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- 601_monitoring_5_00_br36_matrix_512 (601_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- 401_add_basale_2_00_br40_q3_matrix_512 (401_add_basale_2_00_br40_q3_matrix_512) [phase=pre_contrast]
- 501_premonitoring_5_00_br36_matrix_512 (501_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- 801_toradd_venosa_2_00_br40_q3_matrix_512 (801_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]


### Exam 160 - irene_richey

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (501_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- 201_add_basale_2_00_br40_q3_matrix_512 (201_add_basale_2_00_br40_q3_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- BODY Venosa 2,00 Br36 Q3 cor Matrix 512 (601_body_venosa_2_00_br36_q3_cor_matrix_512) [phase=venous]


### Exam 162 - tammy_moran

No eligible series was identified.

### Exam 163 - cathryn_waters

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 168 - jerry_souphom

Selected series:
- Arteriosa  2.0  I30f  3 (16_arteriosa__2_0__i30f__3) [phase=arterial]
- 2_addome__2_0__i30f__3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (17_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 172 - donald_starks

No eligible series was identified.

### Exam 173 - carmen_skillings

Selected series:
- 19_arteriosa__2_0__i30f__3 (19_arteriosa__2_0__i30f__3) [phase=arterial]
- 2_addome__2_0__i30f__3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- 20_venosa__2_0__i30f__3 (20_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 180 - dolores_arellano

Selected series:
- 13_arteriosa__2_0__i30f__3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- 2_addome__2_0__i30f__3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- 14_venosa__2_0__i30f__3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 181 - celeste_fleeger

Selected series:
- 13_arteriosa__2_0__i30f__3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- 2_addome__2_0__i30f__3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- 14_venosa__2_0__i30f__3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 182 - rosalind_west

Selected series:
- 10_arteriosa__2_0__i30f__3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- 2_addome__2_0__i30f__3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- 11_venosa__2_0__i30f__3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 183 - george_smith

Selected series:
- 12_arteriosa__2_0__i30f__3 (12_arteriosa__2_0__i30f__3) [phase=arterial]
- 2_addome__2_0__i30f__3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- 13_venosa__2_0__i30f__3 (13_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 19 - jefferey_wise

Selected series:
- 9_arteriosa__2_0__i30f__3 (9_arteriosa__2_0__i30f__3) [phase=arterial]
- 2_addome__2_0__i30f__3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- 10_venosa__2_0__i30f__3 (10_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 197 - wilma_solis

Selected series:
- 9_arteriosa__2_0__i30f__3 (9_arteriosa__2_0__i30f__3) [phase=arterial]
- 2_addome__2_0__i30f__3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- 10_venosa__2_0__i30f__3 (10_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 199 - james_parker

No eligible series was identified.

### Exam 200 - leon_harkins

Selected series:
- Arteriosa  2.0  I30f  3 (15_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (16_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 201 - monica_spellman

Selected series:
- Arteriosa  2.0  I30f  3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 207 - dwayne_martin

No eligible series was identified.

### Exam 212 - jason_merritt

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 215 - patricia_bash

Selected series:
- Arteriosa  2.0  Br38  3 (11_arteriosa__2_0__br38__3) [phase=arterial]
- Addome  2.0  Br38  3 (2_addome__2_0__br38__3) [phase=pre_contrast]
- Venosa  2.0  Br38  3 (12_venosa__2_0__br38__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 219 - helen_johnson

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 220 - lee_giannakopoulo

Selected series:
- Arteriosa  2.0  I30f  3 (8_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (9_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 223 - ryan_smith

No eligible series was identified.

### Exam 224 - roger_beverly

No eligible series was identified.

### Exam 225 - lewis_merrill

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 228 - michael_smith

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (501_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Add Basale 2,00 Br40 Q3 Matrix 512 (201_add_basale_2_00_br40_q3_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (601_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]


### Exam 23 - john_crissman

Selected series:
- Arteriosa  2.0  I30f  3 (16_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (17_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 230 - brandi_penland

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (501_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Add Basale 2,00 Br40 Q3 Matrix 512 (201_add_basale_2_00_br40_q3_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (601_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]


### Exam 231 - kevin_armstrong

Selected series:
- Arteriosa  2.0  I30f  3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (4_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 239 - eugenia_cary

Selected series:
- Arteriosa  2.0  Br38  3 (17_arteriosa__2_0__br38__3) [phase=arterial]
- Addome  2.0  Br38  3 (4_addome__2_0__br38__3) [phase=pre_contrast]
- Venosa  2.0  Br38  3 (18_venosa__2_0__br38__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 24 - frances_erlandson

No eligible series was identified.

### Exam 240 - anita_brown

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 242 - ned_testa

Selected series:
- Arteriosa  2.0  I30f  3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 244 - miriam_dowden

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 245 - william_johnson

Selected series:
- Arteriosa  2.0  Br38  3 (14_arteriosa__2_0__br38__3) [phase=arterial]
- Addome  2.0  Br38  3 (2_addome__2_0__br38__3) [phase=pre_contrast]
- Venosa  2.0  Br38  3 (15_venosa__2_0__br38__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 246 - virginia_strange

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 252 - robert_ward

No eligible series was identified.

### Exam 253 - teresa_rosenzweig

No eligible series was identified.

### Exam 258 - joseph_troupe

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 284 - matthew_duncan

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 289 - mabel_martinez

No eligible series was identified.

### Exam 29 - earnest_prior

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (601_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (701_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]

Missing required phase buckets: pre_contrast


### Exam 294 - julian_thomas

Selected series:
- Arteriosa  2.0  I30f  3 (17_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (18_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 295 - sophie_spencer

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 299 - carroll_weise

Selected series:
- Arteriosa  2.0  I30f  3 (8_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (9_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 300 - juanita_loveland

No eligible series was identified.

### Exam 304 - etta_williams

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 308 - bradley_escalante

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 31 - kathleen_black

Selected series:
- Arteriosa  2.0  I30f  3 (15_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (16_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 310 - leona_page

Selected series:
- ARTERIOSA  2.0  Br38  3 (11_arteriosa__2_0__br38__3) [phase=arterial]
- Addome  2.0  Br38  3 (2_addome__2_0__br38__3) [phase=pre_contrast]
- VENOSA   2.0  Br38  3 (12_venosa___2_0__br38__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 315 - elizabeth_sanders

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Monitoring  10.0  B30s (4_monitoring__10_0__b30s) [phase=monitoring]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- PreMonitoring  10.0  B30s (3_premonitoring__10_0__b30s) [phase=premonitoring]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]


### Exam 320 - lauren_perry

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 323 - faye_guerra

Selected series:
- Arteriosa  2.0  I30f  3 (12_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (13_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 329 - oscar_beierle

Selected series:
- Arteriosa  2.0  I30f  3 (9_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (10_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 33 - gregory_fain

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 331 - robert_bostwick

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 335 - clayton_halpern

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 338 - amelia_williams

Selected series:
- Arteriosa  2.0  I30f  3 (5_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (6_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 34 - susan_collazo

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (501_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Add Basale 2,00 Br40 Q3 Matrix 512 (201_add_basale_2_00_br40_q3_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (601_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]


### Exam 340 - christopher_lampert

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 344 - lesley_wake

Selected series:
- Arteriosa  2.0  I30f  3 (9_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (10_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 347 - walter_garner

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 353 - sally_jackson

Selected series:
- Arteriosa  2.0  I30f  3 (9_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (10_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 356 - jared_hardt

Selected series:
- Arteriosa  2.0  Br38  3 (9_arteriosa__2_0__br38__3) [phase=arterial]
- Addome  2.0  Br38  3 (2_addome__2_0__br38__3) [phase=pre_contrast]
- Venosa  2.0  Br38  3 (10_venosa__2_0__br38__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 364 - tonya_childs

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 365 - lisa_isenberg

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (701_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (601_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Add Basale 2,00 Br40 Q3 Matrix 512 (401_add_basale_2_00_br40_q3_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (501_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (801_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]


### Exam 369 - hattie_robinson

Selected series:
- Arteriosa  2.0  I30f  3 (18_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (4_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (19_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 371 - scott_logan

Selected series:
- Arteriosa  2.0  I30f  3 (7_arteriosa__2_0__i30f__3) [phase=arterial]
- Venosa  2.0  I30f  3 (8_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: pre_contrast, premonitoring, monitoring


### Exam 372 - eric_mills

No eligible series was identified.

### Exam 374 - sandra_briseno

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (601_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (301_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (701_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 375 - rachael_mullikin

No eligible series was identified.

### Exam 377 - william_burden

No eligible series was identified.

### Exam 38 - mark_adams

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 380 - ronald_schull

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 381 - tom_george

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 382 - ethel_swearinger

Selected series:
- Arteriosa  2.0  I30f  3 (8_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (9_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 384 - esther_sullivan

Selected series:
- Arteriosa  2.0  I30f  3 (14_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (15_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 389 - felix_evans

Selected series:
- Arteriosa  2.0  I30f  3 (12_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (13_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 39 - deborah_benford

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 393 - edward_harris

Selected series:
- Arteriosa  1.5  I30f  4 (15_arteriosa__1_5__i30f__4) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]

Missing required phase buckets: premonitoring, monitoring, venous


### Exam 395 - lonnie_wolf

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 398 - frieda_olander

Selected series:
- Arteriosa  2.0  I30f  3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 402 - kenneth_jones

Selected series:
- Arteriosa  0.6  B30f (11_arteriosa__0_6__b30f) [phase=arterial]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: pre_contrast, premonitoring, monitoring


### Exam 407 - margaret_wallace

Selected series:
- Arteriosa  2.0  I30f  3 (7_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (8_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 410 - elizabeth_nichols

Selected series:
- Arteriosa  2.0  I30f  3 (18_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (19_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 411 - johnnie_kutscher

No eligible series was identified.

### Exam 413 - margaret_cooper

No eligible series was identified.

### Exam 421 - thomas_king

Selected series:
- Arteriosa  2.0  I30f  3 (18_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (19_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 426 - pearlie_simms

No eligible series was identified.

### Exam 429 - robert_crook

No eligible series was identified.

### Exam 433 - eddie_williams

Selected series:
- Arteriosa  2.0  I30f  3 (9_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (10_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 434 - tiffany_shin

Selected series:
- Arteriosa  2.0  Br38  3 (17_arteriosa__2_0__br38__3) [phase=arterial]
- Addome  2.0  Br38  3 (2_addome__2_0__br38__3) [phase=pre_contrast]
- Venosa  2.0  Br38  3 (18_venosa__2_0__br38__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 439 - marquis_aliberti

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 441 - david_mayer

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 445 - helen_snodgrass

Selected series:
- Arteriosa  2.0  I30f  3 (12_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (13_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 446 - harriet_nick

No eligible series was identified.

### Exam 451 - billy_estey

No eligible series was identified.

### Exam 452 - casey_venson

Selected series:
- Arteriosa  2.0  I30f  3 (19_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (4_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (20_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 453 - john_bodak

Selected series:
- Arteriosa 2,00 Br40 Q4 Matrix 512 (501_arteriosa_2_00_br40_q4_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512) [phase=venous]


### Exam 454 - alice_harris

Selected series:
- Arteriosa  2.0  I30f  3 (12_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (13_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 455 - beverly_reiland

Selected series:
- Arteriosa  2.0  I30f  3 (7_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (8_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 456 - michael_bailey

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 457 - richard_ayers

No eligible series was identified.

### Exam 458 - janet_branstetter

Selected series:
- Arteriosa  2.0  I30f  3 (6_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (7_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 460 - andrea_clark

Selected series:
- TorAdd Venosa 2,00 Qr40 Q3 Matrix 512 SPP_ME70 (401_toradd_venosa_2_00_qr40_q3_matrix_512_spp_me70) [phase=venous]

Missing required phase buckets: pre_contrast, premonitoring, monitoring, arterial


### Exam 461 - earl_delancey

Selected series:
- Arteriosa  2.0  I30f  3 (14_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (15_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 464 - karin_bryon

Selected series:
- Arteriosa  2.0  I30f  3 (21_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (4_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (22_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 467 - marcella_lejeune

No eligible series was identified.

### Exam 468 - shani_pless

No eligible series was identified.

### Exam 469 - robert_ouellette

Selected series:
- Arteriosa  2.0  I30f  3 (12_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (13_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 470 - jack_rust

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 472 - norman_fizer

Selected series:
- Arteriosa  2.0  Br38  3 (23_arteriosa__2_0__br38__3) [phase=arterial]
- Addome  2.0  Br38  3 (4_addome__2_0__br38__3) [phase=pre_contrast]
- Venosa  2.0  Br36  3 (24_venosa__2_0__br36__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 473 - wanda_beckett

Selected series:
- Arteriosa  2.0  I30f  3 (14_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (15_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 474 - mike_adams

Selected series:
- Arteriosa  2.0  I30f  3 (15_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (16_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 480 - mark_stratton

Selected series:
- Arteriosa  2.0  I30f  3 (9_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (10_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 481 - mercedes_osborne

Selected series:
- Arteriosa  2.0  I30f  3 (12_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (13_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 482 - roberta_silvera

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 485 - jennie_wilson

No eligible series was identified.

### Exam 49 - martin_maclean

Selected series:
- Arteriosa  2.0  I30f  3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 495 - yong_khoury

No eligible series was identified.

### Exam 496 - lawrence_washam

Selected series:
- Arteriosa  2.0  Br38  3 (10_arteriosa__2_0__br38__3) [phase=arterial]
- Addome  2.0  Br38  3 (2_addome__2_0__br38__3) [phase=pre_contrast]
- Venosa  2.0  Br38  3 (11_venosa__2_0__br38__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 497 - sterling_rodriguez

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 51 - michael_abela

Selected series:
- Arteriosa  2.0  I30f  3 (7_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (8_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 55 - hiram_wanzer

Selected series:
- Arteriosa  2.0  I30f  3 (14_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (15_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 56 - kareem_boyd

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (12_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 58 - erin_vanetten

Selected series:
- Arteriosa  2.0  I30f  3 (8_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (9_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 59 - janice_goss

Selected series:
- Arteriosa  2.0  I30f  3 (17_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (18_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 6 - margaret_jones

Selected series:
- Arteriosa  2.0  I30f  3 (12_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (13_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 60 - james_wolchesky

Selected series:
- Arteriosa  2.0  I30f  3 (18_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (5_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (19_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 61 - fred_kuykendall

Selected series:
- Add Arteriosa 2,00 Br40 Q3 Matrix 512 (601_add_arteriosa_2_00_br40_q3_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- TorAdd Venosa 2,00 Br40 Q3 Matrix 512 (701_toradd_venosa_2_00_br40_q3_matrix_512) [phase=venous]

Missing required phase buckets: pre_contrast


### Exam 62 - raymond_smith

No eligible series was identified.

### Exam 64 - sharon_mineo

Selected series:
- Arteriosa  2.0  I30f  3 (10_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (11_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 68 - geraldine_chan

Selected series:
- Arteriosa  2.0  I30f  3 (9_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (10_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 69 - richard_harris

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 73 - stephen_gross

Selected series:
- Arteriosa  2.0  I30f  3 (14_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (15_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 79 - carl_osburn

No eligible series was identified.

### Exam 81 - whitney_messenger

Selected series:
- Arteriosa  2.0  I30f  3 (7_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (8_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 83 - bernice_roberts

Selected series:
- Arteriosa 2,00 Br40 Q4 ax Matrix 512 (501_arteriosa_2_00_br40_q4_ax_matrix_512) [phase=arterial]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Basale 2,00 Br40 Q4 Matrix 512 (201_basale_2_00_br40_q4_matrix_512) [phase=pre_contrast]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]
- Venosa 2,00 Br40 Q4 ax Matrix 512 (601_venosa_2_00_br40_q4_ax_matrix_512) [phase=venous]


### Exam 87 - raymond_anderson

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 90 - richard_walls

Selected series:
- Arteriosa  2.0  I30f  3 (13_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (14_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring


### Exam 94 - misty_price

Selected series:
- Arteriosa  2.0  I30f  3 (8_arteriosa__2_0__i30f__3) [phase=arterial]
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3) [phase=pre_contrast]
- Venosa  2.0  I30f  3 (9_venosa__2_0__i30f__3) [phase=venous]

Missing required phase buckets: premonitoring, monitoring

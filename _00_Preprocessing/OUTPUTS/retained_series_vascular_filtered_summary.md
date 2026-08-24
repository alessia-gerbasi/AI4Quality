# Vascular Series Selection Summary

## Configurable Rules

```yaml
group_field: ct_id
keep_monitoring: true
candidate_status: accepted
exclude_monitoring: false
keep_additional_distinct_names: false
select_one_best_remaining: true
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
policy_name: vascular
```

## Selection Logic

- Group rows by the configured exam field.
- Keep any monitoring rows unchanged when they match the configured monitoring patterns.
- Rank the remaining eligible vascular series lexicographically by the configured criteria order.
- Use RR% only as a late tie-breaker, with target ranges configured per phase.
- Break exact ties deterministically using acquisition time and series folder.

## Selection Results

- Exams processed: 212
- Groups processed: 212
- Selected vascular series: 133
- Monitoring rows kept: 43
- Exams without an eligible vascular series: 131

## Exams With No Eligible Vascular Series

- 1 andre_clark (monitoring rows kept: 0)
- 100 lacy_kirk (monitoring rows kept: 0)
- 103 ryan_hanna (monitoring rows kept: 0)
- 107 jennifer_clouston (monitoring rows kept: 0)
- 11 doris_perez (monitoring rows kept: 0)
- 111 salvador_doyle (monitoring rows kept: 0)
- 117 helen_gaskill (monitoring rows kept: 0)
- 12 john_greenberg (monitoring rows kept: 0)
- 127 vicky_sutton (monitoring rows kept: 0)
- 13 rachel_edwards (monitoring rows kept: 0)
- 135 dennis_king (monitoring rows kept: 0)
- 137 gloria_rea (monitoring rows kept: 0)
- 138 brendan_wallace (monitoring rows kept: 0)
- 139 barbara_buckner (monitoring rows kept: 0)
- 140 kerri_warren (monitoring rows kept: 0)
- 155 erin_hopper (monitoring rows kept: 0)
- 156 gregory_love (monitoring rows kept: 0)
- 159 linda_crawford (monitoring rows kept: 0)
- 16 dwayne_smith (monitoring rows kept: 0)
- 160 irene_richey (monitoring rows kept: 0)
- 163 cathryn_waters (monitoring rows kept: 0)
- 168 jerry_souphom (monitoring rows kept: 0)
- 173 carmen_skillings (monitoring rows kept: 0)
- 180 dolores_arellano (monitoring rows kept: 0)
- 181 celeste_fleeger (monitoring rows kept: 0)
- 182 rosalind_west (monitoring rows kept: 0)
- 183 george_smith (monitoring rows kept: 0)
- 19 jefferey_wise (monitoring rows kept: 0)
- 197 wilma_solis (monitoring rows kept: 0)
- 200 leon_harkins (monitoring rows kept: 0)
- 201 monica_spellman (monitoring rows kept: 0)
- 212 jason_merritt (monitoring rows kept: 0)
- 215 patricia_bash (monitoring rows kept: 0)
- 219 helen_johnson (monitoring rows kept: 0)
- 220 lee_giannakopoulo (monitoring rows kept: 0)
- 225 lewis_merrill (monitoring rows kept: 0)
- 228 michael_smith (monitoring rows kept: 0)
- 23 john_crissman (monitoring rows kept: 0)
- 230 brandi_penland (monitoring rows kept: 0)
- 231 kevin_armstrong (monitoring rows kept: 0)
- 239 eugenia_cary (monitoring rows kept: 0)
- 240 anita_brown (monitoring rows kept: 0)
- 242 ned_testa (monitoring rows kept: 0)
- 244 miriam_dowden (monitoring rows kept: 0)
- 245 william_johnson (monitoring rows kept: 0)
- 246 virginia_strange (monitoring rows kept: 0)
- 258 joseph_troupe (monitoring rows kept: 0)
- 284 matthew_duncan (monitoring rows kept: 0)
- 29 earnest_prior (monitoring rows kept: 0)
- 294 julian_thomas (monitoring rows kept: 0)
- 295 sophie_spencer (monitoring rows kept: 0)
- 299 carroll_weise (monitoring rows kept: 0)
- 304 etta_williams (monitoring rows kept: 0)
- 308 bradley_escalante (monitoring rows kept: 0)
- 31 kathleen_black (monitoring rows kept: 0)
- 310 leona_page (monitoring rows kept: 0)
- 315 elizabeth_sanders (monitoring rows kept: 0)
- 320 lauren_perry (monitoring rows kept: 0)
- 323 faye_guerra (monitoring rows kept: 0)
- 329 oscar_beierle (monitoring rows kept: 0)
- 33 gregory_fain (monitoring rows kept: 0)
- 331 robert_bostwick (monitoring rows kept: 0)
- 335 clayton_halpern (monitoring rows kept: 0)
- 338 amelia_williams (monitoring rows kept: 0)
- 34 susan_collazo (monitoring rows kept: 0)
- 340 christopher_lampert (monitoring rows kept: 0)
- 344 lesley_wake (monitoring rows kept: 0)
- 347 walter_garner (monitoring rows kept: 0)
- 353 sally_jackson (monitoring rows kept: 0)
- 356 jared_hardt (monitoring rows kept: 0)
- 364 tonya_childs (monitoring rows kept: 0)
- 365 lisa_isenberg (monitoring rows kept: 0)
- 369 hattie_robinson (monitoring rows kept: 0)
- 371 scott_logan (monitoring rows kept: 0)
- 374 sandra_briseno (monitoring rows kept: 0)
- 38 mark_adams (monitoring rows kept: 0)
- 380 ronald_schull (monitoring rows kept: 0)
- 381 tom_george (monitoring rows kept: 0)
- 382 ethel_swearinger (monitoring rows kept: 0)
- 384 esther_sullivan (monitoring rows kept: 0)
- 389 felix_evans (monitoring rows kept: 0)
- 39 deborah_benford (monitoring rows kept: 0)
- 393 edward_harris (monitoring rows kept: 0)
- 395 lonnie_wolf (monitoring rows kept: 0)
- 398 frieda_olander (monitoring rows kept: 0)
- 402 kenneth_jones (monitoring rows kept: 0)
- 407 margaret_wallace (monitoring rows kept: 0)
- 410 elizabeth_nichols (monitoring rows kept: 0)
- 421 thomas_king (monitoring rows kept: 0)
- 433 eddie_williams (monitoring rows kept: 0)
- 434 tiffany_shin (monitoring rows kept: 0)
- 439 marquis_aliberti (monitoring rows kept: 0)
- 441 david_mayer (monitoring rows kept: 0)
- 445 helen_snodgrass (monitoring rows kept: 0)
- 452 casey_venson (monitoring rows kept: 0)
- 453 john_bodak (monitoring rows kept: 0)
- 454 alice_harris (monitoring rows kept: 0)
- 455 beverly_reiland (monitoring rows kept: 0)
- 456 michael_bailey (monitoring rows kept: 0)
- 458 janet_branstetter (monitoring rows kept: 0)
- 460 andrea_clark (monitoring rows kept: 0)
- 461 earl_delancey (monitoring rows kept: 0)
- 464 karin_bryon (monitoring rows kept: 0)
- 469 robert_ouellette (monitoring rows kept: 0)
- 470 jack_rust (monitoring rows kept: 0)
- 472 norman_fizer (monitoring rows kept: 0)
- 473 wanda_beckett (monitoring rows kept: 0)
- 474 mike_adams (monitoring rows kept: 0)
- 480 mark_stratton (monitoring rows kept: 0)
- 481 mercedes_osborne (monitoring rows kept: 0)
- 482 roberta_silvera (monitoring rows kept: 0)
- 49 martin_maclean (monitoring rows kept: 0)
- 496 lawrence_washam (monitoring rows kept: 0)
- 497 sterling_rodriguez (monitoring rows kept: 0)
- 51 michael_abela (monitoring rows kept: 0)
- 55 hiram_wanzer (monitoring rows kept: 0)
- 56 kareem_boyd (monitoring rows kept: 0)
- 58 erin_vanetten (monitoring rows kept: 0)
- 59 janice_goss (monitoring rows kept: 0)
- 6 margaret_jones (monitoring rows kept: 0)
- 60 james_wolchesky (monitoring rows kept: 0)
- 61 fred_kuykendall (monitoring rows kept: 0)
- 64 sharon_mineo (monitoring rows kept: 0)
- 68 geraldine_chan (monitoring rows kept: 0)
- 69 richard_harris (monitoring rows kept: 0)
- 73 stephen_gross (monitoring rows kept: 0)
- 81 whitney_messenger (monitoring rows kept: 0)
- 83 bernice_roberts (monitoring rows kept: 0)
- 87 raymond_anderson (monitoring rows kept: 0)
- 90 richard_walls (monitoring rows kept: 0)
- 94 misty_price (monitoring rows kept: 0)

## Per-Exam Selection

### Exam 1 - andre_clark

No eligible series was identified.

### Exam 100 - lacy_kirk

No eligible series was identified.

### Exam 101 - brenda_gober

Selected series:
- CCT HR Heart  0,20 Bv72 Q4 -160ms Matrix 1024 (601_cct_hr_heart__0_20_bv72_q4_-160ms_matrix_1024)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 103 - ryan_hanna

No eligible series was identified.

### Exam 104 - olive_adams

Selected series:
- 20_ds_coradseq__0_6__i26f__2__bestdiast_83_% (20_ds_coradseq__0_6__i26f__2__bestdiast_83_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 107 - jennifer_clouston

No eligible series was identified.

### Exam 109 - james_lanning

Selected series:
- Torace  2.0  I30f  3 (2_torace__2_0__i30f__3)
- Angio Aorta  0.75  I26f  3 (10_angio_aorta__0_75__i26f__3) [phase=aorta]

Missing required phase buckets: premonitoring, monitoring


### Exam 11 - doris_perez

No eligible series was identified.

### Exam 110 - lavelle_fullilove

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 72 % (9_ds_coradseq__0_6__i26f__2__bestdiast_72_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 111 - salvador_doyle

No eligible series was identified.

### Exam 113 - mary_robinson

Selected series:
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3)
- Angio Aorta  1.0  I26f  3 (13_angio_aorta__1_0__i26f__3) [phase=aorta]

Missing required phase buckets: premonitoring, monitoring


### Exam 116 - george_romero

Selected series:
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 117 - helen_gaskill

No eligible series was identified.

### Exam 12 - john_greenberg

No eligible series was identified.

### Exam 122 - jerry_chambers

Selected series:
- Angio Arti Inf  1.5  I31f  4 (11_angio_arti_inf__1_5__i31f__4)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 127 - vicky_sutton

No eligible series was identified.

### Exam 128 - carl_blanks

Selected series:
- Angio TSA  0.75  I26f  4 (20_angio_tsa__0_75__i26f__4)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 13 - rachel_edwards

No eligible series was identified.

### Exam 135 - dennis_king

No eligible series was identified.

### Exam 137 - gloria_rea

No eligible series was identified.

### Exam 138 - brendan_wallace

No eligible series was identified.

### Exam 139 - barbara_buckner

No eligible series was identified.

### Exam 140 - kerri_warren

No eligible series was identified.

### Exam 147 - miguel_salas

Selected series:
- Arteriosa  2.0  I30f  3 (11_arteriosa__2_0__i30f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 15 - marcos_atkins

Selected series:
- 12_arteriosa__2_0__i30f__3 (12_arteriosa__2_0__i30f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 154 - william_smith

Selected series:
- 17_ds_coradseq__0_6__i26f__2__bestdiast_72_% (17_ds_coradseq__0_6__i26f__2__bestdiast_72_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 155 - erin_hopper

No eligible series was identified.

### Exam 156 - gregory_love

No eligible series was identified.

### Exam 159 - linda_crawford

No eligible series was identified.

### Exam 16 - dwayne_smith

No eligible series was identified.

### Exam 160 - irene_richey

No eligible series was identified.

### Exam 162 - tammy_moran

Selected series:
- 701_add_arteriosa_2_00_br40_q3_matrix_512 (701_add_arteriosa_2_00_br40_q3_matrix_512)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 163 - cathryn_waters

No eligible series was identified.

### Exam 168 - jerry_souphom

No eligible series was identified.

### Exam 17 - robert_wang

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 70 % (8_ds_coradseq__0_6__i26f__2__bestdiast_70_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 171 - frank_reynolds

Selected series:
- 15_ds_coradseq__0_6__i26f__2__bestdiast_76_% (15_ds_coradseq__0_6__i26f__2__bestdiast_76_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 172 - donald_starks

Selected series:
- 601_corcta_uhr_spect_spi_0_20_bv48_q4_bestdiast_86%_matrix_512 (601_corcta_uhr_spect_spi_0_20_bv48_q4_bestdiast_86%_matrix_512)
- 501_monitoring_5_00_br36_matrix_512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- 401_premonitoring_5_00_br36_matrix_512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 173 - carmen_skillings

No eligible series was identified.

### Exam 180 - dolores_arellano

No eligible series was identified.

### Exam 181 - celeste_fleeger

No eligible series was identified.

### Exam 182 - rosalind_west

No eligible series was identified.

### Exam 183 - george_smith

No eligible series was identified.

### Exam 187 - alice_tharrington

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 75 % (9_ds_coradseq__0_6__i26f__2__bestdiast_75_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 19 - jefferey_wise

No eligible series was identified.

### Exam 195 - johnny_mckie

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 75 % (13_ds_coradseq__0_6__i26f__2__bestdiast_75_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 197 - wilma_solis

No eligible series was identified.

### Exam 199 - james_parker

Selected series:
- CorCTA UHR Spect Seq 0,20 Bv48 Q4 BestDiast 74% Matrix 512 (601_corcta_uhr_spect_seq_0_20_bv48_q4_bestdiast_74%_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 200 - leon_harkins

No eligible series was identified.

### Exam 201 - monica_spellman

No eligible series was identified.

### Exam 202 - marcus_hassell

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 73 % (15_ds_coradseq__0_6__i26f__2__bestdiast_73_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 203 - valentin_graham

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 74 % (27_ds_coradseq__0_6__i26f__2__bestdiast_74_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 207 - dwayne_martin

Selected series:
- Arti Inf 2,00 Qr40 Q4 Matrix 512 (401_arti_inf_2_00_qr40_q4_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (301_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (201_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 209 - jo_clark

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 71 % (9_ds_coradseq__0_6__i26f__2__bestdiast_71_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 212 - jason_merritt

No eligible series was identified.

### Exam 215 - patricia_bash

No eligible series was identified.

### Exam 219 - helen_johnson

No eligible series was identified.

### Exam 220 - lee_giannakopoulo

No eligible series was identified.

### Exam 223 - ryan_smith

Selected series:
- CCT HR Function 1,50 Bv48 Q4 0% - 90% Matrix 256 (601_cct_hr_function_1_50_bv48_q4_0%_-_90%_matrix_256)
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 224 - roger_beverly

Selected series:
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 225 - lewis_merrill

No eligible series was identified.

### Exam 226 - gloria_lowery

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 72 % (9_ds_coradseq__0_6__i26f__2__bestdiast_72_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 228 - michael_smith

No eligible series was identified.

### Exam 23 - john_crissman

No eligible series was identified.

### Exam 230 - brandi_penland

No eligible series was identified.

### Exam 231 - kevin_armstrong

No eligible series was identified.

### Exam 239 - eugenia_cary

No eligible series was identified.

### Exam 24 - frances_erlandson

Selected series:
- CorCTA SEQ Diast 0,40 Bv48 Q4 BestDiast 76% Matrix 512 (601_corcta_seq_diast_0_40_bv48_q4_bestdiast_76%_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 240 - anita_brown

No eligible series was identified.

### Exam 242 - ned_testa

No eligible series was identified.

### Exam 243 - randall_williams

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 69 % (8_ds_coradseq__0_6__i26f__2__bestdiast_69_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 244 - miriam_dowden

No eligible series was identified.

### Exam 245 - william_johnson

No eligible series was identified.

### Exam 246 - virginia_strange

No eligible series was identified.

### Exam 250 - sara_shuford

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 70 % (19_ds_coradseq__0_6__i26f__2__bestdiast_70_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 252 - robert_ward

Selected series:
- venosa 2,00 Br40 Q4 Matrix 512 (601_venosa_2_00_br40_q4_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 253 - teresa_rosenzweig

Selected series:
- venosa 1,00 Br40 Q4 Matrix 512 (601_venosa_1_00_br40_q4_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 254 - christopher_roman

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 77 % (12_ds_coradseq__0_6__i26f__2__bestdiast_77_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 258 - joseph_troupe

No eligible series was identified.

### Exam 26 - joyce_surratt

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 68 % (13_ds_coradseq__0_6__i26f__2__bestdiast_68_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 260 - michael_small

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 74 % (17_ds_coradseq__0_6__i26f__2__bestdiast_74_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 263 - john_balling

Selected series:
- DS_CorCTA  0.6  I26f  3  BestDiast 70 % (11_ds_corcta__0_6__i26f__3__bestdiast_70_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 267 - agustin_lee

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 69 % (10_ds_coradseq__0_6__i26f__2__bestdiast_69_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 269 - deborah_scott

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 76 % (11_ds_coradseq__0_6__i26f__2__bestdiast_76_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 284 - matthew_duncan

No eligible series was identified.

### Exam 287 - kaitlyn_terry

Selected series:
- DS_CorCTA  0.6  I26f  3  BestDiast 71 % (16_ds_corcta__0_6__i26f__3__bestdiast_71_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 289 - mabel_martinez

Selected series:
- Basale 1,00 Br40 Q4 Matrix 512 (301_basale_1_00_br40_q4_matrix_512)
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta, monitoring


### Exam 29 - earnest_prior

No eligible series was identified.

### Exam 294 - julian_thomas

No eligible series was identified.

### Exam 295 - sophie_spencer

No eligible series was identified.

### Exam 298 - rosa_pablo

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 72 % (9_ds_coradseq__0_6__i26f__2__bestdiast_72_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 299 - carroll_weise

No eligible series was identified.

### Exam 300 - juanita_loveland

Selected series:
- Aorta 0,80 Bv44 Q4 Matrix 768 (501_aorta_0_80_bv44_q4_matrix_768) [phase=aorta]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (201_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]


### Exam 304 - etta_williams

No eligible series was identified.

### Exam 308 - bradley_escalante

No eligible series was identified.

### Exam 31 - kathleen_black

No eligible series was identified.

### Exam 310 - leona_page

No eligible series was identified.

### Exam 315 - elizabeth_sanders

No eligible series was identified.

### Exam 318 - jennifer_lee

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 73 % (10_ds_coradseq__0_6__i26f__2__bestdiast_73_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 320 - lauren_perry

No eligible series was identified.

### Exam 323 - faye_guerra

No eligible series was identified.

### Exam 328 - gus_roberts

Selected series:
- Angio Arti Inf  1.5  I31f  4 (14_angio_arti_inf__1_5__i31f__4)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 329 - oscar_beierle

No eligible series was identified.

### Exam 33 - gregory_fain

No eligible series was identified.

### Exam 330 - stephanie_butcher

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 77 % (16_ds_coradseq__0_6__i26f__2__bestdiast_77_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 331 - robert_bostwick

No eligible series was identified.

### Exam 335 - clayton_halpern

No eligible series was identified.

### Exam 338 - amelia_williams

No eligible series was identified.

### Exam 34 - susan_collazo

No eligible series was identified.

### Exam 340 - christopher_lampert

No eligible series was identified.

### Exam 344 - lesley_wake

No eligible series was identified.

### Exam 347 - walter_garner

No eligible series was identified.

### Exam 353 - sally_jackson

No eligible series was identified.

### Exam 356 - jared_hardt

No eligible series was identified.

### Exam 364 - tonya_childs

No eligible series was identified.

### Exam 365 - lisa_isenberg

No eligible series was identified.

### Exam 369 - hattie_robinson

No eligible series was identified.

### Exam 371 - scott_logan

No eligible series was identified.

### Exam 372 - eric_mills

Selected series:
- Basale 1,00 Br40 Q4 Matrix 512 (201_basale_1_00_br40_q4_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 373 - holly_wright

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 73 % (14_ds_coradseq__0_6__i26f__2__bestdiast_73_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 374 - sandra_briseno

No eligible series was identified.

### Exam 375 - rachael_mullikin

Selected series:
- Basale 1,50 Br40 Q3 Matrix 512 (201_basale_1_50_br40_q3_matrix_512)
- Aorta UHR 0,20 Bv60 Q4 Matrix 1024 (501_aorta_uhr_0_20_bv60_q4_matrix_1024) [phase=aorta]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]


### Exam 377 - william_burden

Selected series:
- Aorta ECG Heart 1,00 Qr40 Q4 BestDiast 75% Matrix 512 SPP_ME70 (401_aorta_ecg_heart_1_00_qr40_q4_bestdiast_75%_matrix_512_spp_me70) [phase=aorta]
- Monitoring 5,00 Br36 Matrix 512 (301_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (201_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]


### Exam 379 - richard_bolden

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 69 % (17_ds_coradseq__0_6__i26f__2__bestdiast_69_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 38 - mark_adams

No eligible series was identified.

### Exam 380 - ronald_schull

No eligible series was identified.

### Exam 381 - tom_george

No eligible series was identified.

### Exam 382 - ethel_swearinger

No eligible series was identified.

### Exam 384 - esther_sullivan

No eligible series was identified.

### Exam 387 - jacqueline_west

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 70 % (11_ds_coradseq__0_6__i26f__2__bestdiast_70_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 389 - felix_evans

No eligible series was identified.

### Exam 39 - deborah_benford

No eligible series was identified.

### Exam 393 - edward_harris

No eligible series was identified.

### Exam 395 - lonnie_wolf

No eligible series was identified.

### Exam 398 - frieda_olander

No eligible series was identified.

### Exam 4 - emma_kimmerle

Selected series:
- Angio Embolia  1.0  I26f  3 (8_angio_embolia__1_0__i26f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 400 - juanita_gavin

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 67 % (9_ds_coradseq__0_6__i26f__2__bestdiast_67_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 402 - kenneth_jones

No eligible series was identified.

### Exam 407 - margaret_wallace

No eligible series was identified.

### Exam 409 - maurice_thompson

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 73 % (9_ds_coradseq__0_6__i26f__2__bestdiast_73_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 410 - elizabeth_nichols

No eligible series was identified.

### Exam 411 - johnnie_kutscher

Selected series:
- CorCTA UHR Spect Spi 1,00 Bl60 Q4 BestDiast 78% Matrix 768 (701_corcta_uhr_spect_spi_1_00_bl60_q4_bestdiast_78%_matrix_768)
- Monitoring 5,00 Br36 Matrix 512 (601_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 413 - margaret_cooper

Selected series:
- Venosa 2,00 Br40 Q4 iMAR Matrix 512 (601_venosa_2_00_br40_q4_imar_matrix_512)
- Aorta ECG Heart 1,50 Bv36 Q4 BestDiast 68% Matrix 512 (501_aorta_ecg_heart_1_50_bv36_q4_bestdiast_68%_matrix_512) [phase=aorta]

Missing required phase buckets: premonitoring, monitoring


### Exam 415 - bryan_sutch

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 67 % (18_ds_coradseq__0_6__i26f__2__bestdiast_67_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 42 - robert_smith

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 73 % (10_ds_coradseq__0_6__i26f__2__bestdiast_73_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 421 - thomas_king

No eligible series was identified.

### Exam 426 - pearlie_simms

Selected series:
- Addome  2.0  I30f  3 (2_addome__2_0__i30f__3)
- Angio Aorta  1.0  I26f  3 (21_angio_aorta__1_0__i26f__3) [phase=aorta]

Missing required phase buckets: premonitoring, monitoring


### Exam 429 - robert_crook

Selected series:
- CorCTA UHR Spect Seq 0,20 Bv48 Q4 BestDiast 75% Matrix 512 (601_corcta_uhr_spect_seq_0_20_bv48_q4_bestdiast_75%_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 433 - eddie_williams

No eligible series was identified.

### Exam 434 - tiffany_shin

No eligible series was identified.

### Exam 435 - william_garces

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 72 % (13_ds_coradseq__0_6__i26f__2__bestdiast_72_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 437 - crystal_perez

Selected series:
- Angio TSA  0.75  I26f  4 (18_angio_tsa__0_75__i26f__4)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 439 - marquis_aliberti

No eligible series was identified.

### Exam 440 - jerry_brown

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 73 % (11_ds_coradseq__0_6__i26f__2__bestdiast_73_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 441 - david_mayer

No eligible series was identified.

### Exam 445 - helen_snodgrass

No eligible series was identified.

### Exam 446 - harriet_nick

Selected series:
- CorCTA UHR Spect Seq 0,20 Bv48 Q4 BestDiast 74% Matrix 512 (601_corcta_uhr_spect_seq_0_20_bv48_q4_bestdiast_74%_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 451 - billy_estey

Selected series:
- Basale 1,00 Br40 Q3 Matrix 512 (201_basale_1_00_br40_q3_matrix_512)
- Aorta 1,00 Bv44 Q4 Matrix 768 (501_aorta_1_00_bv44_q4_matrix_768) [phase=aorta]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]


### Exam 452 - casey_venson

No eligible series was identified.

### Exam 453 - john_bodak

No eligible series was identified.

### Exam 454 - alice_harris

No eligible series was identified.

### Exam 455 - beverly_reiland

No eligible series was identified.

### Exam 456 - michael_bailey

No eligible series was identified.

### Exam 457 - richard_ayers

Selected series:
- CaSc Seq  3,00 Qr36 Q2 BestDiast 75% Matrix 512 (301_casc_seq__3_00_qr36_q2_bestdiast_75%_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (401_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 458 - janet_branstetter

No eligible series was identified.

### Exam 460 - andrea_clark

No eligible series was identified.

### Exam 461 - earl_delancey

No eligible series was identified.

### Exam 464 - karin_bryon

No eligible series was identified.

### Exam 467 - marcella_lejeune

Selected series:
- Basale 1,00 Br40 Q4 Matrix 512 (201_basale_1_00_br40_q4_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 468 - shani_pless

Selected series:
- Angio Embolia 0,80 Bv44 Q4 Matrix 512 (501_angio_embolia_0_80_bv44_q4_matrix_512)
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (201_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 469 - robert_ouellette

No eligible series was identified.

### Exam 470 - jack_rust

No eligible series was identified.

### Exam 472 - norman_fizer

No eligible series was identified.

### Exam 473 - wanda_beckett

No eligible series was identified.

### Exam 474 - mike_adams

No eligible series was identified.

### Exam 476 - eric_scull

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 75 % (11_ds_coradseq__0_6__i26f__2__bestdiast_75_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 478 - neil_mcdonald

Selected series:
- CCT HR Heart  0,20 Bv72 Q4 -200ms Matrix 1024 (601_cct_hr_heart__0_20_bv72_q4_-200ms_matrix_1024)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 480 - mark_stratton

No eligible series was identified.

### Exam 481 - mercedes_osborne

No eligible series was identified.

### Exam 482 - roberta_silvera

No eligible series was identified.

### Exam 484 - silvia_glen

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 76 % (14_ds_coradseq__0_6__i26f__2__bestdiast_76_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 485 - jennie_wilson

Selected series:
- Monitoring 5,00 Br36 Matrix 512 (501_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]

Missing required phase buckets: aorta


### Exam 488 - pearline_dye

Selected series:
- Angio TSA  0.75  I26f  4 (14_angio_tsa__0_75__i26f__4)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 49 - martin_maclean

No eligible series was identified.

### Exam 495 - yong_khoury

Selected series:
- Arteriosa  2.0  I30f  3 (21_arteriosa__2_0__i30f__3)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 496 - lawrence_washam

No eligible series was identified.

### Exam 497 - sterling_rodriguez

No eligible series was identified.

### Exam 498 - cassandra_stanely

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 72 % (8_ds_coradseq__0_6__i26f__2__bestdiast_72_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 51 - michael_abela

No eligible series was identified.

### Exam 55 - hiram_wanzer

No eligible series was identified.

### Exam 56 - kareem_boyd

No eligible series was identified.

### Exam 58 - erin_vanetten

No eligible series was identified.

### Exam 59 - janice_goss

No eligible series was identified.

### Exam 6 - margaret_jones

No eligible series was identified.

### Exam 60 - james_wolchesky

No eligible series was identified.

### Exam 61 - fred_kuykendall

No eligible series was identified.

### Exam 62 - raymond_smith

Selected series:
- Basale 1,00 Br40 Q3 Matrix 512 (201_basale_1_00_br40_q3_matrix_512)
- Aorta 1,00 Bv44 Q4 cor Matrix 512 (501_aorta_1_00_bv44_q4_cor_matrix_512) [phase=aorta]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]


### Exam 64 - sharon_mineo

No eligible series was identified.

### Exam 66 - lola_tindall

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 71 % (9_ds_coradseq__0_6__i26f__2__bestdiast_71_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 68 - geraldine_chan

No eligible series was identified.

### Exam 69 - richard_harris

No eligible series was identified.

### Exam 71 - myrtle_buchanan

Selected series:
- Angio Aorta  1.0  I26f  3 (11_angio_aorta__1_0__i26f__3) [phase=aorta]

Missing required phase buckets: premonitoring, monitoring


### Exam 73 - stephen_gross

No eligible series was identified.

### Exam 76 - terrie_roach

Selected series:
- TORACE  2.0  I30f  3 (2_torace__2_0__i30f__3)
- Angio Aorta  1.0  I26f  3 (13_angio_aorta__1_0__i26f__3) [phase=aorta]

Missing required phase buckets: premonitoring, monitoring


### Exam 79 - carl_osburn

Selected series:
- Venosa 1,00 Br40 Q3 Matrix 512 (601_venosa_1_00_br40_q3_matrix_512)
- Aorta 0,80 Qr40 Q4 Matrix 512 SPP_ME55 (501_aorta_0_80_qr40_q4_matrix_512_spp_me55) [phase=aorta]
- Monitoring 5,00 Br36 Matrix 512 (401_monitoring_5_00_br36_matrix_512) [phase=monitoring]
- Premonitoring 5,00 Br36 Matrix 512 (301_premonitoring_5_00_br36_matrix_512) [phase=premonitoring]


### Exam 81 - whitney_messenger

No eligible series was identified.

### Exam 83 - bernice_roberts

No eligible series was identified.

### Exam 87 - raymond_anderson

No eligible series was identified.

### Exam 88 - greg_langeness

Selected series:
- TorAddome  2.0  I30f  3 (2_toraddome__2_0__i30f__3)
- Angio Aorta  1.0  I26f  3 (9_angio_aorta__1_0__i26f__3) [phase=aorta]

Missing required phase buckets: premonitoring, monitoring


### Exam 89 - irving_mccool

Selected series:
- DS_CorAdSeq  0.6  I26f  2  BestDiast 72 % (15_ds_coradseq__0_6__i26f__2__bestdiast_72_%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 90 - richard_walls

No eligible series was identified.

### Exam 92 - aaron_adams

Selected series:
- Fl_CorCTA D  0.6  I26f  4  60% (11_fl_corcta_d__0_6__i26f__4__60%)

Missing required phase buckets: aorta, premonitoring, monitoring


### Exam 94 - misty_price

No eligible series was identified.

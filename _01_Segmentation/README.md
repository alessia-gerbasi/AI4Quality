AI4Quality/_01_Segmentation/
  config/
    defaults.yaml        ← all tuneable parameters
    roi_table.yaml       ← procedure code → structures mapping
  dataio/
    roi_mapper.py        ← get_structures(code, phase) → list[str]
    dicom_converter.py   ← 3-way fallback: dcm2niix → dicom2nifti → SimpleITK
  utils/
    merged_series_resolver.py  ← finds *_collapsed.nii.gz, returns output folder name
  segmentation/
    phase_predictor.py   ← wraps totalseg_get_phase → phase.json
    task_router.py       ← maps structures → TaskCall(task, roi_subset)
    runner.py            ← calls totalsegmentator Python API per task
  visualization/
    sanity_check.py      ← CT slice + segmentation contour → sanity_check.png
  main.py                ← orchestrator
  run_log.jsonl          ← per-series JSON log (appended)


To run a real test on 2 patients:
python main.py --test-mode --test-max-n 2

To run specific patients:
python main.py --ct-ids 1 11 17

To run everything:
python main.py

To switch to a new cohort: change csv_path and output_root in config/defaults.yaml.

Running options:

| Mode | Command | Behaviour |
|---|---|---|
| **Default** | `python main.py` | Skip series where CT + all masks already exist |
| **Reprocess** | `python main.py --reprocess` | Keep existing `CT.nii.gz`, delete and redo masks + phase + PNG |
| **Full overwrite** | `python main.py --overwrite` | Delete everything (including `CT.nii.gz`) and redo from scratch |

You can also set the defaults permanently in config/defaults.yaml under `skip_existing` / `overwrite`.


## TotalSegmentator algorithm routing

Thresholds (see `task_router.py`):
- **`MIN_SLICES_FOR_SEGMENTATION = 5`** — series with fewer slices are skipped entirely (degenerate scouts/localizers kill workers)
- **`SMALL_VOLUME_THRESHOLD = 30`** — series below this are treated as monitoring/bolus-tracking volumes

| Protocol | Phase | Slices | Task | Notes |
|---|---|---|---|---|
| Any | any | <5 | **skipped** | degenerate series |
| TACCOR, TACCRG | any | ≥30 | `coronary_arteries` (licensed) | ECG-gated cardiac CT |
| TACCOR, TACCRG | any | 5–29 | **skipped** | `coronary_arteries` rejects `--fast` and needs a full cardiac volume |
| TACACP | any | ≥30 | `heartchambers_highres` (licensed) | only task with `pulmonary_artery` label |
| TACACP | any | 5–29 | **skipped** | `heartchambers_highres` rejects `--fast` and needs a full cardiac volume |
| All others (TACPEC, TACPEM, TACAAO, etc.) | arteriosa / neutral | ≥30 | `total --roi_subset aorta` (open) | full-res model |
| All others | arteriosa / neutral | 5–29 | `total --roi_subset aorta` + **fast=True, no body crop** | monitoring slice |
| All others | venosa | ≥30 | `total --roi_subset liver spleen` (open) | |
| All others | venosa | 5–29 | `total --roi_subset liver spleen` + **fast=True, no body crop** | monitoring slice |
| TACREC, TACREN, TACURO | any | ≥30 | `total --roi_subset kidney_left kidney_right` (open) | |
| TACAGC, TACCRA, TACAGE | any | ≥30 | `total --roi_subset common_carotid_artery_right common_carotid_artery_left` (open) | |
| TACANC | venosa | ≥30 | `total --roi_subset iliopsoas_left iliopsoas_right` (open) | |

**Key decisions:**
- `heartchambers_highres` and `coronary_arteries` **never** use `--fast` (the tasks explicitly forbid it) and require a full diagnostic volume (≥30 slices); monitoring bolus-tracking series for these protocols are skipped
- `heartchambers_highres` for `aorta` is only used with TACCOR/TACCRG (ECG-gated); all other protocols use the `total` task which generalises better to routine 2mm CTs
- `pulmonary_artery` always uses `heartchambers_highres` — no open task has that label
- `total` task on small volumes (5–29 slices) uses `--fast` (3mm model) + no body crop to reduce z-context requirements


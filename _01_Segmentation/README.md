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


The `skip_existing` / `overwrite` flags already exist but can't be toggled cleanly from CLI without editing the YAML. I'll add a proper `--reprocess` flag and make `--overwrite` actually clean the output directory: 

Replacing 13 lines with 38 lines in [](file:///data/alessia.gerbasi/AI4Quality/_01_Segmentation/main.py)


```

```
Also update `defaults.yaml` to document the three modes:  

Replacing 2 lines with 6 lines in [](file:///data/alessia.gerbasi/AI4Quality/_01_Segmentation/config/defaults.yaml)


```

```
Verify the dry-run still works and the new flags parse: 

Ran terminal command:  cd /data/alessia.gerbasi/AI4Quality/_01_Segmentation && python main.py --dry-run --ct-ids 1 11 --reprocess 2>&1 | head -15

All good. Three modes are now available:

| Mode | Command | Behaviour |
|---|---|---|
| **Default** | `python main.py` | Skip series where CT + all masks already exist |
| **Reprocess** | `python main.py --reprocess` | Keep existing `CT.nii.gz`, delete and redo masks + phase + PNG |
| **Full overwrite** | `python main.py --overwrite` | Delete everything (including `CT.nii.gz`) and redo from scratch |

You can also set the defaults permanently in config/defaults.yaml under `skip_existing` / `overwrite`.


---

## TotalSegmentator algorithm routing

Based on the current `task_router.py` logic:

| Protocol | Phase | Slices | Task | Reason |
|---|---|---|---|---|
| TACCOR, TACCRG | any | ≥30 | `coronary_arteries` (licensed) | ECG-gated cardiac CT — dedicated model |
| TACCOR, TACCRG | any | <30 | `coronary_arteries` (licensed) + **fast=True, no body crop** | monitoring bolus slice |
| TACACP | any | ≥30 | `heartchambers_highres` (licensed) | only task with `pulmonary_artery` label |
| TACACP | any | <30 | `heartchambers_highres` (licensed) + **fast=True, no body crop** | monitoring bolus slice |
| All others (TACPEC, TACPEM, TACAAO, etc.) | arteriosa / neutral | ≥30 | `total --roi_subset aorta` (open) | full-res model trained on diverse routine CTs |
| All others | arteriosa / neutral | <30 | `total --roi_subset aorta` + **fast=True, no body crop** | monitoring slice |
| All others | venosa | ≥30 | `total --roi_subset liver spleen` (open) | standard parenchymal |
| All others | venosa | <30 | `total --roi_subset liver spleen` + **fast=True** | monitoring slice |
| TACREC, TACREN, TACURO | any | ≥30 | `total --roi_subset kidney_left kidney_right` (open) | |
| TACAGC, TACCRA, TACAGE | any | ≥30 | `total --roi_subset common_carotid_artery_right common_carotid_artery_left` (open) | |
| TACANC | venosa | ≥30 | `total --roi_subset iliopsoas_left iliopsoas_right` (open) | |
| Any | any | 0 | **skipped** | no data |

**Key decisions:**
- `heartchambers_highres` is **only** used for `aorta` when the protocol is TACCOR/TACCRG (ECG-gated). For all other protocols (TACPEC, TACAAO, etc.) aorta uses the standard `total` task — it generalises better to routine 2mm CTs
- `pulmonary_artery` always uses `heartchambers_highres` because no open task has that label
- Small volumes (<30 slices, i.e. monitoring/bolus series) always force the 3mm fast model to reduce the minimum z-context needed


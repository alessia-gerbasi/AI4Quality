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

Made changes.
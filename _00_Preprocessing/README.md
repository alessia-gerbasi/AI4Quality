# _00_Preprocessing

Modular and extensible CT preprocessing pipeline.

## Implemented V1 modules

- Dataset scan and DICOM metadata extraction (header-only reads)
- Excel enrichment (link anonymization + injection history)
- Procedure code filtering (configurable)
- Keyword-based selector (include/exclude, precedence configurable)
- Split-series grouping by prefix/suffix pattern
- Detailed decision/report exports

## Excel mapping logic (authoritative source)

Procedure code is taken from `Order Procedure` in:

- `/data/alessia.gerbasi/DATA/CDI_NEXO_072026/0_files/Injection History Anonymized.xlsx`

The CT folder to Excel linkage is resolved through:

- `/data/alessia.gerbasi/DATA/CDI_NEXO_072026/0_files/link_anonymization.xlsx`

Deterministic join path for each CT folder `CT_QUALITY_<id>_<name>`:

1. Build `ct_key = CT_QUALITY_<id>` from folder name.
2. Lookup `ct_key` in `link_anonymization.xlsx` column `ID`.
3. From matched link row, read both `index` (e.g., `IDX_2103`) and `PAT_N` (e.g., `PAT_1648`).
4. Try to match injection rows by `index` first (primary source).
5. If no `index` hit exists, fallback to `Patient Id` match using `PAT_N`.
6. Read `Order Procedure` and `Scanner` from the chosen injection row.

## Series selection behavior

After procedure code filtering, series are selected as follows:

1. Reject series containing exclusion keywords (`mpr`, `nan`, `topogram`, `snapshot`, `none`, `vrt`, `encefalo`, `mip`, `wil`).
2. Accept all series that do not contain exclusion keywords.
3. If `venosa` or `arteriosa` appears in series text, store it as `phase_name`.

So `venosa`/`arteriosa` are used for phase tagging, not as mandatory inclusion criteria.

### Adding a new phase name

Use `selection.phase_keywords` in [AI4Quality/_00_Preprocessing/config/defaults.yaml](AI4Quality/_00_Preprocessing/config/defaults.yaml).

Example:

```yaml
selection:
  phase_keywords:
    - venosa
    - arteriosa
    - tardiva
```

You do not need to add phase names to `exclude_keywords`.

`include_keywords` is kept only for backward compatibility; phase detection now reads from `phase_keywords`.

If duplicates/conflicts exist, they are recorded in `metadata_issues.csv` with issue codes such as:

- `duplicate_link_mapping`
- `duplicate_injection_mapping`
- `index_patient_mapping_conflict`
- `missing_link_mapping`
- `missing_injection_mapping`
- `empty_order_procedure`

## Run

```bash
python _00_Preprocessing/main.py \
  --config _00_Preprocessing/config/defaults.yaml \
  --max-ct 50
```

Dry run (no output files):

```bash
python _00_Preprocessing/main.py \
  --config _00_Preprocessing/config/defaults.yaml \
  --dry-run \
  --max-ct 20
```

## How to test

Use the requested conda environment:

```bash
source /data/alessia.gerbasi/miniconda3/etc/profile.d/conda.sh
conda activate torch-gpu
```

Run a quick smoke test:

```bash
cd /data/alessia.gerbasi/AI4Quality
python _00_Preprocessing/main.py --config _00_Preprocessing/config/defaults.yaml --dry-run --max-ct 5
```

Run with artifact export:

```bash
python _00_Preprocessing/main.py --config _00_Preprocessing/config/defaults.yaml --max-ct 50
```

Validate outputs:

1. Check summary:
```bash
cat _00_Preprocessing/OUTPUTS/run_summary.json
```
2. Check that procedures are populated:
```bash
python - <<'PY'
import pandas as pd
df = pd.read_csv('/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/OUTPUTS/decisions.csv')
print('rows', len(df))
print('procedure non-null', df['procedure_code_value'].notna().sum())
print('top procedures')
print(df['procedure_code_value'].value_counts(dropna=True).head(15))
print('top rejection reasons')
print(df['reason_code'].value_counts().head(10))
PY
```
3. Inspect mapping problems:
```bash
python - <<'PY'
import pandas as pd
mi = pd.read_csv('/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/OUTPUTS/metadata_issues.csv')
print(mi['issue'].value_counts().head(20))
PY
```

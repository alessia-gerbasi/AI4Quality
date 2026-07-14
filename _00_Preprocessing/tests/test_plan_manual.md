# Manual test plan for _00_Preprocessing

## Environment

```bash
source /data/alessia.gerbasi/miniconda3/etc/profile.d/conda.sh
conda activate torch-gpu
cd /data/alessia.gerbasi/AI4Quality
```

## 1) Config sanity

```bash
python _00_Preprocessing/main.py --config _00_Preprocessing/config/defaults.yaml --dry-run --max-ct 1
```

Expected:
- pipeline starts
- scan_completed appears
- enrichment_completed appears
- no Python exceptions

## 2) Mapping correctness sample check

```bash
python _00_Preprocessing/main.py --config _00_Preprocessing/config/defaults.yaml --max-ct 20
```

Then:

```bash
python - <<'PY'
import pandas as pd
base='/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/OUTPUTS'
df=pd.read_csv(f'{base}/decisions.csv')
print('rows', len(df))
print('nonnull procedure', int(df['procedure_code_value'].notna().sum()))
print(df[['ct_folder','procedure_code_value']].drop_duplicates().head(20).to_string(index=False))
PY
```

Expected:
- non-null procedure count > 0
- procedure values look like TAC* codes

## 3) Selection behavior

```bash
python - <<'PY'
import pandas as pd
base='/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/OUTPUTS'
df=pd.read_csv(f'{base}/decisions.csv')
print('status counts')
print(df['status'].value_counts())
print('reason counts')
print(df['reason_code'].value_counts().head(15))
PY
```

Expected:
- reasons include matched_exclude_keyword, matched_include_keyword, and accepted_no_exclude_keyword
- no mass missing_procedure_code unless mappings are actually missing

Check phase extraction:

```bash
python - <<'PY'
import pandas as pd
base='/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/OUTPUTS'
df=pd.read_csv(f'{base}/decisions.csv')
print(df['phase_name'].value_counts(dropna=False).head(10))
PY
```

Expected:
- `phase_name` contains `venosa` or `arteriosa` when present in series text.
- `phase_name` is empty for other accepted non-excluded series.

## 4) Merge detection

```bash
python - <<'PY'
import pandas as pd
base='/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/OUTPUTS'
df=pd.read_csv(f'{base}/decisions.csv')
print(df['merge_status'].value_counts())
print(df[df['merge_status']=='merged_source'][['ct_folder','series_folder','merge_group_id','merge_part_index','merge_part_count']].head(20).to_string(index=False))
PY
```

Expected:
- merged_source appears for split folder groups

## 5) Metadata issue audit

```bash
python - <<'PY'
import pandas as pd
mi=pd.read_csv('/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/OUTPUTS/metadata_issues.csv')
print(mi['issue'].value_counts().head(20))
PY
```

Expected:
- issue codes are explicit and actionable

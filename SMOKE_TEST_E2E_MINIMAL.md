# Smoke Test E2E Minimal (Segmentation -> QualityCheck -> RCA)

Esegui dalla root progetto `AI4Quality`.

## Smoke test non distruttivo (output dedicati)

1. Segmentation (1 caso, skip se gia processato)

```bash
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python _01_Segmentation/main.py --test-mode --test-max-n 1 --skip-existing
```

2. Quality Check (config unificato + output smoke dedicato)

```bash
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python _02_QualityCheck/main.py --rules config/common/ct_protocols.yaml --max-cases 10 --output-dir _02_QualityCheck/OUTPUTS_smoke
```

3. Root Cause Analysis batch (output smoke dedicato)

```bash
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python _03_RootCauseAnalysis/batch_analysis.py --schema timing_schema --output _03_RootCauseAnalysis/rca_results_smoke.csv
```

## Output smoke da verificare

- `_01_Segmentation/run_log.jsonl`
- `_02_QualityCheck/OUTPUTS_smoke/roi_hu_qc_results.csv`
- `_03_RootCauseAnalysis/rca_results_smoke.csv`

## Rigenerare i risultati completi in OUTPUTS principale

Per ricreare i risultati Quality Check completi nella cartella principale `_02_QualityCheck/OUTPUTS`, esegui senza `--max-cases` e senza `--output-dir`:

```bash
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python _02_QualityCheck/main.py --rules config/common/ct_protocols.yaml
```

Questo comando sovrascrive i file in `_02_QualityCheck/OUTPUTS` con una run completa.

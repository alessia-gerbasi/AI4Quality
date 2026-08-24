#!/usr/bin/env bash
set -euo pipefail

cd /data/alessia.gerbasi/AI4Quality
PY=/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python

# 1) Segmentation smoke (non distruttivo)
$PY _01_Segmentation/main.py --test-mode --test-max-n 1 --skip-existing

# 2) QualityCheck smoke -> output dedicato
$PY _02_QualityCheck/main.py \
  --rules config/common/ct_protocols.yaml \
  --max-cases 10 \
  --output-dir _02_QualityCheck/OUTPUTS_smoke

# 3) RCA batch smoke -> output dedicato
$PY _03_RootCauseAnalysis/batch_analysis.py \
  --schema timing_schema \
  --output _03_RootCauseAnalysis/rca_results_smoke.csv

echo "Smoke test completed."
echo "QC smoke outputs: _02_QualityCheck/OUTPUTS_smoke"
echo "RCA smoke output: _03_RootCauseAnalysis/rca_results_smoke.csv"

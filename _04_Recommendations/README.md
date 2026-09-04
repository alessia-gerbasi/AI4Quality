# AI4Quality Recommendations

This module combines image-quality results, RCA findings, injector/patient data, and a local LLM recommendation for the complete exam.

## Run

```bash
cd /data/alessia.gerbasi/AI4Quality
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python -m streamlit run _04_Recommendations/dashboard.py --server.port 8506
```

Use **Refresh database** after rerunning RCA batches. The SQLite dataset is written to `data/ai4quality_recommendations.sqlite`.

## Generate recommendations without the dashboard

The dashboard is only a viewer. After preprocessing, quality checking, and RCA have completed, generate and store recommendations for every QC/RCA patient with:

```bash
cd /data/alessia.gerbasi/AI4Quality
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python _04_Recommendations/generate_recommendations.py
```

To test one patient first:

```bash
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python _04_Recommendations/generate_recommendations.py --ct-id 472
```

The command rebuilds the source SQLite tables, calls vLLM, and stores one current exam recommendation per patient. It fails rather than storing a fallback if the model cannot be loaded or generated.

Patient-level enhancement warnings are calculated during quality checking and stored in `patient_hu_qc_summary.csv` and the SQLite `patient_warnings` table. Re-run quality checking, RCA batches, and then **Refresh database** to propagate updated warning priorities through the pipeline.

## Local LLM

The adapter uses vLLM and defaults to `google/gemma-3-27b-it`. It exposes only the fourth physical GPU with `CUDA_VISIBLE_DEVICES=3` before importing vLLM; inside the process this device is therefore visible as `cuda:0`.

Set `AI4QUALITY_LLM_MODEL` or pass `--model` to use another Hugging Face model supported by vLLM. The model is loaded lazily on the first recommendation request and remains cached for subsequent requests.

The prompt intentionally requests two short paragraphs and at most three concrete protocol actions, so recommendations remain readable rather than becoming a long report.

The database stores source data as JSON as well as normalized tables. Recommendations are stored at exam scope with the model, source, input, and output text.

## Open the database

The database is at:

```text
_04_Recommendations/data/ai4quality_recommendations.sqlite
```

Use the dashboard's **Download SQLite database** button if the remote VS Code extension cannot access the workspace path. Open the downloaded file with DB Browser for SQLite, or use the **Download SQL dump** button and open the `.sql` file in any editor.

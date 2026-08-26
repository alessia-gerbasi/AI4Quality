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

The command rebuilds the source SQLite tables, calls Ollama, and stores one current exam recommendation per patient. It fails rather than storing a fallback if Ollama is unavailable.

Patient-level enhancement warnings are calculated during quality checking and stored in `patient_hu_qc_summary.csv` and the SQLite `patient_warnings` table. Re-run quality checking, RCA batches, and then **Refresh database** to propagate updated warning priorities through the pipeline.

## Local LLM

The adapter uses Ollama's local HTTP API and defaults to `qwen2.5:7b`. This is the recommended interactive model for this project: it is already installed, fast enough for case review, and produces clear concise summaries. `qwen3:32b` is a stronger but slower option for offline batch generation if more GPU/RAM is available:

```bash
ollama pull qwen2.5:7b
ollama serve
```

Set `AI4QUALITY_LLM_MODEL` to another installed Ollama model. Ollama must be running when a recommendation is generated; the dashboard reports a clear error if the model is unavailable and does not create a fallback recommendation.

The prompt intentionally requests two short paragraphs and at most three concrete protocol actions, so recommendations remain readable rather than becoming a long report.

The database stores source data as JSON as well as normalized tables. Recommendations are stored at exam scope with the model, source, input, and output text.

## Open the database

The database is at:

```text
_04_Recommendations/data/ai4quality_recommendations.sqlite
```

Use the dashboard's **Download SQLite database** button if the remote VS Code extension cannot access the workspace path. Open the downloaded file with DB Browser for SQLite, or use the **Download SQL dump** button and open the `.sql` file in any editor.

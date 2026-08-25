# AI4Quality Recommendations

This module combines image-quality results, RCA findings, injector/patient data, and optional local LLM recommendations.

## Run

```bash
cd /data/alessia.gerbasi/AI4Quality
/data/alessia.gerbasi/miniconda3/envs/ctq/bin/python -m streamlit run _04_Recommendations/dashboard.py --server.port 8506
```

Use **Refresh database** after rerunning RCA batches. The SQLite dataset is written to `data/ai4quality_recommendations.sqlite`.

## Optional local LLM

The adapter uses Ollama's local HTTP API and defaults to `qwen2.5:7b`. This is the recommended interactive model for this project: it is already installed, fast enough for case review, and produces clear concise summaries. `qwen3:32b` is a stronger but slower option for offline batch generation if more GPU/RAM is available:

```bash
ollama pull qwen2.5:7b
ollama serve
```

Set `AI4QUALITY_LLM_MODEL` to another installed Ollama model. If Ollama is unavailable, the dashboard generates and stores a deterministic fallback recommendation instead.

The prompt intentionally requests two short paragraphs and at most three concrete protocol actions, so recommendations remain readable rather than becoming a long report.

The database stores source data as JSON as well as normalized tables, including `recommendations` with scope (`series` or `exam`), model, source, input, and output text.

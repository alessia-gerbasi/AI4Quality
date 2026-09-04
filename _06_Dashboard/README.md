# AI4Quality Final Clinical Dashboard

This dashboard is the final review surface for clinicians. It combines image quality results, root cause analysis, warnings, injector data, and stored LLM recommendations in one Streamlit app.

The app does not call the LLM during page rendering. Generate recommendations before opening the dashboard:

```bash
python _04_Recommendations/generate_recommendations.py
```

Then launch the final dashboard:

```bash
streamlit run _07_Dashboard/dashboard.py
```

Use `Aggiorna database` in the sidebar after rerunning QC, RCA, or the recommendation batch job.
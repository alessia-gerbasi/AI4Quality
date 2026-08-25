"""Optional local LLM recommendations with a deterministic fallback."""
import json
import os
from urllib import request

DEFAULT_MODEL = os.getenv("AI4QUALITY_LLM_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")


def fallback_recommendation(series: dict, findings: list[dict], exam_findings: list[dict]) -> str:
    labels = [str(item.get("diagnosis", item.get("rca_label", ""))) for item in findings]
    actions = []
    if any("pressure" in label for label in labels):
        actions.append("review injection access and pressure limits")
    if any("dose" in label or "volume" in label or "idr" in label or "flow" in label for label in labels):
        actions.append("review programmed dose, volume, concentration, duration, and flow settings")
    if any("timing" in label or label in {"early", "late"} for label in labels):
        actions.append("review bolus timing and acquisition delay")
    if any("liver" in label or "egfr" in label for label in labels):
        actions.append("consider the patient's renal function and liver baseline during protocol review")
    if not actions:
        actions.append("review the recorded image-quality findings and injection metadata")
    finding_text = ', '.join(labels) if labels else 'no explicit RCA finding'
    return (
        f"The series {series.get('series_folder', 'unknown')} shows {finding_text}. "
        "These findings should be interpreted together with the image-quality results and the other series in the examination. "
        f"Protocol actions: {'; '.join(actions[:3])}."
    )


def generate_recommendation(series: dict, findings: list[dict], exam_findings: list[dict], model: str = DEFAULT_MODEL) -> tuple[str, str]:
    """Return recommendation text and status (llm or fallback)."""
    payload = {
        "series": series,
        "series_findings": findings,
        "exam_findings": exam_findings,
    }
    prompt = (
        "You are a CT quality specialist. Write a short, readable clinical recommendation in plain text. "
        "Use exactly 2 short paragraphs: first explain what was wrong in this series and cite only the supplied evidence; "
        "second relate it briefly to the patient's other series. End with one sentence starting 'Protocol actions:' "
        "and give at most 3 concrete protocol corrections separated by semicolons. "
        "Do not use headings, markdown, numbered lists, long introductions, or invented values.\n\n"
        + json.dumps(payload, default=str)
    )
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 350},
    }).encode()
    try:
        with request.urlopen(request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}), timeout=8) as response:
            result = json.loads(response.read().decode())
        text = str(result.get("response", "")).strip()
        if text:
            return text, f"llm ({model})"
    except Exception:
        pass
    return fallback_recommendation(series, findings, exam_findings), "fallback"

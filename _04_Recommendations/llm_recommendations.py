"""Local LLM recommendations."""
import json
import os
from urllib import request
from urllib.error import HTTPError, URLError

DEFAULT_MODEL = os.getenv("AI4QUALITY_LLM_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT = float(os.getenv("AI4QUALITY_LLM_TIMEOUT", "120"))


def generate_recommendation(series: dict, findings: list[dict], exam_findings: list[dict], model: str = DEFAULT_MODEL) -> tuple[str, str]:
    """Return an LLM recommendation or raise an actionable service error."""
    payload = {
        "series": series,
        "series_findings": findings,
        "exam_findings": exam_findings,
        "notes": series.get("notes", []),
    }
    prompt = (
        "You are a CT quality specialist. Write a short, readable clinical recommendation in plain text. "
        "Use exactly 2 short paragraphs: first explain only the actual problems across the examination and cite only supplied evidence. "
        "In exam_findings, the quality statuses optimal, acceptable_low, and acceptable_high mean acceptable quality, not a problem; never report them as failures or recommend correcting them. "
        "Treat the status field as authoritative and do not reinterpret a value as outside a threshold when its status is acceptable. "
        "Use any supplied notes when they contain clinically interpretable information, but do not treat a note as a problem unless the supplied findings support it. "
        "Use the supplied patient_warning as authoritative patient-level context and explain its priority and evidence when present. "
        "Treat segmentation_warning as a separate warning: mention missing ROIs as segmentation issues, not as enhancement failures. "
        "A quality status of missing means that the ROI could not be measured, usually because segmentation was unavailable; say that the phase or organ is not assessable. "
        "Never describe a phase with missing ROIs as having no measurement issues, adequate enhancement, or a confirmed normal result. "
        "Do not recommend changing contrast or timing based only on a missing measurement; recommend reviewing segmentation or reacquiring data only when supported by the supplied warning. "
        "Do not invent missing-data problems or protocol actions unless they are explicitly present in series_findings. "
        "You must explicitly incorporate every item in series_findings, including its finding and associated Series, into the narrative; do not omit less prominent findings such as eGFR. "
        "A Series is one acquisition/reconstruction phase. Multiple ROI or organ evaluations with the same Series name are measurements within that one series, not separate series or phases; group them together and state the evaluated organs when relevant. "
        "Use only the series supplied in the series field; do not infer or mention monitoring or other retained series that were not quality-checked. "
        "Then state how the problematic series relate to one another, or state that there are no problematic series. End with one sentence starting 'Protocol actions:' "
        "If there are no problematic series, end with exactly 'Protocol actions: no corrective action indicated.' Otherwise give at most 3 concrete protocol corrections separated by semicolons. "
        "Write as connected prose only. Do not use headings, markdown, bullets, numbered lists, 'additional findings', or a separate evidence summary. Do not repeat the same evidence unnecessarily, and do not invent values.\n\n"
        + json.dumps(payload, default=str)
    )
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 350},
    }).encode()
    try:
        with request.urlopen(request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}), timeout=OLLAMA_TIMEOUT) as response:
            result = json.loads(response.read().decode())
        text = str(result.get("response", "")).strip()
        if text:
            if not findings and "Protocol actions:" in text:
                text = text.split("Protocol actions:", 1)[0].rstrip()
                text += "\n\nProtocol actions: no corrective action indicated."
            return text, f"llm ({model})"
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM recommendation failed using {model} at {OLLAMA_URL}: {exc}") from exc

    raise RuntimeError(f"LLM recommendation returned no text using {model} at {OLLAMA_URL}")

"""Local LLM recommendations."""
import json
import os
import re
from urllib import request
from urllib.error import HTTPError, URLError

DEFAULT_MODEL = os.getenv("AI4QUALITY_LLM_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT = float(os.getenv("AI4QUALITY_LLM_TIMEOUT", "120"))


def image_quality_findings(row: dict) -> list[dict]:
    findings = []
    status = str(row.get("status", "")).lower()
    if status not in {"optimal", "acceptable_low", "acceptable_high", "nan"}:
        findings.append({
            "Schema": "image_quality",
            "Series": row.get("series_folder"),
            "Finding": f"{row.get('roi_name')} {row.get('status')}",
            "Explanation": f"{row.get('metric_name')}: evaluated value {row.get('evaluated_value')}",
            "Recommendations": "Review image-quality measurement and acquisition protocol.",
        })
    if str(row.get("attenuation_consistency", "")).lower() == "incoherent":
        findings.append({
            "Schema": "image_quality",
            "Series": row.get("series_folder"),
            "Finding": f"{row.get('roi_name')} incoherent attenuation",
            "Explanation": row.get("attenuation_message"),
            "Recommendations": "Review contrast timing and exclude pathological causes of regional attenuation change.",
        })
    return findings


def _numeric_tokens(value: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", value or "")


def _protocol_detail_is_present(text: str, finding: dict) -> bool:
    text_lower = text.lower()
    finding_text = str(finding.get("Finding", "")).lower()
    explanation = str(finding.get("Explanation", ""))
    explanation_lower = explanation.lower()

    if "weight" in finding_text:
        return "weight" in text_lower and any(word in text_lower for word in ("missing", "unavailable"))
    if "saline" in finding_text:
        has_saline_problem = "saline" in text_lower and any(word in text_lower for word in ("high", "excess", "above", "exceed"))
        numbers = _numeric_tokens(explanation)
        return has_saline_problem and (not numbers or numbers[0] in text)
    return finding_text in text_lower or explanation_lower in text_lower


def _ensure_protocol_evidence(text: str, findings: list[dict]) -> str:
    missing_details = []
    for finding in findings:
        if finding.get("Schema") != "protocol_schema_v1":
            continue
        explanation = str(finding.get("Explanation", "")).strip()
        if not explanation or _protocol_detail_is_present(text, finding):
            continue
        series = str(finding.get("Series", "")).strip()
        finding_name = str(finding.get("Finding", "Protocol finding")).strip()
        location = f" in {series}" if series else ""
        missing_details.append(f"{finding_name}{location}: {explanation}")

    if not missing_details:
        return text

    detail_sentence = "Protocol details: " + "; ".join(missing_details) + "."
    if "Protocol actions:" in text:
        narrative, actions = text.split("Protocol actions:", 1)
        return f"{narrative.rstrip()} {detail_sentence}\n\nProtocol actions:{actions}"
    return f"{text.rstrip()}\n\n{detail_sentence}"


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
        "Treat every supplied incoherent attenuation finding as an image-quality issue: cite its proximal and distal HU evidence and state that, in the absence of pathological issues, it may suggest a timing-related acquisition error. "
        "Use any supplied notes when they contain clinically interpretable information, but do not treat a note as a problem unless the supplied findings support it. "
        "Use the supplied patient_warning as authoritative patient-level context and explain its priority and evidence when present. "
        "Treat segmentation_warning as a separate warning: mention missing ROIs as segmentation issues, not as enhancement failures. "
        "A quality status of missing means that the ROI could not be measured, usually because segmentation was unavailable; say that the phase or organ is not assessable. "
        "Never describe a phase with missing ROIs as having no measurement issues, adequate enhancement, or a confirmed normal result. "
        "Do not recommend changing contrast or timing based only on a missing measurement; recommend reviewing segmentation or reacquiring data only when supported by the supplied warning. "
        "Do not invent missing-data problems or protocol actions unless they are explicitly present in series_findings. "
        "For protocol_schema_v1 findings, mention each supplied protocol problem in the first paragraph using its supplied evidence; do not leave protocol findings only for the Protocol actions sentence. "
        "If patient weight is missing, say patient weight is missing. If saline volume is high or excessive, say saline volume is high or excessive and cite the measured saline volume when supplied. "
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
            text = _ensure_protocol_evidence(text, findings)
            return text, f"llm ({model})"
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM recommendation failed using {model} at {OLLAMA_URL}: {exc}") from exc

    raise RuntimeError(f"LLM recommendation returned no text using {model} at {OLLAMA_URL}")

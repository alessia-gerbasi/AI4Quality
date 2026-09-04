"""Local LLM recommendations."""
import json
import os
import re
from urllib import request
from urllib.error import HTTPError, URLError

DEFAULT_MODEL = os.getenv("AI4QUALITY_LLM_MODEL", "gemma4:31b")
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
        "You are a CT quality specialist writing a clinical recommendation for radiologists. Be precise, direct, and clinician-friendly. "
        "Write exactly 2 short paragraphs: (1) describe only the actual image quality problems found, citing specific HU values and ROI names; (2) explain any protocol issues. "
        "Quality statuses of optimal, acceptable_low, and acceptable_high are acceptable—do not report them as problems. "
        "If a status is acceptable, never recommend correcting it. "
        "For incoherent vessel attenuation: state the proximal and distal HU values, explain they differ in severity, and note this may indicate a timing acquisition error if no pathology explains it. "
        "Mention patient warnings when supplied and explain their clinical significance. "
        "Segmentation warnings = missing ROI measurements. Missing measurements mean 'not assessable,' not a failure. "
        "Do not invent problems or protocol actions not explicitly in the findings. "
        "Protocol details from series_findings must be integrated into the main text with specific values, not isolated in the actions line. "
        "When weight is missing, state it clearly. When saline volume exceeds the acceptable range, cite the measured and expected values. "
        "Include all supplied findings (ROI names, HU values, ranges). Explain how problematic series relate to each other. "
        "Conclude with: 'Protocol actions: ' followed by at most 3 specific, actionable corrections separated by semicolons. "
        "If no corrections are needed: 'Protocol actions: no corrective action indicated.' "
        "Use clear prose only. No bullets, headings, markdown, or invented values.\n\n"
        + json.dumps(payload, default=str)
    )
    print("Prompt length:", len(prompt))
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False, ## disable thinking
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

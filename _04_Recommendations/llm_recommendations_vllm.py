"""
Local LLM recommendations using vLLM.
"""

import json
import os
import re

# ------------------------------------------------------------------
# GPU SELECTION
# ------------------------------------------------------------------

# Usa esclusivamente la quarta GPU fisica (cuda:3)
# Deve essere impostato PRIMA di importare torch/vllm
os.environ["CUDA_VISIBLE_DEVICES"] = "3"

from vllm import LLM, SamplingParams


# ------------------------------------------------------------------
# MODEL CONFIGURATION
# ------------------------------------------------------------------

DEFAULT_MODEL = os.getenv(
    "AI4QUALITY_LLM_MODEL",
    "google/gemma-3-27b-it",
)

# inizializzato una sola volta
_LLM = None
_LOADED_MODEL = None

_SAMPLING_PARAMS = SamplingParams(
    temperature=0.1,
    max_tokens=350,
)


def get_llm(model: str = DEFAULT_MODEL):
    global _LLM, _LOADED_MODEL

    if _LLM is None or _LOADED_MODEL != model:
        print(f"Loading vLLM model: {model}")

        _LLM = LLM(
            model=model,
            trust_remote_code=True,
            gpu_memory_utilization=0.90,
            max_model_len=32768,
        )
        _LOADED_MODEL = model

    return _LLM


# ------------------------------------------------------------------
# FINDINGS
# ------------------------------------------------------------------

def image_quality_findings(row: dict) -> list[dict]:
    findings = []

    status = str(row.get("status", "")).lower()

    if status not in {
        "optimal",
        "acceptable_low",
        "acceptable_high",
        "nan",
    }:
        findings.append(
            {
                "Schema": "image_quality",
                "Series": row.get("series_folder"),
                "Finding": f"{row.get('roi_name')} {row.get('status')}",
                "Explanation": (
                    f"{row.get('metric_name')}: "
                    f"evaluated value {row.get('evaluated_value')}"
                ),
                "Recommendations": (
                    "Review image-quality measurement "
                    "and acquisition protocol."
                ),
            }
        )

    if str(
        row.get("attenuation_consistency", "")
    ).lower() == "incoherent":
        findings.append(
            {
                "Schema": "image_quality",
                "Series": row.get("series_folder"),
                "Finding": (
                    f"{row.get('roi_name')} "
                    "incoherent attenuation"
                ),
                "Explanation": row.get(
                    "attenuation_message"
                ),
                "Recommendations": (
                    "Review contrast timing and "
                    "exclude pathological causes of "
                    "regional attenuation change."
                ),
            }
        )

    return findings


def _numeric_tokens(value: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", value or "")


def _protocol_detail_is_present(
    text: str,
    finding: dict,
) -> bool:

    text_lower = text.lower()

    finding_text = str(
        finding.get("Finding", "")
    ).lower()

    explanation = str(
        finding.get("Explanation", "")
    )

    explanation_lower = explanation.lower()

    if "weight" in finding_text:
        return (
            "weight" in text_lower
            and any(
                word in text_lower
                for word in (
                    "missing",
                    "unavailable",
                )
            )
        )

    if "saline" in finding_text:

        has_saline_problem = (
            "saline" in text_lower
            and any(
                word in text_lower
                for word in (
                    "high",
                    "excess",
                    "above",
                    "exceed",
                )
            )
        )

        numbers = _numeric_tokens(
            explanation
        )

        return (
            has_saline_problem
            and (
                not numbers
                or numbers[0] in text
            )
        )

    return (
        finding_text in text_lower
        or explanation_lower in text_lower
    )


def _ensure_protocol_evidence(
    text: str,
    findings: list[dict],
) -> str:

    missing_details = []

    for finding in findings:

        if (
            finding.get("Schema")
            != "protocol_schema_v1"
        ):
            continue

        explanation = str(
            finding.get("Explanation", "")
        ).strip()

        if (
            not explanation
            or _protocol_detail_is_present(
                text,
                finding,
            )
        ):
            continue

        series = str(
            finding.get("Series", "")
        ).strip()

        finding_name = str(
            finding.get(
                "Finding",
                "Protocol finding",
            )
        ).strip()

        location = (
            f" in {series}"
            if series
            else ""
        )

        missing_details.append(
            f"{finding_name}{location}: "
            f"{explanation}"
        )

    if not missing_details:
        return text

    detail_sentence = (
        "Protocol details: "
        + "; ".join(missing_details)
        + "."
    )

    if "Protocol actions:" in text:

        narrative, actions = text.split(
            "Protocol actions:",
            1,
        )

        return (
            f"{narrative.rstrip()} "
            f"{detail_sentence}\n\n"
            f"Protocol actions:{actions}"
        )

    return (
        f"{text.rstrip()}\n\n"
        f"{detail_sentence}"
    )


def _ensure_clinical_evidence(
    text: str,
    exam_findings: list[dict],
) -> str:
    missing_details = []

    for finding in exam_findings:
        if finding.get("rca_schema") != "other_schema_v1":
            continue

        label = str(finding.get("rca_label", "")).lower()
        explanation = str(finding.get("rca_explanation", "")).strip()
        if "egfr" not in label or not explanation:
            continue
        if explanation.lower() not in text.lower():
            missing_details.append(explanation)

    if not missing_details:
        return text

    detail_sentence = "Clinical findings: " + "; ".join(missing_details) + "."
    if "Protocol actions:" in text:
        narrative, actions = text.split("Protocol actions:", 1)
        return f"{narrative.rstrip()} {detail_sentence}\n\nProtocol actions:{actions}"
    return f"{text.rstrip()}\n\n{detail_sentence}"


# ------------------------------------------------------------------
# RECOMMENDATION GENERATION
# ------------------------------------------------------------------

def generate_recommendation(
    series: dict,
    findings: list[dict],
    exam_findings: list[dict],
    model: str = DEFAULT_MODEL,
) -> tuple[str, str]:

    payload = {
        "series": series,
        "series_findings": findings,
        "exam_findings": exam_findings,
        "notes": series.get(
            "notes",
            [],
        ),
    }

    prompt = (
        "You are a CT quality specialist "
        "writing a clinical recommendation "
        "for radiologists. "
        "Be precise, direct, and "
        "clinician-friendly. "
        "Write exactly 2 short paragraphs: "
        "(1) describe only the actual image "
        "quality problems found, citing "
        "specific HU values and ROI names; "
        "(2) explain any protocol issues. "
        "Quality statuses of optimal, "
        "acceptable_low, and acceptable_high "
        "are acceptable and must not be "
        "reported as problems. "
        "If a status is acceptable, never "
        "recommend correcting it. "
        "For incoherent vessel attenuation: "
        "state the proximal and distal HU "
        "values, explain they differ in "
        "severity, and note that this may "
        "indicate a timing acquisition error "
        "if no pathology explains it. "
        "Mention patient warnings when "
        "supplied and explain their clinical "
        "significance. "
        "Mention every clinically relevant finding "
        "in exam_findings, ALWAYS including eGFR: report "
        "the exact value, units, and stage when supplied, "
        "and explain its relevance to contrast administration. "
        "Segmentation warnings mean "
        "measurements are not assessable, "
        "not failures. "
        "Do not invent findings or protocol actions. "
        "Protocol details must be integrated into "
        "the main text with specific values. "
        "When weight is missing, state exactly that "
        "the optimal dose could not be computed because "
        "patient weight is missing; do not attribute the "
        "dose RCA to timing or another cause. "
        "When saline volume exceeds the acceptable "
        "range, cite measured and expected values. "
        "Include all supplied findings and explain "
        "how problematic series relate to each other. "
        "Conclude with: 'Protocol actions:' followed "
        "by at most 3 specific actions separated by "
        "semicolons. If no corrections are needed, "
        "write 'Protocol actions: no corrective action "
        "indicated.' Use clear prose only: no bullets, "
        "headings, markdown, or invented values.\n\n"
        + json.dumps(payload, default=str)
    )

    print("Prompt length:", len(prompt))

    try:
        llm = get_llm(model)
        outputs = llm.generate(
            [prompt],
            _SAMPLING_PARAMS,
        )

        text = (
            outputs[0]
            .outputs[0]
            .text.strip()
        )

        if not text:
            raise RuntimeError(
                "Empty model response"
            )

        if (
            not findings
            and "Protocol actions:" in text
        ):
            text = (
                text.split(
                    "Protocol actions:",
                    1
                )[0]
                .rstrip()
            )

            text += (
                "\n\n"
                "Protocol actions: no corrective action indicated."
            )

        text = _ensure_protocol_evidence(text, findings)
        text = _ensure_clinical_evidence(text, exam_findings)
        return text, f"llm ({model})"
    except Exception as exc:
        raise RuntimeError(
            f"LLM recommendation failed using vLLM model {model}: {exc}"
        ) from exc
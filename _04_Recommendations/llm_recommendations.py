"""LLM recommendation backend used by the dashboard and batch pipeline."""

from llm_recommendations_vllm import (
    DEFAULT_MODEL,
    generate_recommendation,
    image_quality_findings,
)

__all__ = [
    "DEFAULT_MODEL",
    "generate_recommendation",
    "image_quality_findings",
]
from app.core.config import Settings
from app.graph.enrichment_llm import (
    DeterministicEnrichmentLLM,
    EnrichmentLLM,
    OpenAIEnrichmentLLM,
)
from app.graph.nodes import DeterministicDraftLLM, DraftLLM
from app.graph.openai_llm import OpenAIDraftLLM


def build_draft_llm(settings: Settings) -> DraftLLM:
    if settings.llm_provider.lower() == "openai":
        if not settings.openai_api_key:
            return DeterministicDraftLLM()
        return OpenAIDraftLLM(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            reasoning_effort=settings.openai_reasoning_effort,
            base_url=settings.openai_base_url,
        )
    return DeterministicDraftLLM()


def build_enrichment_llm(settings: Settings) -> EnrichmentLLM:
    if settings.enrichment_provider.lower() == "openai":
        if not settings.openai_api_key:
            return DeterministicEnrichmentLLM(
                min_confidence_to_draft=settings.enrichment_min_confidence_to_draft,
            )
        return OpenAIEnrichmentLLM(
            api_key=settings.openai_api_key,
            model=settings.enrichment_model,
            reasoning_effort=settings.enrichment_reasoning_effort,
            base_url=settings.openai_base_url,
            require_evidence=settings.enrichment_require_evidence,
            min_confidence_to_draft=settings.enrichment_min_confidence_to_draft,
        )
    return DeterministicEnrichmentLLM(
        min_confidence_to_draft=settings.enrichment_min_confidence_to_draft,
    )

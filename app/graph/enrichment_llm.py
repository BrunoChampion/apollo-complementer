from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from app.core.langfuse import get_tracer
from app.domain.enrichment import (
    EnrichmentResult,
    EnrichmentStatus,
    EvidenceItem,
    EvidenceSourceType,
    RecommendedAction,
)


class EnrichmentLLM(Protocol):
    def enrich_company(
        self,
        *,
        enrichment_id: str,
        run_id: str | None,
        lead_id: str | None,
        company_name: str,
        company_website: str | None,
        company_domain: str | None,
        prospect_name: str | None,
        prospect_title: str | None,
        industry: str | None,
        country: str | None,
        manual_context: str | None,
        web_results: list[dict[str, Any]],
    ) -> EnrichmentResult: ...


class OpenAIEnrichmentLLM:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60,
        require_evidence: bool = True,
        min_confidence_to_draft: int = 65,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.require_evidence = require_evidence
        self.min_confidence_to_draft = min_confidence_to_draft

    def enrich_company(
        self,
        *,
        enrichment_id: str,
        run_id: str | None,
        lead_id: str | None,
        company_name: str,
        company_website: str | None,
        company_domain: str | None,
        prospect_name: str | None,
        prospect_title: str | None,
        industry: str | None,
        country: str | None,
        manual_context: str | None,
        web_results: list[dict[str, Any]],
    ) -> EnrichmentResult:
        payload = {
            "company_name": company_name,
            "company_website": company_website,
            "company_domain": company_domain,
            "prospect_name": prospect_name,
            "prospect_title": prospect_title,
            "industry": industry,
            "country": country,
            "manual_context": manual_context,
            "web_results": [
                {
                    "url": r.get("url"),
                    "status": r.get("status"),
                    "text_preview": (r.get("text") or "")[:800],
                }
                for r in web_results
            ],
        }
        result = self._json_response(self._build_instructions(), payload)
        return self._parse_result(
            result,
            enrichment_id=enrichment_id,
            run_id=run_id,
            lead_id=lead_id,
        )

    def _build_instructions(self) -> str:
        return (
            "You are NYVEX's company enrichment researcher. Analyze the provided company data "
            "and web content to produce a structured enrichment output. "
            "Be factual, skeptical, and never invent facts not present in the input.\n\n"
            "Return a JSON object with these exact keys:\n"
            "- company_summary: concise 1-3 sentence description (or null if insufficient data)\n"
            "- b2b_fit: true/false/null — is this clearly a B2B company?\n"
            "- operational_pain_hypothesis: what operational pain might they have? (or null)\n"
            "- possible_ai_use_case: what AI/automation use case could be relevant? (or null)\n"
            "- personalization_angle: angle for outreach personalization (or null)\n"
            "- trigger_summary: what signal makes this a good time to reach out? (or null)\n"
            "- risk_flags: array of strings listing risks or red flags\n"
            "- evidence_items: array of objects, each with {claim, source_type, source_url, "
            "quote_or_summary, confidence (0-100), used_in_message (boolean)}\n"
            "- confidence_score: integer 0-100 reflecting overall evidence strength\n"
            "- recommended_action: one of 'draft', 'needs_manual_research', "
            "'needs_email_verification', 'discard', 'wait'\n\n"
            "Rules:\n"
            "1. If web_results are empty or weak, set risk_flags to include 'insufficient_data' "
            "and recommended_action to 'needs_manual_research'.\n"
            "2. Only recommend 'draft' if there is at least one evidence item with a concrete "
            "claim backed by source text.\n"
            "3. Do not include evidence without a specific claim and source.\n"
            "4. confidence_score should reflect how much you actually know, not optimism."
        )

    def _json_response(self, instructions: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self.model,
            "reasoning": {"effort": self.reasoning_effort},
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are NYVEX's sales research assistant. "
                        "Be factual, specific, concise, and skeptical of weak evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        instructions
                        + "\n\nINPUT:\n"
                        + json.dumps(payload, ensure_ascii=False)
                    ),
                },
            ],
        }
        tracer = get_tracer()
        with tracer.generation(
            "enrichment.openai.responses",
            model=self.model,
            input={
                "instruction_preview": instructions[:500],
                "company_name": payload.get("company_name"),
                "company_domain": payload.get("company_domain"),
                "country": payload.get("country"),
                "web_result_count": len(payload.get("web_results") or []),
            },
            metadata={
                "feature": "enrichment",
                "reasoning_effort": self.reasoning_effort,
                "base_url": self.base_url,
            },
        ) as generation:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
            generation.update(
                output=_summarize_response(data),
                usage=_usage_details(data),
                metadata={"response_id": data.get("id")},
            )

        text = self._extract_output_text(data)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            parsed = json.loads(text[start : end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI response was not a JSON object.")
        return parsed

    def _extract_output_text(self, response: dict[str, Any]) -> str:
        output_text = response.get("output_text")
        if isinstance(output_text, str):
            return output_text
        chunks: list[str] = []
        for item in response.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
        return "\n".join(chunks)

    def _parse_result(
        self,
        data: dict[str, Any],
        *,
        enrichment_id: str,
        run_id: str | None,
        lead_id: str | None,
    ) -> EnrichmentResult:
        evidence_raw = data.get("evidence_items") or []
        evidence_items = []
        for item in evidence_raw:
            if not isinstance(item, dict):
                continue
            try:
                evidence_items.append(EvidenceItem.model_validate(item))
            except Exception:
                continue

        raw_action = data.get("recommended_action", "needs_manual_research")
        try:
            recommended_action = RecommendedAction(raw_action)
        except ValueError:
            recommended_action = RecommendedAction.NEEDS_MANUAL_RESEARCH

        if not evidence_items and self.require_evidence:
            enrichment_status = EnrichmentStatus.INSUFFICIENT_DATA
            recommended_action = RecommendedAction.NEEDS_MANUAL_RESEARCH
        else:
            enrichment_status = EnrichmentStatus.ENRICHED

        confidence = data.get("confidence_score")
        try:
            confidence = int(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence = None

        if confidence is not None and confidence < self.min_confidence_to_draft:
            recommended_action = RecommendedAction.NEEDS_MANUAL_RESEARCH

        return EnrichmentResult(
            enrichment_id=enrichment_id,
            run_id=run_id,
            lead_id=lead_id,
            company_name=data.get("company_name") or data.get("company_name"),
            company_website=data.get("company_website"),
            prospect_name=data.get("prospect_name"),
            prospect_title=data.get("prospect_title"),
            enrichment_status=enrichment_status,
            company_summary=data.get("company_summary"),
            b2b_fit=data.get("b2b_fit"),
            operational_pain_hypothesis=data.get("operational_pain_hypothesis"),
            possible_ai_use_case=data.get("possible_ai_use_case"),
            personalization_angle=data.get("personalization_angle"),
            trigger_summary=data.get("trigger_summary"),
            risk_flags=data.get("risk_flags") or [],
            evidence_items=evidence_items,
            confidence_score=confidence,
            recommended_action=recommended_action,
        )


def _summarize_response(response: dict[str, Any]) -> dict[str, Any]:
    output_text = response.get("output_text")
    if not isinstance(output_text, str):
        chunks: list[str] = []
        for item in response.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
        output_text = "\n".join(chunks)
    return {
        "id": response.get("id"),
        "status": response.get("status"),
        "output_preview": output_text[:500],
    }


def _usage_details(response: dict[str, Any]) -> dict[str, Any] | None:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return None
    return {
        "input": usage.get("input_tokens"),
        "output": usage.get("output_tokens"),
        "total": usage.get("total_tokens"),
    }


class DeterministicEnrichmentLLM:
    def __init__(self, min_confidence_to_draft: int = 65) -> None:
        self.min_confidence_to_draft = min_confidence_to_draft

    def enrich_company(
        self,
        *,
        enrichment_id: str,
        run_id: str | None,
        lead_id: str | None,
        company_name: str,
        company_website: str | None,
        company_domain: str | None,
        prospect_name: str | None,
        prospect_title: str | None,
        industry: str | None,
        country: str | None,
        manual_context: str | None,
        web_results: list[dict[str, Any]],
    ) -> EnrichmentResult:
        evidence_items: list[EvidenceItem] = []
        text_parts: list[str] = []

        if manual_context:
            evidence_items.append(
                EvidenceItem(
                    claim=f"Manual context available for {company_name}",
                    source_type=EvidenceSourceType.MANUAL_CONTEXT,
                    source_url=None,
                    quote_or_summary=manual_context[:200],
                    confidence=60,
                    used_in_message=True,
                )
            )
            text_parts.append(manual_context[:400])

        for result in web_results:
            if result.get("status") == "ok" and result.get("text"):
                url = result["url"]
                text = result["text"][:400]
                text_parts.append(text)

                source_type = EvidenceSourceType.WEBSITE
                lower_url = url.lower()
                if any(s in lower_url for s in ["/careers", "/jobs", "/work-with-us"]):
                    source_type = EvidenceSourceType.CAREERS
                elif any(s in lower_url for s in ["/blog", "/news", "/insights"]):
                    source_type = EvidenceSourceType.BLOG
                elif any(s in lower_url for s in ["/help", "/docs", "/support", "/knowledge-base"]):
                    source_type = EvidenceSourceType.HELP_CENTER

                evidence_items.append(
                    EvidenceItem(
                        claim=f"Content extracted from {url}",
                        source_type=source_type,
                        source_url=url,
                        quote_or_summary=text[:200],
                        confidence=50,
                        used_in_message=True,
                    )
                )

        if not evidence_items:
            return EnrichmentResult(
                enrichment_id=enrichment_id,
                run_id=run_id,
                lead_id=lead_id,
                company_name=company_name,
                company_website=company_website,
                prospect_name=prospect_name,
                prospect_title=prospect_title,
                enrichment_status=EnrichmentStatus.INSUFFICIENT_DATA,
                company_summary=f"No data available for {company_name}",
                b2b_fit=None,
                operational_pain_hypothesis=None,
                possible_ai_use_case=None,
                personalization_angle=None,
                trigger_summary=None,
                risk_flags=["insufficient_data"],
                evidence_items=[],
                confidence_score=0,
                recommended_action=RecommendedAction.NEEDS_MANUAL_RESEARCH,
            )

        confidence = min(50 + len(evidence_items) * 10, 80)
        total_text = " ".join(text_parts).lower()
        b2b_signals = [
            "b2b", "enterprise", "saas", "software", "platform",
            "servicios", "clientes", "empresas",
        ]
        b2b_fit = any(signal in total_text for signal in b2b_signals) or bool(company_website)

        company_summary = f"{' '.join(text_parts)[:500]}".strip()
        if not company_summary:
            company_summary = f"{company_name} has an online presence."

        recommended_action = (
            RecommendedAction.DRAFT
            if confidence >= self.min_confidence_to_draft and len(evidence_items) >= 2
            else RecommendedAction.NEEDS_MANUAL_RESEARCH
        )
        enrichment_status = (
            EnrichmentStatus.ENRICHED
            if recommended_action == RecommendedAction.DRAFT
            else EnrichmentStatus.NEEDS_REVIEW
        )

        return EnrichmentResult(
            enrichment_id=enrichment_id,
            run_id=run_id,
            lead_id=lead_id,
            company_name=company_name,
            company_website=company_website,
            prospect_name=prospect_name,
            prospect_title=prospect_title,
            enrichment_status=enrichment_status,
            company_summary=company_summary,
            b2b_fit=b2b_fit,
            operational_pain_hypothesis="Unable to determine from available data",
            possible_ai_use_case="Potential automation use case unclear from surface data",
            personalization_angle=f"Reference {company_name}'s online presence and operations",
            trigger_summary="No strong trigger detected in surface data",
            risk_flags=["surface_data_only"] if confidence < 70 else [],
            evidence_items=evidence_items,
            confidence_score=confidence,
            recommended_action=recommended_action,
        )

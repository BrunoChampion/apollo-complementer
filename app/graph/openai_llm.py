from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.langfuse import get_tracer
from app.domain.leads import LeadRow


class OpenAIDraftLLM:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def extract_manual_context(self, lead: LeadRow) -> str:
        context = {
            "company_name": lead.company_name,
            "company_website": lead.company_website,
            "prospect_name": lead.prospect_name,
            "prospect_title": lead.prospect_title,
            "country": lead.country,
            "industry": lead.industry,
            "manual_context": lead.manual_context,
            "manual_company_context": lead.manual_company_context,
            "manual_person_context": lead.manual_person_context,
            "manual_linkedin_notes": lead.manual_linkedin_notes,
            "manual_company_linkedin_text": lead.manual_company_linkedin_text,
            "manual_person_linkedin_text": lead.manual_person_linkedin_text,
            "identity_validation_status": lead.identity_validation_status,
            "icp_status": lead.icp_status,
            "icp_score_reason": lead.icp_score_reason,
            "source_url": lead.source_url,
        }
        return self._text_response(
            "Summarize the useful prospecting context in 1-3 factual sentences. "
            "Do not invent facts. If there is not enough context, say that clearly.",
            context,
        )

    def draft_email(
        self,
        *,
        lead: LeadRow,
        message_angle: str,
        evidence_items: list[dict[str, object]],
        max_words: int,
    ) -> tuple[str, str]:
        payload = {
            "lead": lead.model_dump(mode="json"),
            "message_angle": message_angle,
            "evidence_items": evidence_items,
            "max_words": max_words,
        }
        result = self._json_response(
            (
                "Write a cold outbound email draft for NYVEX. Return JSON with keys "
                "`subject` and `body`. The body must be in Spanish, concise, specific, "
                "low hype, and must not claim facts not present in the input. "
                "Use this structure: 1) open with one concrete operational signal from "
                "evidence_items, not a decorative fact. The opener must be company-first: "
                "after the greeting, the first sentence must start with 'Vi que [Empresa]...' "
                "or equivalent wording where the company is the subject. Do not open with "
                "the prospect's role, title, responsibilities, or wording like 'en tu rol "
                "de COO'; 2) frame the pain as a general "
                "B2B friction using wording like 'En empresas B2B con ese tipo de "
                "operación suele aparecer una fricción...', never as a diagnosis of "
                "the company; 3) add sober credibility: 'Desde NYVEX trabajé "
                "recientemente en un sistema de IA/RAG para una empresa B2B de HR "
                "software, enfocado justamente en convertir conocimiento disperso en "
                "flujos operativos reales.' without exaggerating results; 4) add a "
                "separate line: 'Creo que podría haber 2-3 ideas aplicables a "
                "[Empresa].'; 5) close with exactly this soft CTA: '¿Tiene sentido "
                "que te las comparta brevemente?' "
                "Do not ask for a 15-minute meeting in the first email. Do not use "
                "'podría estar atravesando', 'ya hemos logrado solucionar', or "
                "generic template language. Do not say NYVEX can solve everything. "
                "Do not auto-send language. "
                f"Keep body under {max_words} words."
            ),
            payload,
        )
        subject = str(result.get("subject") or f"Idea para {lead.company_name}")
        body = str(result.get("body") or "")
        return subject, body

    def revise_email(
        self,
        *,
        previous_draft: str,
        revision_instruction: str,
        max_words: int,
    ) -> str:
        result = self._json_response(
            (
                "Revise this cold email draft. Return JSON with key `body`. "
                "Preserve factual accuracy, keep it in Spanish, and do not add claims "
                f"not present in the draft or instruction. Keep it under {max_words} words."
            ),
            {
                "previous_draft": previous_draft,
                "revision_instruction": revision_instruction,
                "max_words": max_words,
            },
        )
        return _limit_words(str(result.get("body") or previous_draft), max_words)

    def validate_email_language(
        self,
        *,
        lead: LeadRow,
        subject: str,
        body: str,
        max_words: int,
    ) -> dict[str, object]:
        result = self._json_response(
            (
                "Validate this outbound email draft. Return JSON with keys "
                "`passes`, `issues`, and `reason`. The draft must be written in "
                "natural professional Spanish for a LATAM B2B buyer. It must not "
                "contain English prose, Spanglish, awkward English possessives like "
                "`Company's`, untranslated operational paragraphs, or a sentence cut "
                "off because of word limits. Allow proper nouns and common acronyms "
                "such as NYVEX, IA/RAG, API, CRM, B2B, HR, COO, SaaS and product names. "
                "The first concrete-signal sentence after the greeting must be company-first: "
                "it should use the company as the subject, not the prospect's title, role "
                "or responsibilities. Reject openers like 'Vi que en tu rol de COO...' "
                "or 'Vi que como COO...'. "
                f"The body must be under {max_words} words. If any issue is present, "
                "`passes` must be false and `issues` must list the concrete problems. "
                "Do not rewrite the draft in this validation step."
            ),
            {
                "lead": lead.model_dump(mode="json"),
                "subject": subject,
                "body": body,
                "max_words": max_words,
            },
        )
        return {
            "passes": bool(result.get("passes")),
            "issues": result.get("issues") if isinstance(result.get("issues"), list) else [],
            "reason": str(result.get("reason") or ""),
        }

    def _text_response(self, instructions: str, payload: dict[str, Any]) -> str:
        response = self._responses_create(instructions=instructions, payload=payload)
        return _extract_output_text(response).strip()

    def _json_response(self, instructions: str, payload: dict[str, Any]) -> dict[str, Any]:
        text = self._text_response(instructions, payload)
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

    def _responses_create(self, *, instructions: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self.model,
            "reasoning": {"effort": self.reasoning_effort},
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are NYVEX's sales research and email drafting assistant. "
                        "Be factual, specific, concise, and skeptical of weak evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": instructions
                    + "\n\nINPUT:\n"
                    + json.dumps(payload, ensure_ascii=False),
                },
            ],
        }
        tracer = get_tracer()
        with tracer.generation(
            "draft.openai.responses",
            model=self.model,
            input={
                "instruction_preview": instructions[:500],
                "payload_keys": sorted(payload.keys()),
                "company_name": (payload.get("lead") or {}).get("company_name")
                if isinstance(payload.get("lead"), dict)
                else None,
                "lead_id": (payload.get("lead") or {}).get("lead_id")
                if isinstance(payload.get("lead"), dict)
                else None,
            },
            metadata={
                "feature": "drafting",
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
            return data


def _extract_output_text(response: dict[str, Any]) -> str:
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


def _limit_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _summarize_response(response: dict[str, Any]) -> dict[str, Any]:
    text = _extract_output_text(response)
    return {
        "id": response.get("id"),
        "status": response.get("status"),
        "output_preview": text[:500],
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

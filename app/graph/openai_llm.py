from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.langfuse import get_tracer
from app.domain.leads import LeadRow

EMAIL_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["subject", "body"],
    "additionalProperties": False,
}

EMAIL_REVISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "body": {"type": "string"},
    },
    "required": ["body"],
    "additionalProperties": False,
}

EMAIL_VALIDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "passes": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["passes", "issues", "reason"],
    "additionalProperties": False,
}


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
        selected_signal: str | None,
        nyvex_relevance: str | None,
        why_now_trigger: str | None,
        solution_fit_type: str | None,
        nyvex_positioning: str | None,
        message_brief: dict[str, object] | None,
        max_words: int,
    ) -> tuple[str, str]:
        payload = {
            "lead": lead.model_dump(mode="json"),
            "message_angle": message_angle,
            "evidence_items": evidence_items,
            "message_brief": message_brief or {},
            "selected_operational_signal": selected_signal,
            "nyvex_relevance": nyvex_relevance,
            "why_now_trigger": why_now_trigger,
            "solution_fit_type": solution_fit_type,
            "nyvex_positioning": nyvex_positioning,
            "max_words": max_words,
        }
        result = self._json_response(
            (
                "Write a cold outbound email draft for NYVEX. Return JSON with keys "
                "`subject` and `body`. The body must be in Spanish, concise, specific, "
                "low hype, and must not claim facts not present in the input. "
                "Treat `message_brief` as the drafting contract. The opener must use "
                "`message_brief.selected_signal` as the concrete company fact. Do not "
                "turn that signal into a broader, prettier, or more abstract claim. "
                "Use only the evidence IDs listed in `message_brief.supporting_evidence_ids` "
                "for the first sentence. Other evidence can only help you avoid mistakes; "
                "it is not permission to add extra claims. "
                "Use Spanish by default. A small amount of natural LATAM corporate "
                "English is acceptable when it is the normal business term, but prefer "
                "clear Spanish when it sounds equally natural, e.g. 'software de RRHH' "
                "over 'HR software' and 'documentacion' over 'docs'. "
                "Use this structure: 1) open with `selected_operational_signal` as the "
                "main concrete operational signal. If selected_operational_signal is "
                "present, do not choose a different opener from evidence_items. The opener "
                "must be one natural sentence under 28 words. Mention one or two "
                "operational surfaces, not a long product catalog. If the evidence has "
                "many products or capabilities, group them into a broader operational "
                "surface instead of listing them one by one, while staying close to "
                "the wording supported by evidence_items. The opener "
                "must be durable and operational, not a credential, certification, metric, "
                "date, event, or news-style milestone. Prefer safe openers like '[Empresa] "
                "trabaja con bancos y cooperativas en canales digitales, onboarding y "
                "productos de IA para atencion al cliente' over precise claims like "
                "'acaba de obtener SOC 2 con 100% de cumplimiento'. The opener must be "
                "company-first: "
                "after the greeting, the first sentence must start with 'Vi que [Empresa]...' "
                "or equivalent wording where the company is the subject. Do not open with "
                "the prospect's role, title, responsibilities, or wording like 'en tu rol "
                "de COO'. The signal must be an operational company characteristic related "
                "to a plausible NYVEX exploration: support, onboarding, implementation, "
                "documentation, CRM/tickets, integrations, data workflows, customer success, "
                "internal processes, compliance operations, or knowledge management. Do not "
                "use hiring, funding, expansion, events, headcount, or generic growth as the "
                "main opener. You may use those only as secondary timing context if needed; "
                "if timing context has no clear date or may be stale, omit it from the draft. "
                "2) frame the pain as a general "
                "B2B friction using wording like 'En empresas B2B con ese tipo de "
                "operación suele aparecer una fricción...', and make sure 'ese tipo de "
                "operacion' clearly refers to the operational company characteristic in "
                "the opener, never as a diagnosis of "
                "the company. For the credibility line, use `nyvex_positioning` when "
                "provided. It may mention the previous IA/RAG project as proof of "
                "technical judgment, but it must not imply that the exact same RAG "
                "solution fits every prospect. If the fit is exploratory, say NYVEX "
                "would explore tailored hypotheses rather than sell a generic solution. "
                "Do not force the same IA/RAG credibility line when the prospect's "
                "signal points more naturally to agents, data workflows, integrations "
                "or a custom exploratory solution; use the provided positioning line "
                "as the source of truth. 3) Add that sober credibility line without "
                "exaggerating results. 4) add a "
                "separate line: 'Creo que podría haber 2-3 ideas aplicables a "
                "[Empresa].'; 5) close with exactly this soft CTA: '¿Tiene sentido "
                "que te las comparta brevemente?' "
                "Do not ask for a 15-minute meeting in the first email. Do not use "
                "'podría estar atravesando', 'ya hemos logrado solucionar', or "
                "generic template language. Do not say NYVEX can solve everything. "
                "Do not mention exact recency, percentages, certifications, compliance "
                "reports, funding amounts or customer counts unless they are explicitly "
                "needed and exactly supported by evidence_items; avoid using them as the "
                "first sentence. "
                "The pain line must imply a real system opportunity for NYVEX: data "
                "from live tools, rules, permissions, traceability, human review, "
                "integrations, repeatable workflows, or knowledge retrieval across "
                "documentation/tickets/CRM/product data. Do not frame a trivial task "
                "that a user could solve by pasting text into ChatGPT, such as merely "
                "summarizing notes or making a one-off checklist. "
                "Use controlled variety by `solution_fit_type`: for direct_rag_fit, "
                "focus on documentation, support, tickets, onboarding and knowledge "
                "retrieval; for data_ops_fit, focus on turning data, rules and "
                "exceptions into repeatable decisions; for agentic_workflow_fit, focus "
                "on handoffs, actions, routing and workflow execution; for "
                "exploratory_custom_solution, make it explicit that NYVEX would explore "
                "hypotheses instead of forcing a generic AI implementation. Do not use "
                "the exact same friction sentence for every prospect when a more precise "
                "fit-specific version is available. "
                "Do not auto-send language. "
                f"Keep body under {max_words} words."
            ),
            payload,
            schema_name="email_draft",
            schema=EMAIL_DRAFT_SCHEMA,
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
            schema_name="email_revision",
            schema=EMAIL_REVISION_SCHEMA,
        )
        return _limit_words(str(result.get("body") or previous_draft), max_words)

    def auto_repair_email(
        self,
        *,
        lead: LeadRow,
        subject: str,
        body: str,
        issues: list[str],
        evidence_items: list[dict[str, object]],
        selected_signal: str | None,
        message_angle: str | None,
        solution_fit_type: str | None,
        nyvex_positioning: str | None,
        message_brief: dict[str, object] | None,
        max_words: int,
    ) -> tuple[str, str]:
        result = self._json_response(
            (
                "Repair this NYVEX cold outbound email. Return JSON with keys "
                "`subject` and `body`. Fix only the listed issues. Do not add new "
                "claims, numbers, recency, customers, funding, certifications, or "
                "personal facts. Keep the email in natural professional Spanish. "
                "Treat `message_brief` as the repair contract. Keep the same "
                "`message_brief.selected_signal`; do not replace it with a broader "
                "or more abstract claim. If the opener is the issue, rewrite it as "
                "'Vi que [Empresa] [selected_signal].' with light grammatical cleanup. "
                "Preserve the soft CTA. The opener must be one company-first sentence "
                "using `selected_operational_signal`, grouped into one clear durable "
                "operational surface rather than a product catalog. Avoid role-first "
                "phrasing, hiring/funding/event openers, and excessive Spanglish. "
                "The pain line must imply a real system opportunity for NYVEX: data "
                "from live tools, rules, permissions, traceability, human review, "
                "integrations, repeatable workflows, or knowledge retrieval across "
                "documentation/tickets/CRM/product data. Do not frame a trivial task "
                "that a user could solve by pasting text into ChatGPT, such as merely "
                "summarizing notes or making a one-off checklist. Use controlled "
                "variety by `solution_fit_type` and make the friction line specific "
                "to the selected fit. Use `nyvex_positioning` as the credibility line "
                "when provided. "
                f"Keep body under {max_words} words."
            ),
            {
                "lead": lead.model_dump(mode="json"),
                "subject": subject,
                "body": body,
                "issues": issues,
                "evidence_items": evidence_items,
                "selected_operational_signal": selected_signal,
                "message_angle": message_angle,
                "solution_fit_type": solution_fit_type,
                "nyvex_positioning": nyvex_positioning,
                "message_brief": message_brief or {},
                "max_words": max_words,
            },
            schema_name="email_draft_repair",
            schema=EMAIL_DRAFT_SCHEMA,
        )
        repaired_subject = str(result.get("subject") or subject)
        repaired_body = _limit_words(str(result.get("body") or body), max_words)
        return repaired_subject, repaired_body

    def validate_email_language(
        self,
        *,
        lead: LeadRow,
        subject: str,
        body: str,
        evidence_items: list[dict[str, object]],
        message_angle: str | None,
        max_words: int,
    ) -> dict[str, object]:
        result = self._json_response(
            (
                "Validate this outbound email draft. Return JSON with keys "
                "`passes`, `issues`, and `reason`. The draft must be written in "
                "natural professional Spanish for a LATAM B2B buyer. It may contain "
                "a small amount of normal corporate English when it sounds natural in "
                "LATAM B2B, such as software, HR software, SaaS, CRM, API, tickets, "
                "onboarding, customer success, marketplace, enterprise, delivery, COO "
                "or product names. Prefer Spanish alternatives when they sound natural "
                "and precise, e.g. 'software de RRHH', 'documentacion', 'soporte', "
                "'implementacion' or 'flujos'. It must not contain English prose, "
                "awkward English possessives like `Company's`, untranslated operational "
                "paragraphs, or a sentence cut off because of word limits. Reject "
                "Spanglish overload: too many English business terms in one sentence, "
                "an English-heavy paragraph, or terms like 'docs' or 'on-the-job' when "
                "a natural Spanish equivalent is available. Allow proper nouns and "
                "common acronyms such as NYVEX, IA/RAG, API, CRM, B2B, HR, COO, SaaS "
                "and product names. "
                "The first concrete-signal sentence after the greeting must be company-first: "
                "it should use the company as the subject, not the prospect's title, role "
                "or responsibilities. Reject openers like 'Vi que en tu rol de COO...' "
                "or 'Vi que como COO...'. "
                "The opener should be one natural sentence under 28 words. Reject if it "
                "sounds like a product catalog, lists more than three separate capabilities, "
                "or has several comma-separated items instead of one clear operational "
                "surface. "
                "The opener must name an operational company characteristic that could "
                "reasonably connect to NYVEX's exploration of AI/software/RAG/agent "
                "implementations: support, onboarding, implementation, documentation, "
                "CRM, tickets, integrations, data workflows, customer success, internal "
                "processes, compliance operations or knowledge management. Reject if the "
                "main opener is only hiring, funding, expansion, headcount, an event, or "
                "generic growth. Those triggers may support timing, but they are not the "
                "operational signal. The phrase 'ese tipo de operacion' must have a clear "
                "antecedent in the opener. "
                "Reject if the opener is primarily a certification, compliance report, "
                "percentage, funding amount, customer count, recency claim or news-style "
                "milestone when a safer operational company characteristic is available. "
                "Prefer stable operational surfaces over precise claims that are easy to "
                "overstate. "
                "Reject if the NYVEX angle sounds like a trivial one-off ChatGPT task "
                "instead of a system that would justify technical implementation: live "
                "data/tool connections, rules, permissions, traceability, human review, "
                "integrations, repeatable workflows, or retrieval over company knowledge. "
                f"The body must be under {max_words} words. If any issue is present, "
                "`passes` must be false and `issues` must list the concrete problems. "
                "Do not rewrite the draft in this validation step."
            ),
            {
                "lead": lead.model_dump(mode="json"),
                "subject": subject,
                "body": body,
                "evidence_items": evidence_items,
                "message_angle": message_angle,
                "max_words": max_words,
            },
            schema_name="email_validation",
            schema=EMAIL_VALIDATION_SCHEMA,
        )
        return {
            "passes": bool(result.get("passes")),
            "issues": result.get("issues") if isinstance(result.get("issues"), list) else [],
            "reason": str(result.get("reason") or ""),
        }

    def _json_response(
        self,
        instructions: str,
        payload: dict[str, Any],
        *,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        text = self._text_response(
            instructions,
            payload,
            schema_name=schema_name,
            schema=schema,
        )
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

    def _text_response(
        self,
        instructions: str,
        payload: dict[str, Any],
        *,
        schema_name: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> str:
        response = self._responses_create(
            instructions=instructions,
            payload=payload,
            schema_name=schema_name,
            schema=schema,
        )
        return _extract_output_text(response).strip()

    def _responses_create(
        self,
        *,
        instructions: str,
        payload: dict[str, Any],
        schema_name: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
        if schema_name and schema:
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
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

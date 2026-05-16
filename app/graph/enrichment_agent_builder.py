from __future__ import annotations

import logging
from collections.abc import Callable
from time import perf_counter
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.core.config import Settings, get_settings
from app.core.langfuse import Tracer, get_tracer
from app.core.markets import country_market_status
from app.domain.enrichment import (
    EnrichmentResult,
    EnrichmentStatus,
    EvidenceItem,
    EvidenceSourceType,
    RecommendedAction,
)
from app.graph.enrichment_state import EnrichmentState
from app.graph.enrichment_tools import ENRICHMENT_TOOLS
from app.services.enrichment_scoring import score_enrichment_result
from app.services.enrichment_review import apply_review_decision
from app.services.github_org_service import github_search_org_data
from app.services.web_search_service import search_web_snippets
from app.services.website_stack_analyzer import analyze_website_stack_url

ToolFunction = Callable[..., dict[str, Any] | list[dict[str, Any]]]
logger = logging.getLogger(__name__)


class AgentEnrichmentOutput(EnrichmentResult):
    """Structured output schema returned by the LangChain enrichment agent."""


class DeterministicEnrichmentAgent:
    """Local deterministic agent runner with the same state contract as the tool agent."""

    def __init__(
        self,
        *,
        web_search_tool: Callable[[str, int], list[dict[str, Any]]] | None = None,
        stack_tool: Callable[[str], dict[str, Any]] | None = None,
        github_tool: Callable[[str, str | None], dict[str, Any]] | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self.web_search_tool = web_search_tool or search_web_snippets
        self.stack_tool = stack_tool or analyze_website_stack_url
        self.github_tool = github_tool or github_search_org_data
        self.tracer = tracer or get_tracer()

    def invoke(self, state: EnrichmentState) -> dict[str, Any]:
        settings = get_settings()
        lead = state.get("lead", {})
        company_name = str(lead.get("company_name") or "")
        website = lead.get("company_website")
        domain = lead.get("company_domain") or _domain_from_url(website)
        country = lead.get("country")
        max_iterations = max(1, settings.enrichment_max_iterations)

        history: list[dict[str, Any]] = []
        evidence_items: list[EvidenceItem] = []
        logger.info(
            "enrichment.agent.deterministic.start "
            "run_id=%s lead_id=%s company=%s country=%s max_iterations=%s",
            state.get("run_id"),
            state.get("lead_id") or lead.get("lead_id"),
            company_name,
            country,
            max_iterations,
        )

        if country_market_status(country) == "unsupported":
            logger.info(
                "enrichment.agent.deterministic.unsupported_country "
                "run_id=%s lead_id=%s country=%s",
                state.get("run_id"),
                state.get("lead_id") or lead.get("lead_id"),
                country,
            )
            result = _empty_result(
                state=state,
                status=EnrichmentStatus.NEEDS_REVIEW,
                action=RecommendedAction.DISCARD,
                risk_flags=["unsupported_country", "brazil_not_supported"],
            )
            return {
                "enrichment_result": result.model_dump(mode="json"),
                "evidence_items": [],
                "iteration_count": 0,
                "tool_calls_history": [],
                "status": "discard",
            }

        if company_name and len(history) < max_iterations:
            query = f"{company_name} {country or ''} empresa B2B".strip()
            search_results = self._call_tool(
                history,
                "web_search",
                {"query": query, "max_results": settings.duckduckgo_max_results},
                lambda: self.web_search_tool(query, settings.duckduckgo_max_results),
            )
            for item in search_results[:2]:
                snippet = item.get("snippet") or ""
                if snippet:
                    evidence_items.append(
                        EvidenceItem(
                            claim=f"Search result mentions {company_name}",
                            source_type=EvidenceSourceType.SEARCH_RESULT,
                            source_url=item.get("url"),
                            quote_or_summary=snippet[:300],
                            confidence=55,
                            used_in_message=True,
                        )
                    )

        if website and len(history) < max_iterations:
            stack_result = self._call_tool(
                history,
                "analyze_website_stack",
                {"url": website},
                lambda: self.stack_tool(str(website)),
            )
            technologies = stack_result.get("technologies") or []
            if technologies:
                technology_summary = ", ".join(technologies)
                evidence_items.append(
                    EvidenceItem(
                        claim=(
                            f"{company_name} website shows technology signals: "
                            f"{technology_summary}"
                        ),
                        source_type=EvidenceSourceType.WEBSITE,
                        source_url=str(website),
                        quote_or_summary=", ".join(stack_result.get("raw_signals") or technologies),
                        confidence=60,
                        used_in_message=True,
                    )
                )

        if domain and len(history) < max_iterations:
            github_result = self._call_tool(
                history,
                "github_search_org",
                {"company_domain": domain, "company_name": company_name},
                lambda: self.github_tool(str(domain), company_name),
            )
            if github_result.get("org_found"):
                evidence_items.append(
                    EvidenceItem(
                        claim=f"{company_name} has a public GitHub organization",
                        source_type=EvidenceSourceType.UNKNOWN,
                        source_url=f"https://github.com/{github_result.get('org_name')}",
                        quote_or_summary=(
                            f"Public repos: {github_result.get('public_repos')}; "
                            f"languages: {', '.join(github_result.get('top_languages') or [])}"
                        ),
                        confidence=50,
                        used_in_message=False,
                    )
                )

        result = _result_from_evidence(state, evidence_items)
        logger.info(
            "enrichment.agent.deterministic.done "
            "run_id=%s lead_id=%s tools=%s evidence_count=%s status=%s",
            state.get("run_id"),
            state.get("lead_id") or lead.get("lead_id"),
            len(history),
            len(evidence_items),
            "enriched" if evidence_items else "insufficient_data",
        )
        return {
            "enrichment_result": result.model_dump(mode="json"),
            "evidence_items": [item.model_dump(mode="json") for item in evidence_items],
            "iteration_count": len(history),
            "tool_calls_history": history,
            "agent_messages": [
                {"role": "assistant", "content": "deterministic enrichment complete"}
            ],
            "structured_response": result.model_dump(mode="json"),
            "status": "enriched" if evidence_items else "insufficient_data",
        }

    def _call_tool(
        self,
        history: list[dict[str, Any]],
        tool_name: str,
        tool_input: dict[str, Any],
        call: Callable[[], Any],
    ) -> Any:
        start = perf_counter()
        error = None
        logger.info(
            "enrichment.tool.start tool=%s iteration=%s",
            tool_name,
            len(history) + 1,
        )
        with self.tracer.span(f"enrichment.tool.{tool_name}", metadata={"input": tool_input}):
            try:
                output = call()
            except Exception as exc:
                output = [] if tool_name == "web_search" else {}
                error = str(exc)
                logger.info(
                    "enrichment.tool.error tool=%s iteration=%s error=%s",
                    tool_name,
                    len(history) + 1,
                    error,
                )
        duration_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "enrichment.tool.done tool=%s iteration=%s duration_ms=%s error=%s",
            tool_name,
            len(history) + 1,
            duration_ms,
            bool(error),
        )
        history.append(
            {
                "tool_name": tool_name,
                "input": tool_input,
                "output": output,
                "error": error,
                "duration_ms": duration_ms,
                "iteration": len(history) + 1,
            }
        )
        return output


class LangChainEnrichmentAgent:
    """Real LangChain create_agent runner with structured output."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str,
        base_url: str,
        create_agent_func: Callable[..., Any] | None = None,
        chat_model: Any | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url
        self.create_agent_func = create_agent_func
        self.chat_model = chat_model
        self._agent = None

    def invoke(self, state: EnrichmentState) -> dict[str, Any]:
        if country_market_status(state.get("lead", {}).get("country")) == "unsupported":
            logger.info(
                "enrichment.agent.langchain.unsupported_country run_id=%s lead_id=%s country=%s",
                state.get("run_id"),
                state.get("lead_id"),
                state.get("lead", {}).get("country"),
            )
            result = _empty_result(
                state=state,
                status=EnrichmentStatus.NEEDS_REVIEW,
                action=RecommendedAction.DISCARD,
                risk_flags=["unsupported_country", "brazil_not_supported"],
            )
            return {
                "enrichment_result": result.model_dump(mode="json"),
                "evidence_items": [],
                "iteration_count": 0,
                "tool_calls_history": [],
                "status": "discard",
            }

        agent = self._build_agent()
        lead = state.get("lead", {})
        settings = get_settings()
        tool_budget = max(1, settings.enrichment_max_tool_calls)
        recursion_limit = max(8, tool_budget * 2 + 4)
        logger.info(
            "enrichment.agent.langchain.start "
            "run_id=%s lead_id=%s company=%s model=%s max_tool_calls=%s",
            state.get("run_id"),
            state.get("lead_id") or lead.get("lead_id"),
            lead.get("company_name"),
            self.model,
            tool_budget,
        )
        response = agent.invoke(
            {
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": _lead_prompt(state)},
                ]
            },
            config={"recursion_limit": recursion_limit},
        )
        structured = _extract_structured_response(response)
        result = _agent_output_to_result(state, structured)
        messages = response.get("messages", []) if isinstance(response, dict) else []
        logger.info(
            "enrichment.agent.langchain.done "
            "run_id=%s lead_id=%s tool_calls=%s evidence_count=%s action=%s confidence=%s",
            state.get("run_id"),
            state.get("lead_id") or lead.get("lead_id"),
            _count_tool_messages(messages),
            len(result.evidence_items or []),
            result.recommended_action.value,
            result.confidence_score,
        )
        return {
            "enrichment_result": result.model_dump(mode="json"),
            "evidence_items": [
                item.model_dump(mode="json") for item in (result.evidence_items or [])
            ],
            "iteration_count": _count_tool_messages(messages),
            "tool_calls_history": _extract_tool_history(messages),
            "agent_messages": [_message_to_dict(message) for message in messages],
            "structured_response": structured.model_dump(mode="json"),
            "status": "enriched" if result.evidence_items else "insufficient_data",
        }

    def _build_agent(self) -> Any:
        if self._agent is not None:
            return self._agent
        create_agent_func = self.create_agent_func or _import_create_agent()
        model = self.chat_model or _build_chat_model(
            api_key=self.api_key,
            model=self.model,
            reasoning_effort=self.reasoning_effort,
            base_url=self.base_url,
        )
        self._agent = create_agent_func(
            model=model,
            tools=ENRICHMENT_TOOLS,
            response_format=AgentEnrichmentOutput,
            system_prompt=_system_prompt(),
        )
        return self._agent


def build_enrichment_agent(settings: Settings | None = None):
    settings = settings or get_settings()
    if (
        settings.enrichment_provider.lower() == "openai"
        and _is_real_secret(settings.openai_api_key)
    ):
        try:
            _import_create_agent()
            _build_chat_model(
                api_key=settings.openai_api_key,
                model=settings.enrichment_model,
                reasoning_effort=settings.enrichment_reasoning_effort,
                base_url=settings.openai_base_url,
            )
        except Exception as exc:
            logger.info(
                "enrichment.agent.provider=fallback_deterministic "
                "reason=langchain_unavailable error=%s",
                exc,
            )
            return DeterministicEnrichmentAgent()
        logger.info(
            "enrichment.agent.provider=langchain model=%s reasoning_effort=%s",
            settings.enrichment_model,
            settings.enrichment_reasoning_effort,
        )
        return LangChainEnrichmentAgent(
            api_key=settings.openai_api_key,
            model=settings.enrichment_model,
            reasoning_effort=settings.enrichment_reasoning_effort,
            base_url=settings.openai_base_url,
        )
    logger.info("enrichment.agent.provider=deterministic")
    return DeterministicEnrichmentAgent()


def build_enrichment_agent_graph(
    agent: Any | None = None,
    checkpointer: InMemorySaver | None = None,
):
    agent = agent or build_enrichment_agent()
    checkpointer = checkpointer or InMemorySaver()

    graph = StateGraph(EnrichmentState)
    graph.add_node("validate_input", _validate_input)
    graph.add_node("run_enrichment_agent", agent.invoke)
    graph.add_node("validate_and_score", _validate_and_score)
    graph.add_node("write_result", _write_result)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges(
        "validate_input",
        lambda state: "write_result" if state.get("status") == "error" else "run_enrichment_agent",
        {
            "run_enrichment_agent": "run_enrichment_agent",
            "write_result": "write_result",
        },
    )
    graph.add_edge("run_enrichment_agent", "validate_and_score")
    graph.add_edge("validate_and_score", "write_result")
    graph.add_edge("write_result", END)
    return graph.compile(checkpointer=checkpointer)


def _system_prompt() -> str:
    return (
        "You are NYVEX's enrichment researcher for Spanish-speaking high-ticket B2B "
        "markets. Use tools to gather factual evidence. Read search snippets only; do "
        "not scrape LinkedIn, Indeed, Computrabajo, GetOnBoard, or job boards directly. "
        "Treat the pasted person LinkedIn content and pasted company LinkedIn content "
        "as mandatory identity context, not as permission to invent. Never assume that "
        "a web result refers to the same person or company just because the name is "
        "similar; mark uncertainty or conflict instead. "
        "Brazil and non-Spanish-speaking markets are out of scope. Stop once you have "
        "enough evidence. Use at most 6 tool calls total. Prefer one broad web search, "
        "one official website/stack analysis, and one targeted follow-up search only "
        "when needed. Do not paginate search results. Do not invent facts. Return "
        "structured output only."
    )


def _lead_prompt(state: EnrichmentState) -> str:
    lead = state.get("lead", {})
    return (
        "Research this lead for outbound personalization.\n"
        f"run_id: {state.get('run_id')}\n"
        f"lead_id: {state.get('lead_id')}\n"
        f"company_name: {lead.get('company_name')}\n"
        f"company_website: {lead.get('company_website')}\n"
        f"company_domain: {lead.get('company_domain')}\n"
        f"country: {lead.get('country')}\n"
        f"prospect_name: {lead.get('prospect_name')}\n"
        f"prospect_title: {lead.get('prospect_title')}\n"
        f"company_size: {lead.get('company_size')}\n"
        f"manual_context: {lead.get('manual_context')}\n"
        f"manual_company_context: {lead.get('manual_company_context')}\n"
        f"manual_person_context: {lead.get('manual_person_context')}\n"
        f"manual_linkedin_notes: {lead.get('manual_linkedin_notes')}\n"
        f"manual_company_linkedin_text: {lead.get('manual_company_linkedin_text')}\n"
        f"manual_person_linkedin_text: {lead.get('manual_person_linkedin_text')}\n"
    )


def _import_create_agent() -> Callable[..., Any]:
    from langchain.agents import create_agent

    return create_agent


def _build_chat_model(
    *,
    api_key: str,
    model: str,
    reasoning_effort: str,
    base_url: str,
) -> Any:
    from langchain_openai import ChatOpenAI

    model_kwargs: dict[str, Any] = {}
    explicit_kwargs: dict[str, Any] = {}
    if reasoning_effort:
        explicit_kwargs["reasoning"] = {"effort": reasoning_effort}
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        base_url=base_url,
        model_kwargs=model_kwargs,
        **explicit_kwargs,
    )


def _is_real_secret(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    return not (
        normalized.startswith("replace-with")
        or normalized.startswith("generate-")
        or normalized in {"changeme", "change-me", "todo", "none", "null"}
    )


def _extract_structured_response(response: Any) -> AgentEnrichmentOutput:
    if isinstance(response, dict):
        structured = response.get("structured_response")
        if isinstance(structured, AgentEnrichmentOutput):
            return structured
        if isinstance(structured, EnrichmentResult):
            return AgentEnrichmentOutput.model_validate(structured.model_dump(mode="json"))
        if isinstance(structured, dict):
            return AgentEnrichmentOutput.model_validate(structured)
    raise ValueError("LangChain agent did not return structured_response.")


def _agent_output_to_result(
    state: EnrichmentState,
    output: AgentEnrichmentOutput,
) -> EnrichmentResult:
    data = output.model_dump(mode="json")
    lead = state.get("lead", {})
    data["enrichment_id"] = (
        data.get("enrichment_id")
        or state.get("enrichment_id")
        or f"enr-{lead.get('lead_id', state.get('lead_id', 'unknown'))}"
    )
    data["run_id"] = data.get("run_id") or state.get("run_id")
    data["lead_id"] = data.get("lead_id") or state.get("lead_id") or lead.get("lead_id")
    data["company_name"] = data.get("company_name") or lead.get("company_name")
    data["company_website"] = data.get("company_website") or lead.get("company_website")
    data["company_domain"] = data.get("company_domain") or lead.get("company_domain")
    data["company_linkedin_url"] = data.get("company_linkedin_url") or lead.get(
        "company_linkedin_url"
    )
    data["prospect_name"] = data.get("prospect_name") or lead.get("prospect_name")
    data["prospect_title"] = data.get("prospect_title") or lead.get("prospect_title")
    data["prospect_linkedin_url"] = data.get("prospect_linkedin_url") or lead.get(
        "prospect_linkedin_url"
    )
    data["country"] = data.get("country") or lead.get("country")
    data["industry"] = data.get("industry") or lead.get("industry")
    data["company_size"] = data.get("company_size") or lead.get("company_size")
    return EnrichmentResult.model_validate(data)


def _count_tool_messages(messages: list[Any]) -> int:
    return sum(1 for message in messages if _message_to_dict(message).get("type") == "tool")


def _extract_tool_history(messages: list[Any]) -> list[dict[str, Any]]:
    history = []
    for message in messages:
        data = _message_to_dict(message)
        if data.get("type") == "tool":
            history.append(
                {
                    "tool_name": data.get("name") or data.get("tool_call_id") or "tool",
                    "input": data.get("input") or {},
                    "output": data.get("content"),
                    "error": None,
                    "duration_ms": None,
                    "iteration": len(history) + 1,
                }
            )
    return history


def _message_to_dict(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        return message
    if hasattr(message, "model_dump"):
        return message.model_dump()
    return {
        "type": getattr(message, "type", None),
        "content": getattr(message, "content", None),
        "name": getattr(message, "name", None),
        "tool_call_id": getattr(message, "tool_call_id", None),
    }


def _validate_input(state: EnrichmentState) -> dict[str, Any]:
    lead = state.get("lead", {})
    if not lead.get("company_name"):
        logger.info(
            "enrichment.graph.validate_input.error "
            "run_id=%s lead_id=%s reason=missing_company_name",
            state.get("run_id"),
            state.get("lead_id") or lead.get("lead_id"),
        )
        return {"status": "error", "error_message": "company_name is required"}
    logger.info(
        "enrichment.graph.validate_input.done run_id=%s lead_id=%s company=%s",
        state.get("run_id"),
        state.get("lead_id") or lead.get("lead_id"),
        lead.get("company_name"),
    )
    return {
        "status": "validated",
        "enrichment_id": state.get("enrichment_id")
        or f"enr-{lead.get('lead_id', state.get('lead_id', 'unknown'))}",
    }


def _validate_and_score(state: EnrichmentState) -> dict[str, Any]:
    if state.get("status") == "error":
        return {}
    try:
        result = EnrichmentResult.model_validate(state.get("enrichment_result", {}))
    except Exception as exc:
        result = _empty_result(
            state=state,
            status=EnrichmentStatus.INSUFFICIENT_DATA,
            action=RecommendedAction.NEEDS_MANUAL_RESEARCH,
            risk_flags=["invalid_agent_output"],
            error_message=str(exc),
        )

    if country_market_status(state.get("lead", {}).get("country")) == "unsupported":
        result.recommended_action = RecommendedAction.DISCARD
        result.risk_flags = (result.risk_flags or []) + ["unsupported_country"]

    if not result.evidence_items:
        result.enrichment_status = EnrichmentStatus.INSUFFICIENT_DATA
        result.recommended_action = RecommendedAction.NEEDS_MANUAL_RESEARCH
        result.risk_flags = (result.risk_flags or []) + ["insufficient_data"]

    score = score_enrichment_result(result, lead_data=state.get("lead", {}))
    result.confidence_score = score.confidence_score
    result.recommended_action = score.recommended_action
    result.risk_flags = (result.risk_flags or []) + [f"score: {score.score}"] + score.score_reasons

    if country_market_status(state.get("lead", {}).get("country")) == "unsupported":
        result.recommended_action = RecommendedAction.DISCARD

    result = apply_review_decision(result)

    logger.info(
        "enrichment.graph.validate_and_score.done "
        "run_id=%s lead_id=%s status=%s action=%s confidence=%s evidence_count=%s",
        state.get("run_id"),
        state.get("lead_id") or state.get("lead", {}).get("lead_id"),
        result.enrichment_status.value,
        result.recommended_action.value,
        result.confidence_score,
        len(result.evidence_items or []),
    )
    return {
        "enrichment_result": result.model_dump(mode="json"),
        "evidence_items": [item.model_dump(mode="json") for item in (result.evidence_items or [])],
        "status": "scored",
    }


def _write_result(state: EnrichmentState) -> dict[str, Any]:
    if state.get("status") == "error":
        logger.info(
            "enrichment.graph.write_result.error run_id=%s lead_id=%s error=%s",
            state.get("run_id"),
            state.get("lead_id") or state.get("lead", {}).get("lead_id"),
            state.get("error_message"),
        )
        return {"agent_note": "Enrichment failed."}
    result = state.get("enrichment_result", {})
    logger.info(
        "enrichment.graph.write_result.done run_id=%s lead_id=%s status=%s action=%s confidence=%s",
        state.get("run_id"),
        state.get("lead_id") or state.get("lead", {}).get("lead_id"),
        result.get("enrichment_status", "unknown"),
        result.get("recommended_action", "unknown"),
        result.get("confidence_score", "N/A"),
    )
    return {
        "agent_note": (
            "Enrichment complete. "
            f"Status: {result.get('enrichment_status', 'unknown')}, "
            f"confidence: {result.get('confidence_score', 'N/A')}, "
            f"recommended_action: {result.get('recommended_action', 'unknown')}."
        )
    }


def _result_from_evidence(
    state: EnrichmentState, evidence_items: list[EvidenceItem]
) -> EnrichmentResult:
    lead = state.get("lead", {})
    if not evidence_items:
        return _empty_result(
            state=state,
            status=EnrichmentStatus.INSUFFICIENT_DATA,
            action=RecommendedAction.NEEDS_MANUAL_RESEARCH,
            risk_flags=["insufficient_data"],
        )
    company_name = lead.get("company_name")
    technologies = [
        item.claim for item in evidence_items if "technology signals" in item.claim.lower()
    ]
    return EnrichmentResult(
        enrichment_id=state.get("enrichment_id")
        or f"enr-{lead.get('lead_id', state.get('lead_id', 'unknown'))}",
        run_id=state.get("run_id"),
        lead_id=state.get("lead_id") or lead.get("lead_id"),
        company_name=company_name,
        company_website=lead.get("company_website"),
        company_domain=lead.get("company_domain"),
        company_linkedin_url=lead.get("company_linkedin_url"),
        prospect_name=lead.get("prospect_name"),
        prospect_title=lead.get("prospect_title"),
        prospect_linkedin_url=lead.get("prospect_linkedin_url"),
        country=lead.get("country"),
        industry=lead.get("industry"),
        company_size=lead.get("company_size"),
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_summary=f"{company_name} has public signals available for outbound research.",
        b2b_fit=True if country_market_status(lead.get("country")) == "supported" else None,
        operational_pain_hypothesis=(
            "Potential operational scaling or revenue operations process gaps."
        ),
        possible_ai_use_case="AI-assisted research, routing, and outbound draft preparation.",
        personalization_angle=technologies[0]
        if technologies
        else f"Reference public signals about {company_name}.",
        trigger_summary="Recent public web/search signals found.",
        risk_flags=["surface_data_only"],
        evidence_items=evidence_items,
        confidence_score=min(50 + len(evidence_items) * 10, 80),
        recommended_action=RecommendedAction.NEEDS_MANUAL_RESEARCH,
    )


def _empty_result(
    *,
    state: EnrichmentState,
    status: EnrichmentStatus,
    action: RecommendedAction,
    risk_flags: list[str],
    error_message: str | None = None,
) -> EnrichmentResult:
    lead = state.get("lead", {})
    return EnrichmentResult(
        enrichment_id=state.get("enrichment_id")
        or f"enr-{lead.get('lead_id', state.get('lead_id', 'unknown'))}",
        run_id=state.get("run_id"),
        lead_id=state.get("lead_id") or lead.get("lead_id"),
        company_name=lead.get("company_name"),
        company_website=lead.get("company_website"),
        company_domain=lead.get("company_domain"),
        company_linkedin_url=lead.get("company_linkedin_url"),
        prospect_name=lead.get("prospect_name"),
        prospect_title=lead.get("prospect_title"),
        prospect_linkedin_url=lead.get("prospect_linkedin_url"),
        country=lead.get("country"),
        industry=lead.get("industry"),
        company_size=lead.get("company_size"),
        enrichment_status=status,
        risk_flags=risk_flags,
        evidence_items=[],
        confidence_score=0,
        recommended_action=action,
        error_message=error_message,
    )


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    value = str(url).replace("https://", "").replace("http://", "").split("/")[0]
    return value.removeprefix("www.") or None

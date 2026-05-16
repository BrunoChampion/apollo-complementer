from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction
from app.services.enrichment_scoring import score_enrichment_result
from app.services.enrichment_review import apply_review_decision
from app.services.web_fetcher import fetch_company_pages

from .enrichment_llm import EnrichmentLLM
from .enrichment_state import EnrichmentState


def validate_enrichment_input(state: EnrichmentState) -> dict[str, object]:
    lead = state.get("lead", {})
    if not lead.get("company_name"):
        return {"status": "error", "error_message": "company_name is required"}
    return {
        "status": "validated",
        "enrichment_id": state.get("enrichment_id")
        or f"enr-{lead.get('lead_id', 'unknown')}",
    }


def fetch_web_data_node(state: EnrichmentState) -> dict[str, object]:
    if state.get("status") == "error":
        return {}
    lead = state.get("lead", {})
    website = lead.get("company_website")
    domain = lead.get("company_domain")
    if not website and not domain:
        return {"web_results": [], "status": "web_fetched"}
    results = fetch_company_pages(
        website=website,
        company_domain=domain or website,
    )
    return {"web_results": results, "status": "web_fetched"}


def enrich_company_node(llm: EnrichmentLLM) -> callable:
    def node(state: EnrichmentState) -> dict[str, object]:
        if state.get("status") == "error":
            return {}
        lead = state.get("lead", {})
        enrichment_id = state.get("enrichment_id", "unknown")

        result = llm.enrich_company(
            enrichment_id=enrichment_id,
            run_id=state.get("run_id"),
            lead_id=lead.get("lead_id"),
            company_name=lead.get("company_name", ""),
            company_website=lead.get("company_website"),
            company_domain=lead.get("company_domain") or lead.get("company_website"),
            prospect_name=lead.get("prospect_name"),
            prospect_title=lead.get("prospect_title"),
            industry=lead.get("industry"),
            country=lead.get("country"),
            manual_context=lead.get("manual_context"),
            web_results=state.get("web_results", []),
        )

        return {
            "enrichment_result": result.model_dump(mode="json"),
            "evidence_items": [
                item.model_dump(mode="json")
                for item in (result.evidence_items or [])
            ],
            "status": "enriched",
        }

    return node


def validate_enrichment_output(state: EnrichmentState) -> dict[str, object]:
    if state.get("status") == "error":
        return {}
    result_dict = state.get("enrichment_result", {})
    try:
        result = EnrichmentResult.model_validate(result_dict)
    except Exception as exc:
        return {
            "status": "error",
            "error_message": f"Invalid enrichment result: {exc}",
        }

    if not result.evidence_items or len(result.evidence_items) == 0:
        result.enrichment_status = EnrichmentStatus.INSUFFICIENT_DATA
        result.recommended_action = RecommendedAction.NEEDS_MANUAL_RESEARCH
        result.risk_flags = (result.risk_flags or []) + ["insufficient_data"]
        return {
            "enrichment_result": result.model_dump(mode="json"),
            "status": "insufficient_data",
        }

    return {
        "enrichment_result": result.model_dump(mode="json"),
        "status": "validated_output",
    }


def score_enrichment_node(state: EnrichmentState) -> dict[str, object]:
    if state.get("status") == "error":
        return {}
    result_dict = state.get("enrichment_result", {})
    try:
        result = EnrichmentResult.model_validate(result_dict)
    except Exception:
        return {}

    score = score_enrichment_result(result, lead_data=state.get("lead", {}))
    result.confidence_score = score.confidence_score
    result.recommended_action = score.recommended_action
    # Store score reasons in risk_flags for traceability
    existing_flags = result.risk_flags or []
    result.risk_flags = existing_flags + [f"score: {score.score}"] + score.score_reasons
    result = apply_review_decision(result)

    return {
        "enrichment_result": result.model_dump(mode="json"),
        "status": "scored",
    }


def write_enrichment_result(state: EnrichmentState) -> dict[str, object]:
    if state.get("status") == "error":
        return {"agent_note": "Enrichment failed."}
    result_dict = state.get("enrichment_result", {})
    status = result_dict.get("enrichment_status", "unknown")
    confidence = result_dict.get("confidence_score", "N/A")
    action = result_dict.get("recommended_action", "unknown")
    return {
        "agent_note": (
            f"Enrichment complete. Status: {status}, confidence: {confidence}, "
            f"recommended_action: {action}."
        )
    }

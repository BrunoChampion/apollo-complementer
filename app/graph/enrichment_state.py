from typing import Any, NotRequired, TypedDict


class EnrichmentState(TypedDict):
    run_id: str
    lead_id: str
    lead: dict[str, Any]
    enrichment_id: NotRequired[str]
    web_results: NotRequired[list[dict[str, Any]]]
    enrichment_result: NotRequired[dict[str, Any]]
    evidence_items: NotRequired[list[dict[str, Any]]]
    iteration_count: NotRequired[int]
    tool_calls_history: NotRequired[list[dict[str, Any]]]
    agent_messages: NotRequired[list[dict[str, Any]]]
    structured_response: NotRequired[dict[str, Any]]
    status: NotRequired[str]
    error_message: NotRequired[str]
    agent_note: NotRequired[str]

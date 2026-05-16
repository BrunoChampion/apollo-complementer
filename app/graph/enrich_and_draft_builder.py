from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.draft_guardrails import (
    language_validator,
    route_after_guardrail,
    tone_checker,
    verify_claims_against_evidence,
)
from app.graph.enrich_and_draft_nodes import (
    gate_draft_on_enrichment,
    inject_enrichment_context,
    write_enrich_and_draft_result,
)
from app.graph.nodes import (
    DeterministicDraftLLM,
    DraftLLM,
    draft_message_node,
    evaluate_draft,
    load_playbook_node,
    select_message_angle,
)
from app.graph.routing import route_after_evaluation
from app.graph.state import LeadState


def _route_after_gate(state: LeadState) -> str:
    if state.get("status") in {"error", "insufficient_data", "needs_manual_research"}:
        return "write_result"
    return "load_playbook"


def build_enrich_and_draft_graph(
    llm: DraftLLM | None = None,
    checkpointer: InMemorySaver | None = None,
):
    llm = llm or DeterministicDraftLLM()
    checkpointer = checkpointer or InMemorySaver()

    graph = StateGraph(LeadState)
    graph.add_node("gate_draft", gate_draft_on_enrichment)
    graph.add_node("load_playbook", load_playbook_node)
    graph.add_node("inject_context", inject_enrichment_context)
    graph.add_node("select_message_angle", select_message_angle)
    graph.add_node("draft_message", draft_message_node(llm))
    graph.add_node("verify_claims", verify_claims_against_evidence)
    graph.add_node("language_validator", language_validator)
    graph.add_node("tone_checker", tone_checker)
    graph.add_node("evaluate_draft", evaluate_draft)
    graph.add_node("write_result", write_enrich_and_draft_result)

    graph.add_edge(START, "gate_draft")
    graph.add_conditional_edges(
        "gate_draft",
        _route_after_gate,
        {
            "load_playbook": "load_playbook",
            "write_result": "write_result",
        },
    )
    graph.add_edge("load_playbook", "inject_context")
    graph.add_edge("inject_context", "select_message_angle")
    graph.add_edge("select_message_angle", "draft_message")
    graph.add_edge("draft_message", "verify_claims")
    graph.add_conditional_edges(
        "verify_claims",
        route_after_guardrail,
        {
            "next": "language_validator",
            "write_result": "write_result",
        },
    )
    graph.add_conditional_edges(
        "language_validator",
        route_after_guardrail,
        {
            "next": "tone_checker",
            "write_result": "write_result",
        },
    )
    graph.add_conditional_edges(
        "tone_checker",
        route_after_guardrail,
        {
            "next": "evaluate_draft",
            "write_result": "write_result",
        },
    )
    graph.add_conditional_edges(
        "evaluate_draft",
        route_after_evaluation,
        {
            "write_graph_result": "write_result",
            "write_revision_result": "write_result",
        },
    )
    graph.add_edge("write_result", END)

    return graph.compile(checkpointer=checkpointer)

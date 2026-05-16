from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.draft_guardrails import (
    language_validator,
    route_after_guardrail,
    tone_checker,
    verify_claims_against_evidence,
)
from app.graph.nodes import DeterministicDraftLLM, DraftLLM, evaluate_draft, load_playbook_node
from app.graph.state import LeadState
from app.services.revision_hash import hash_revision_instruction


def revise_enriched_draft_node(llm: DraftLLM):
    def node(state: LeadState) -> dict[str, object]:
        if state.get("status") == "error":
            return {}
        previous_draft = state.get("previous_draft") or state.get("email_draft")
        instruction = state.get("revision_instruction")
        if not previous_draft:
            return {"status": "error", "error_message": "previous draft is required"}
        if not instruction:
            return {"status": "error", "error_message": "revision_instruction is required"}

        revision_hash = hash_revision_instruction(instruction)
        if revision_hash == state.get("last_processed_revision_hash"):
            return {
                "status": "revised",
                "revised_draft": previous_draft,
                "revision_instruction_hash": revision_hash,
                "agent_note": "Revision instruction already processed.",
            }

        max_words = int(state["playbook"]["message_rules"]["max_words_email"])
        revised = llm.revise_email(
            previous_draft=previous_draft,
            revision_instruction=instruction,
            max_words=max_words,
        )
        return {
            "email_draft": revised,
            "revised_draft": revised,
            "revision_instruction_hash": revision_hash,
            "last_processed_revision_hash": revision_hash,
            "revision_count": int(state.get("revision_count", 0)) + 1,
            "status": "revised",
        }

    return node


def write_revise_result(state: LeadState) -> dict[str, object]:
    if state.get("status") == "error":
        return {"agent_note": "Enriched revision failed."}
    if state.get("agent_note") == "Revision instruction already processed.":
        return {}
    if state.get("status") == "needs_revision":
        return {"agent_note": state.get("agent_note", "Revised draft needs revision.")}
    return {
        "agent_note": (
            f"Enriched revision applied. Revision count is {state.get('revision_count')}; "
            f"quality score is {state.get('quality_score')}."
        )
    }


def _route_after_revise(state: LeadState) -> str:
    if state.get("status") == "error":
        return "write_result"
    if state.get("agent_note") == "Revision instruction already processed.":
        return "write_result"
    return "verify_claims"


def build_revise_enriched_draft_graph(
    llm: DraftLLM | None = None,
    checkpointer: InMemorySaver | None = None,
):
    llm = llm or DeterministicDraftLLM()
    checkpointer = checkpointer or InMemorySaver()

    graph = StateGraph(LeadState)
    graph.add_node("load_playbook", load_playbook_node)
    graph.add_node("revise_draft", revise_enriched_draft_node(llm))
    graph.add_node("verify_claims", verify_claims_against_evidence)
    graph.add_node("language_validator", language_validator)
    graph.add_node("tone_checker", tone_checker)
    graph.add_node("evaluate_draft", evaluate_draft)
    graph.add_node("write_result", write_revise_result)

    graph.add_edge(START, "load_playbook")
    graph.add_edge("load_playbook", "revise_draft")
    graph.add_conditional_edges(
        "revise_draft",
        _route_after_revise,
        {
            "verify_claims": "verify_claims",
            "write_result": "write_result",
        },
    )
    graph.add_conditional_edges(
        "verify_claims",
        route_after_guardrail,
        {"next": "language_validator", "write_result": "write_result"},
    )
    graph.add_conditional_edges(
        "language_validator",
        route_after_guardrail,
        {"next": "tone_checker", "write_result": "write_result"},
    )
    graph.add_conditional_edges(
        "tone_checker",
        route_after_guardrail,
        {"next": "evaluate_draft", "write_result": "write_result"},
    )
    graph.add_edge("evaluate_draft", "write_result")
    graph.add_edge("write_result", END)
    return graph.compile(checkpointer=checkpointer)

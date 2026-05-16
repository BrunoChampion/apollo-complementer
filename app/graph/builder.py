from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    DeterministicDraftLLM,
    DraftLLM,
    draft_message_node,
    evaluate_draft,
    extract_manual_context_node,
    load_playbook_node,
    revise_message_node,
    score_fit,
    select_message_angle,
    validate_input,
    write_graph_result,
    write_revision_result,
)
from app.graph.routing import (
    route_after_evaluation,
    route_after_playbook,
    route_after_revision,
    should_continue_after_validation,
)
from app.graph.state import LeadState


def build_research_and_draft_graph(
    llm: DraftLLM | None = None,
    checkpointer: InMemorySaver | None = None,
):
    llm = llm or DeterministicDraftLLM()
    checkpointer = checkpointer or InMemorySaver()

    graph = StateGraph(LeadState)
    graph.add_node("validate_input", validate_input)
    graph.add_node("load_playbook", load_playbook_node)
    graph.add_node("extract_manual_context", extract_manual_context_node(llm))
    graph.add_node("score_fit", score_fit)
    graph.add_node("select_message_angle", select_message_angle)
    graph.add_node("draft_message", draft_message_node(llm))
    graph.add_node("revise_message", revise_message_node(llm))
    graph.add_node("evaluate_draft", evaluate_draft)
    graph.add_node("write_graph_result", write_graph_result)
    graph.add_node("write_revision_result", write_revision_result)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges(
        "validate_input",
        should_continue_after_validation,
        {
            "load_playbook": "load_playbook",
            "write_graph_result": "write_graph_result",
        },
    )
    graph.add_conditional_edges(
        "load_playbook",
        route_after_playbook,
        {
            "extract_manual_context": "extract_manual_context",
            "revise_message": "revise_message",
        },
    )
    graph.add_edge("extract_manual_context", "score_fit")
    graph.add_edge("score_fit", "select_message_angle")
    graph.add_edge("select_message_angle", "draft_message")
    graph.add_edge("draft_message", "evaluate_draft")
    graph.add_conditional_edges(
        "revise_message",
        route_after_revision,
        {
            "evaluate_draft": "evaluate_draft",
            "write_revision_result": "write_revision_result",
        },
    )
    graph.add_conditional_edges(
        "evaluate_draft",
        route_after_evaluation,
        {
            "write_graph_result": "write_graph_result",
            "write_revision_result": "write_revision_result",
        },
    )
    graph.add_edge("write_graph_result", END)
    graph.add_edge("write_revision_result", END)

    return graph.compile(checkpointer=checkpointer)

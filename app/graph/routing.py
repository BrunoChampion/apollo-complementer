from .state import LeadState


def should_continue_after_validation(state: LeadState) -> str:
    if state.get("status") == "error":
        return "write_graph_result"
    return "load_playbook"


def route_after_playbook(state: LeadState) -> str:
    if state.get("action") == "revise":
        return "revise_message"
    return "extract_manual_context"


def route_after_evaluation(state: LeadState) -> str:
    if state.get("action") == "revise":
        return "write_revision_result"
    return "write_graph_result"


def route_after_revision(state: LeadState) -> str:
    if state.get("agent_note") == "Revision instruction already processed.":
        return "write_revision_result"
    return "evaluate_draft"

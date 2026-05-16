from langgraph.checkpoint.memory import InMemorySaver

from app.graph.builder import build_research_and_draft_graph


def test_graph_persists_checkpoint_by_thread_id() -> None:
    checkpointer = InMemorySaver()
    graph = build_research_and_draft_graph(checkpointer=checkpointer)
    thread_id = "run_123:lead_123"
    state = {
        "run_id": "run_123",
        "lead_id": "lead_123",
        "action": "research_and_draft",
        "lead": {
            "lead_id": "lead_123",
            "company_name": "Nova Cyber Advisors",
            "company_website": "https://novacyber.example.com",
            "prospect_name": "Martin Silva",
            "prospect_title": "Sales Director",
            "prospect_email": "martin@novacyber.example.com",
            "country": "Colombia",
            "industry": "cybersecurity",
            "manual_context": "Firma de ciberseguridad para empresas medianas.",
            "action": "research_and_draft",
            "status": "new",
        },
    }

    graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
    checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})

    assert checkpoint is not None
    assert checkpoint["channel_values"]["lead_id"] == "lead_123"
    assert checkpoint["channel_values"]["status"] == "drafted"

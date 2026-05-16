from app.graph.builder import build_research_and_draft_graph


def test_graph_generates_research_and_draft_output() -> None:
    graph = build_research_and_draft_graph()
    state = {
        "run_id": "run_001",
        "lead_id": "lead_good_001",
        "action": "research_and_draft",
        "lead": {
            "lead_id": "lead_good_001",
            "company_name": "Andes ERP Partners",
            "company_website": "https://andeserp.example.com",
            "prospect_name": "Camila Rojas",
            "prospect_title": "Founder",
            "prospect_email": "camila@andeserp.example.com",
            "country": "Peru",
            "industry": "ERP implementation",
            "source": "manual",
            "manual_context": "Consultora B2B de implementacion ERP con ventas consultivas.",
            "action": "research_and_draft",
            "status": "new",
        },
    }

    result = graph.invoke(state, config={"configurable": {"thread_id": "run_001:lead_good_001"}})

    assert result["status"] == "drafted"
    assert result["fit_score"] >= 90
    assert result["message_angle"]
    assert "Andes ERP Partners" in result["email_subject"]
    assert result["email_draft"]
    assert result["quality_score"] >= 70
    assert result["agent_note"]


def test_graph_routes_invalid_lead_to_error_result() -> None:
    graph = build_research_and_draft_graph()
    state = {
        "run_id": "run_001",
        "lead_id": "broken",
        "action": "research_and_draft",
        "lead": {
            "lead_id": "broken",
            "company_name": "",
            "action": "research_and_draft",
            "status": "new",
        },
    }

    result = graph.invoke(state, config={"configurable": {"thread_id": "run_001:broken"}})

    assert result["status"] == "error"
    assert result["error_message"]
    assert result["agent_note"] == "Graph failed before drafting."

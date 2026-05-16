from app.graph.builder import build_research_and_draft_graph
from app.services.revision_hash import hash_revision_instruction


def test_graph_processes_revision_instruction() -> None:
    instruction = "Hazlo mas directo y menciona trazabilidad de evidencia."
    graph = build_research_and_draft_graph()
    state = {
        "run_id": "run_005",
        "lead_id": "lead_revision_001",
        "action": "revise",
        "lead": {
            "lead_id": "lead_revision_001",
            "company_name": "Nova Cyber Advisors",
            "company_website": "https://novacyber.example.com",
            "prospect_name": "Martin Silva",
            "prospect_title": "Sales Director",
            "prospect_email": "martin@novacyber.example.com",
            "industry": "cybersecurity",
            "manual_context": "Firma de ciberseguridad con servicios para empresas medianas.",
            "action": "revise",
            "status": "drafted",
            "email_draft": "Hola Martin, vi que Nova Cyber Advisors vende servicios B2B.",
            "revision_instruction": instruction,
            "revision_count": 0,
        },
    }

    result = graph.invoke(
        state,
        config={"configurable": {"thread_id": "run_005:lead_revision_001"}},
    )

    assert result["status"] == "revised"
    assert result["revision_count"] == 1
    assert result["revision_instruction_hash"] == hash_revision_instruction(instruction)
    assert result["last_processed_revision_hash"] == hash_revision_instruction(instruction)
    assert "Ajuste aplicado" in result["revised_draft"]
    assert "Revision applied" in result["agent_note"]


def test_graph_does_not_reprocess_same_revision_hash() -> None:
    instruction = "Hazlo mas corto."
    revision_hash = hash_revision_instruction(instruction)
    graph = build_research_and_draft_graph()
    state = {
        "run_id": "run_005",
        "lead_id": "lead_revision_002",
        "action": "revise",
        "lead": {
            "lead_id": "lead_revision_002",
            "company_name": "Pacific Data Co",
            "prospect_name": "Ana Ruiz",
            "prospect_email": "ana@pacificdata.example.com",
            "action": "revise",
            "status": "revised",
            "email_draft": "Hola Ana, draft previo.",
            "revision_instruction": instruction,
            "revision_instruction_hash": revision_hash,
            "last_processed_revision_hash": revision_hash,
            "revision_count": 2,
        },
    }

    result = graph.invoke(
        state,
        config={"configurable": {"thread_id": "run_005:lead_revision_002"}},
    )

    assert result["status"] == "revised"
    assert result["revision_count"] == 2
    assert result["agent_note"] == "Revision instruction already processed."

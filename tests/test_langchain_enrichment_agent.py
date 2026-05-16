from app.core.config import Settings
from app.domain.enrichment import EvidenceItem
from app.graph.enrichment_agent_builder import (
    AgentEnrichmentOutput,
    DeterministicEnrichmentAgent,
    LangChainEnrichmentAgent,
    build_enrichment_agent,
)


class FakeCreatedAgent:
    def invoke(self, payload, config=None):
        self.config = config
        return {
            "messages": [
                {"type": "human", "content": "lead"},
                {"type": "tool", "name": "web_search", "content": "snippet"},
            ],
            "structured_response": AgentEnrichmentOutput(
                enrichment_id="agent-output",
                company_summary="Acme sells B2B software.",
                b2b_fit=True,
                operational_pain_hypothesis="Scaling revenue ops.",
                possible_ai_use_case="Automate routing.",
                personalization_angle="Mention B2B software.",
                trigger_summary="Public search result.",
                risk_flags=[],
                evidence_items=[
                    EvidenceItem(
                        claim="Acme sells B2B software",
                        source_type="search_result",
                        source_url="https://search.example",
                        quote_or_summary="Acme vende software B2B.",
                        confidence=70,
                        used_in_message=True,
                    )
                ],
                confidence_score=75,
                recommended_action="needs_manual_research",
            ),
        }


def test_langchain_agent_invokes_create_agent_with_structured_output() -> None:
    calls = {}

    def fake_create_agent(**kwargs):
        calls.update(kwargs)
        return FakeCreatedAgent()

    runner = LangChainEnrichmentAgent(
        api_key="sk-test",
        model="gpt-test",
        reasoning_effort="low",
        base_url="https://api.openai.com/v1",
        create_agent_func=fake_create_agent,
        chat_model="fake-model",
    )
    result = runner.invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-1",
            "lead": {"lead_id": "lead-1", "company_name": "Acme", "country": "Mexico"},
        }
    )

    assert calls["model"] == "fake-model"
    assert calls["response_format"] is AgentEnrichmentOutput
    assert len(calls["tools"]) == 3
    assert result["structured_response"]["company_summary"] == "Acme sells B2B software."
    assert result["iteration_count"] == 1
    assert result["tool_calls_history"][0]["tool_name"] == "web_search"
    assert runner._agent.config["recursion_limit"] >= 8


def test_langchain_agent_discards_brazil_without_calling_model() -> None:
    def fail_create_agent(**kwargs):
        raise AssertionError("model should not be built for Brazil")

    runner = LangChainEnrichmentAgent(
        api_key="sk-test",
        model="gpt-test",
        reasoning_effort="low",
        base_url="https://api.openai.com/v1",
        create_agent_func=fail_create_agent,
        chat_model="fake-model",
    )
    result = runner.invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-br",
            "lead": {"lead_id": "lead-br", "company_name": "Acme", "country": "Brasil"},
        }
    )

    assert result["enrichment_result"]["recommended_action"] == "discard"


def test_enrichment_agent_factory_falls_back_without_openai_key() -> None:
    agent = build_enrichment_agent(Settings(enrichment_provider="openai", openai_api_key=""))

    assert isinstance(agent, DeterministicEnrichmentAgent)

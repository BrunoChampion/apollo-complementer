from langgraph.checkpoint.memory import InMemorySaver

from app.graph.enrichment_agent_builder import build_enrichment_agent_graph
from app.graph.enrichment_llm import EnrichmentLLM


def build_enrichment_graph(
    llm: EnrichmentLLM | None = None,
    checkpointer: InMemorySaver | None = None,
):
    # `llm` is accepted for backwards compatibility with existing tests/callers.
    return build_enrichment_agent_graph(
        agent=None,
        checkpointer=checkpointer,
    )

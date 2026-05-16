# OpenAI Setup

The app can use OpenAI through the Responses API for the LangGraph drafting flow.

## Environment

Set these in the root `.env`:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.5
OPENAI_REASONING_EFFORT=medium
OPENAI_BASE_URL=https://api.openai.com/v1
```

If `OPENAI_API_KEY` is blank, the app falls back to the deterministic local test LLM.

## Where It Is Used

The OpenAI provider is used for:

- manual context summarization,
- first cold email draft generation,
- revision of existing drafts.

The project uses Gmail draft creation only after human approval. The OpenAI provider does not send emails.

## Notes

Reasoning models should use the Responses API with:

```json
{"reasoning": {"effort": "medium"}}
```

The model name is configurable because availability can vary by account and date.

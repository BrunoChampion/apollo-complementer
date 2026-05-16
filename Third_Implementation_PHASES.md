# Revenue Ops Copilot - Third Implementation PHASES

**Fecha:** Mayo 2026  
**Spec:** `Third_Implementation_SPECS.md`  
**Base:** Phases 0-15 completadas (`Second_Implementation_PHASES.md`).  
**Objetivo:** Implementar un enrichment agent iterativo con tools usando patrones modernos de LangChain/LangGraph, guardrails determinísticos en draft y revise enriquecido desde Google Sheets.

---

## 0. Principios de Ejecución

1. Cada phase tiene tests propios que deben pasar antes de avanzar.
2. No modificar el agente original (`research_and_draft_graph`) ni sus tests.
3. `ruff check .` debe estar limpio al final de cada phase.
4. Mantener fases pequeñas, demostrables y útiles para aprender arquitectura de agentes.
5. El MVP debe ser práctico para ventas, pero también explicar con claridad: tool calling, middleware, state, structured output, tracing, guardrails y human-in-the-loop.
6. No procesar prospectos de Brasil ni mercados no hispanohablantes.

---

## Phase 1 - ICP Hispano, Configuración Base y Web Search Tool

### Objetivo

Preparar la base de la tercera implementación: países soportados, dependencias modernas de agentes y primera tool (`web_search`).

### Entregables

- Actualizar `pyproject.toml` con dependencias:
  - `langchain`
  - `langchain-openai`
  - `duckduckgo-search`
- `app/core/config.py`:
  - `DUCKDUCKGO_MAX_RESULTS`
  - `WEB_SEARCH_TIMEOUT_SECONDS`
  - `SUPPORTED_COUNTRIES`
  - `UNSUPPORTED_COUNTRIES`
- `app/services/web_search_service.py`
- `app/graph/enrichment_tools.py` con tool `web_search`
- Tests unitarios.

### Archivos Esperados

```text
app/services/web_search_service.py
app/graph/enrichment_tools.py
tests/test_web_search_tool.py
tests/test_supported_countries.py
```

### Detalle Técnico

La tool `web_search` debe:

- Recibir `query: str` y `max_results: int = 5`.
- Usar `duckduckgo-search`.
- Devolver `list[dict]` con `title`, `snippet`, `url`.
- Retry 1 vez.
- Timeout 10s.
- Nunca abrir URLs de resultados.
- Tener type hints y docstring clara para LangChain tools.
- Usar nombre `web_search`.

Las reglas ICP deben:

- Soportar México, Colombia, Chile, Perú, Argentina, Uruguay, Costa Rica, Panamá y España.
- Rechazar Brasil/Brazil.
- Mantener todo draft en español.

### Validación

```bash
pytest tests/test_web_search_tool.py tests/test_supported_countries.py -v
ruff check app/services/web_search_service.py app/graph/enrichment_tools.py app/core/config.py
```

### No Hacer

- No conectar todavía al enrichment graph.
- No implementar Bing fallback.
- No hacer requests reales en tests.

---

## Phase 2 - Website Stack Analyzer y GitHub Org Tool

### Objetivo

Crear las dos tools restantes: `analyze_website_stack` y `github_search_org`.

### Entregables

- `app/services/website_stack_analyzer.py`
- `app/services/github_org_service.py`
- Actualizar `app/graph/enrichment_tools.py` para registrar las 3 tools.
- Tests unitarios.

### Archivos Esperados

```text
app/services/website_stack_analyzer.py
app/services/github_org_service.py
tests/test_website_stack_analyzer.py
tests/test_github_org_service.py
```

### Detalle Técnico

**`analyze_website_stack`:**

- Input: `url: str`.
- HTTP GET con timeout 10s.
- User-Agent realista.
- Límite máximo de descarga: 500KB.
- Solo homepage.
- Detectar HubSpot, Salesforce, Intercom, Zendesk, Google Analytics, Shopify, WooCommerce, WordPress.
- Devolver `technologies`, `has_chatbot`, `has_crm`, `has_ecommerce`, `raw_signals`.

**`github_search_org`:**

- Input: `company_domain: str`, `company_name: str | None`.
- Probar dominio normalizado y variaciones de company name.
- Devolver `org_found`, `org_name`, `public_repos`, `top_languages`, `recent_activity`.
- Manejar 404 y rate limit sin romper el flujo.
- Considerar GitHub como señal best-effort.

### Validación

```bash
pytest tests/test_website_stack_analyzer.py tests/test_github_org_service.py -v
ruff check app/services/website_stack_analyzer.py app/services/github_org_service.py app/graph/enrichment_tools.py
```

---

## Phase 3 - Enrichment Agent Moderno con `create_agent`

### Objetivo

Implementar el enrichment researcher iterativo usando `langchain.agents.create_agent`, la API moderna recomendada sobre LangGraph v1.

### Entregables

- `app/graph/enrichment_agent_builder.py`
- `app/graph/enrichment_state.py` actualizado.
- Builder aislado para no acoplar todo el sistema a LangChain.
- Structured output compatible con `EnrichmentResult`.
- Tests de integración del agente.

### Archivos Esperados

```text
app/graph/enrichment_agent_builder.py
app/graph/enrichment_state.py
tests/test_enrichment_agent_builder.py
```

### Detalle Técnico

- Usar `from langchain.agents import create_agent`.
- Tools:
  - `web_search`
  - `analyze_website_stack`
  - `github_search_org`
- Modelo:
  - `langchain-openai` cuando `OPENAI_API_KEY` exista.
  - fallback determinístico/fake para tests.
- Usar `response_format` con schema Pydantic si la versión local lo soporta.
- Si structured output no es estable en tests, usar parser robusto.
- System prompt debe instruir:
  - investigar solo empresas B2B hispanohablantes high-ticket;
  - descartar Brasil;
  - usar snippets y homepage, no job boards directos;
  - detenerse con suficiente evidence;
  - devolver salida estructurada;
  - no inventar facts.

### Estado

Agregar a `EnrichmentState`:

```text
iteration_count
tool_calls_history
agent_messages
structured_response
```

### Validación

```bash
pytest tests/test_enrichment_agent_builder.py -v
ruff check app/graph/enrichment_agent_builder.py app/graph/enrichment_state.py
```

### No Hacer

- No eliminar `app/graph/enrichment_builder.py`.
- No modificar el draft agent.
- No depender de internet real en tests.

---

## Phase 4 - Orquestación, Scoring y Persistencia del Enrichment Iterativo

### Objetivo

Conectar el nuevo enrichment agent al flujo real sin romper el pipeline anterior.

### Entregables

- `app/graph/enrichment_builder.py` delega al nuevo builder o queda deprecado con compatibilidad.
- `app/services/enrich_and_draft_service.py` usa el nuevo enrichment agent.
- `app/services/lead_enrichment_service.py` usa el nuevo enrichment agent.
- Persistencia de `enrichment_result` en:
  - tab `Enrichment`;
  - columna `Leads.enrichment_result`;
  - DB cuando haya repositorio disponible.
- Extender scoring para países hispanohablantes y descarte de Brasil.

### Archivos Esperados

```text
app/graph/enrichment_builder.py
app/services/enrich_and_draft_service.py
app/services/lead_enrichment_service.py
app/services/enrichment_scoring.py
app/domain/leads.py
app/integrations/sheets/constants.py
tests/test_enrichment_iterative_integration.py
tests/test_enrichment_scoring_spanish_icp.py
```

### Detalle Técnico

- `score_enrichment_result()` debe penalizar países fuera de ICP.
- Brasil debe producir `discard`.
- La fila de `Leads` debe conservar `enrichment_result` como JSON string.
- Si el agente devuelve JSON inválido: `needs_manual_research` con `agent_note` claro.
- Si se alcanza límite de tool calls sin evidence suficiente: `needs_manual_research`.

### Validación

```bash
pytest tests/test_enrichment_iterative_integration.py tests/test_enrichment_scoring_spanish_icp.py -v
ruff check app/graph/enrichment_builder.py app/services/enrich_and_draft_service.py app/services/lead_enrichment_service.py app/services/enrichment_scoring.py
```

---

## Phase 5 - Guardrails en el Draft Agent

### Objetivo

Agregar validaciones determinísticas después de `draft_message` en `enrich_and_draft_graph`.

### Entregables

- `app/graph/draft_guardrails.py`
- Modificar `app/graph/enrich_and_draft_builder.py`
- Tests unitarios.

### Archivos Esperados

```text
app/graph/draft_guardrails.py
app/graph/enrich_and_draft_builder.py
tests/test_draft_guardrails.py
```

### Detalle Técnico

Nuevo flujo:

```text
draft_message -> verify_claims -> language_validator -> tone_checker -> evaluate_draft
```

**`verify_claims_against_evidence`:**

- Validar solo claims fuertes.
- Comparar contra `claim` y `quote_or_summary`.
- Si no hay respaldo, `needs_revision`.

**`language_validator`:**

- Solo español.
- Brasil/Brazil no pasa.
- Rechazar drafts en inglés o portugués.

**`tone_checker`:**

- Usar `avoid_phrases` del playbook.
- Agregar frases genéricas en inglés y español.

### Validación

```bash
pytest tests/test_draft_guardrails.py -v
ruff check app/graph/draft_guardrails.py app/graph/enrich_and_draft_builder.py
```

---

## Phase 6 - Revise Enriquecido desde Google Sheets

### Objetivo

Agregar soporte para revisar drafts enriquecidos leyendo `revision_instruction` desde la Sheet, sin re-enriquecer.

### Entregables

- `app/graph/revise_builder.py`
- `app/api/routes/enrichment.py` endpoint `POST /enrichment/revise`
- `app/services/enrich_and_draft_service.py` método `revise_enriched_draft`
- `app/services/lead_enrich_and_draft_service.py` método para procesar filas de revise
- Tests de integración.

### Archivos Esperados

```text
app/graph/revise_builder.py
app/api/routes/enrichment.py
app/services/enrich_and_draft_service.py
app/services/lead_enrich_and_draft_service.py
tests/test_enrichment_revise.py
```

### Detalle Técnico

**Endpoint `POST /enrichment/revise`:**

Request:

```json
{
  "source": "fake_sheet",
  "sheet_id": null,
  "tab_name": "Leads",
  "lead_ids": ["lead_001"],
  "run_id": "manual_revise"
}
```

El backend:

- lee la Sheet;
- filtra leads;
- obtiene `revision_instruction` desde la fila;
- valida `enrichment_result` y draft previo;
- no ejecuta enrichment;
- ejecuta revise;
- corre guardrails;
- actualiza Sheet.

### Validación

```bash
pytest tests/test_enrichment_revise.py -v
ruff check app/graph/revise_builder.py app/api/routes/enrichment.py app/services/enrich_and_draft_service.py app/services/lead_enrich_and_draft_service.py
```

---

## Phase 7 - Middleware, Langfuse Tracing y Budget OpenAI

### Objetivo

Hacer visible y gobernable el comportamiento del agente iterativo.

### Entregables

- Tool tracing con `app/core/langfuse.py`.
- `tool_calls_history` completo.
- Budget OpenAI en `CreditBudgetService`.
- Tests de tracing y budget.

### Archivos Esperados

```text
app/core/langfuse.py
app/services/credit_budget_service.py
app/graph/enrichment_agent_builder.py
tests/test_enrichment_tool_tracing.py
tests/test_openai_budget_service.py
```

### Detalle Técnico

- Cada tool call registra:
  - name;
  - input;
  - output;
  - error;
  - duration;
  - iteration index.
- Usar `NoOpTracer` en tests por default.
- `InMemoryTracer` debe permitir assertions.
- OpenAI budget debe soportar tokens o USD estimado.

### Validación

```bash
pytest tests/test_enrichment_tool_tracing.py tests/test_openai_budget_service.py -v
ruff check app/core/langfuse.py app/services/credit_budget_service.py app/graph/enrichment_agent_builder.py
```

---

## Phase 8 - E2E, Apps Script, Docs y Hardening

### Objetivo

Cerrar la implementación con flujo completo, documentación y demo operable.

### Entregables

- Test end-to-end:
  - enrich;
  - draft con guardrails;
  - revise desde Sheet;
  - no Brasil;
  - trace visible.
- Actualizar `docs/demo_script.md`.
- Actualizar `docs/weekly_operations_guide.md`.
- Actualizar `README.md`.
- Apps Script opcional: menú `Revisar draft enriquecido`.
- `ruff check .` limpio.

### Archivos Esperados

```text
tests/test_integration_e2e.py
docs/demo_script.md
docs/weekly_operations_guide.md
README.md
apps_script/Code.gs
```

### Validación

```bash
pytest tests/ -v --tb=short
ruff check .
ruff format --check .
```

### Criterios de Éxito

- >=90% de tests pasan.
- `ruff check .` limpio.
- `POST /runs` sigue funcionando.
- `POST /enrichment/enrich_and_draft` funciona.
- `POST /enrichment/revise` lee instrucciones desde Sheet.
- Brasil no produce drafts.
- Tool calls aparecen en trazas.
- El comportamiento del agente se puede explicar en demo comercial.

---

## Orden Recomendado de Ejecución

```text
Phase 1: ICP + Web Search Tool + dependencias modernas
Phase 2: Stack Analyzer + GitHub Tool
Phase 3: Enrichment Agent con create_agent
Phase 4: Orquestación + scoring + persistencia
Phase 5: Guardrails en Draft Agent
Phase 6: Revise desde Google Sheets
Phase 7: Middleware + Langfuse + Budget OpenAI
Phase 8: E2E + Apps Script + Docs + Hardening
```

**Razón del orden:**

- Primero se define el mercado y las tools.
- Luego se construye el agente moderno.
- Después se conecta al flujo real.
- Guardrails antes de revise.
- Observabilidad y budget cuando el flujo ya existe.
- Docs y demo al final.

---

## Checklist de No Hacer

- No procesar Brasil.
- No generar drafts en portugués.
- No scrapear LinkedIn, Indeed, Computrabajo, GetOnBoard ni job boards directamente.
- No dar tools de investigación al draft agent.
- No modificar `research_and_draft_graph`.
- No usar SerpAPI/Tavily en este MVP.
- No agregar loops sin límite.
- No hacer commits de git sin confirmación del usuario.
- No depender de internet real en tests.


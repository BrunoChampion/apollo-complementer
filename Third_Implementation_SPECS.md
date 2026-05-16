# Revenue Ops Copilot - Third Implementation SPECS

**Fecha:** Mayo 2026  
**Base:** `Second_Implementation_SPECS.md` y `Second_Implementation_PHASES.md` (Phases 0-15 completadas).  
**Objetivo:** Evolucionar el enrichment agent de pipeline fijo a agente iterativo con tools; agregar guardrails al draft agent; agregar soporte de `revise` desde Google Sheets para el flujo enriquecido.

---

## 0. Principios de Diseño

1. **El enrichment agent es el único investigador.** El draft agent nunca busca información; solo redacta o revisa usando el evidence entregado.
2. **ICP hispanohablante high-ticket.** El sistema no trabaja prospectos de Brasil ni mercados no hispanohablantes. Brasil debe descartarse temprano.
3. **Compliance estricto:** Solo se leen snippets de motores de búsqueda. Nunca se scrapean job boards (LinkedIn, Indeed, Computrabajo, GetOnBoard) directamente.
4. **Costo controlado:** Máximo 5 tool calls por lead. Si no hay evidence suficiente, el agente se detiene y marca `needs_manual_research`.
5. **Hard stop de budget:** Apollo y OpenAI tienen límites mensuales configurables. El sistema rechaza ejecuciones que los excederían.
6. **Trazabilidad:** Langfuse trackea cada tool call como span anidado con input, output, timing y costo estimado.
7. **Determinismo en draft:** Los guardrails son nodos de Python puro, no llamadas adicionales al LLM.
8. **Human-in-the-loop:** El usuario revisa enrichment, drafts y revisiones en Google Sheets antes de aprobar.
9. **MVP didáctico:** La implementación debe enseñar patrones modernos de agentes: tool calling, middleware, state, structured output, guardrails, observability y budget control.

---

## 1. ICP y Cobertura Geográfica

### 1.1 Países Soportados

El MVP apunta a empresas B2B high-ticket de países hispanohablantes con potencial de venta consultiva:

- México
- Colombia
- Chile
- Perú
- Argentina
- Uruguay
- Costa Rica
- Panamá
- España

### 1.2 Países No Soportados

- Brasil
- Estados Unidos-only
- Canadá-only
- Mercados no hispanohablantes
- Empresas sin señales B2B o sin buyer claro

### 1.3 Reglas de Scoring

- Si `country` es `Brazil` o `Brasil`, `recommended_action = discard`.
- Si `country` está en países soportados, se aplica boost ICP.
- Si el país está vacío pero hay señales hispanohablantes en website/snippets, se permite `needs_manual_research`.
- Si el país está fuera del ICP, se penaliza y no se debe generar draft.
- Todo draft debe estar en español profesional, neutro LATAM salvo que el país requiera matiz local.

---

## 2. Arquitectura de Agentes (Target)

### 2.1 Enrichment Agent (Iterativo con Tools)

Reemplaza el pipeline fijo de 6 nodos por un agente iterativo que decide qué buscar.

**API recomendada a mayo 2026:** `langchain.agents.create_agent`.

**Nota de aprendizaje:** `langgraph.prebuilt.create_react_agent` fue el prebuilt clásico de LangGraph para agentes ReAct, pero LangGraph v1 lo marca como deprecado en favor de `create_agent` de LangChain v1. `create_agent` corre sobre LangGraph y agrega middleware, mejor structured output y una API más moderna. Se debe aprender el patrón ReAct, pero implementar con la API vigente.

**Forma recomendada del grafo:**

```text
START
  |
  v
validate_enrichment_input
  |
  v
run_enrichment_agent (LangChain create_agent sobre LangGraph)
  |
  v
validate_and_score
  |
  v
persist_enrichment_result
  |
  v
END
```

El agente interno usa el loop estándar:

```text
LLM decides -> tool call(s) -> tool result(s) -> LLM decides again -> final structured response
```

**Estado compartido:** `EnrichmentState` (TypedDict), extendido con:

```text
iteration_count: int  (default 0, max 5)
tool_calls_history: list[dict]  (debugging, auditoría y demo comercial)
agent_messages: list[dict]  (opcional; mensajes compactados del agente)
structured_response: dict | None  (respuesta final del agente)
```

**Structured output:**

El agente debe devolver una salida compatible con `EnrichmentResult`. Idealmente usar `response_format` de `create_agent` con un schema Pydantic o `ToolStrategy`. Si la versión local no lo permite de forma estable, usar fallback:

```text
final AIMessage -> parse_json_safely -> EnrichmentResult.model_validate()
```

El parser debe soportar:

- JSON puro.
- JSON envuelto en markdown.
- Campos faltantes.
- Evidence inválido.
- Mensaje final no JSON.

**Nodo final (`validate_and_score`):**

- Parsea la salida del agente a `EnrichmentResult`.
- Valida que haya >=1 evidence item.
- Corre `score_enrichment_result()` con reglas ICP hispanohablantes.
- Si score < 35 o no hay evidence: `recommended_action = discard` o `needs_manual_research`.
- Si Brasil/no hispanohablante: `recommended_action = discard`.
- Persiste en DB, tab `Enrichment` y columna `enrichment_result` de `Leads`.

### 2.2 Middleware del Enrichment Agent

Para aprender y demostrar arquitectura moderna de agentes, usar middleware o wrappers equivalentes:

1. **ToolBudgetMiddleware**
   - Cuenta tool calls.
   - Corta al llegar a `ENRICHMENT_MAX_ITERATIONS=5`.
   - Devuelve `needs_manual_research` si el agente no produjo evidence suficiente.

2. **ToolTracingMiddleware**
   - Registra cada tool call con `tool_name`, input, output, duración, error y costo estimado.
   - Alimenta `tool_calls_history`.
   - Emite spans de Langfuse.

3. **ComplianceMiddleware**
   - Bloquea scraping directo de job boards.
   - Permite leer snippets de motores de búsqueda.
   - Bloquea cualquier intento de pasar URLs de LinkedIn/Indeed/Computrabajo/GetOnBoard a fetchers directos.

4. **SpanishICPGuardMiddleware** o validación equivalente
   - Descarta Brasil y mercados no hispanohablantes antes de gastar más tokens.

### 2.3 Draft Agent (Pipeline Fijo + Guardrails)

Se mantiene como pipeline fijo. Se agregan 3 nodos de validación después de `draft_message`.

```text
START
  |
  v
gate_draft --[FAIL]--> write_result
  |[PASS]
  v
load_playbook
  |
  v
inject_context (enrichment_result + manual_context)
  |
  v
select_message_angle
  |
  v
draft_message (LLM call #1 del draft)
  |
  v
verify_claims_against_evidence --[FAIL]--> write_result (needs_revision)
  |[PASS]
  v
language_validator --[FAIL]--> write_result (needs_revision)
  |[PASS]
  v
tone_checker --[FAIL]--> write_result (needs_revision)
  |[PASS]
  v
evaluate_draft
  |
  v
write_result
  |
  v
END
```

### 2.4 Revise en Flujo Enriquecido

El revise enriquecido se dispara desde Google Sheets. El usuario escribe `revision_instruction` en la fila del lead y ejecuta el endpoint o menú correspondiente.

**Condición:** El lead tiene:

- `enrichment_result` persistido en `Leads` o DB.
- `email_draft` o `revised_draft` previo.
- `revision_instruction` en Google Sheets.

**Comportamiento:**

1. NO re-ejecuta `enrichment_graph`.
2. Lee la fila desde Sheet.
3. Lee `enrichment_result` existente desde `Leads.enrichment_result`; si no existe, intenta DB.
4. Ejecuta `revise_enriched_draft_graph`.
5. El LLM recibe:
   - Draft anterior.
   - `revision_instruction`.
   - `enrichment_result`.
   - `evidence_items`.
   - Playbook.
6. Corre guardrails (`verify_claims`, `language`, `tone`) sobre el nuevo draft.
7. Persiste el resultado actualizado en Sheet y, cuando aplique, DB.

---

## 3. Tools del Enrichment Agent

### 3.1 `web_search`

**Descripción:** Busca en la web usando DuckDuckGo (`duckduckgo-search`). Devuelve snippets del motor de búsqueda, no scrapea páginas destino.

**Input:**

```json
{
  "query": "string",
  "max_results": 5
}
```

**Output:**

```json
[
  {
    "title": "string",
    "snippet": "string",
    "url": "string"
  }
]
```

**Uso de job postings:** El agente genera queries como:

- `"{company_name} empleo"`
- `"{company_name} estamos contratando"`
- `"{company_name} careers"`
- `"{company_name} hiring"`

Solo se lee el snippet del buscador. No se accede a la URL de job boards.

**Implementación:**

- Wrapper alrededor de `duckduckgo-search`.
- Retry 1 vez.
- Timeout 10s.
- Tests mockeados; no depender de internet en CI.
- Nombre snake_case y type hints/docstring clara para compatibilidad con LangChain tools.

### 3.2 `analyze_website_stack`

**Descripción:** Analiza HTML de la homepage del prospecto para detectar tecnologías.

**Input:**

```json
{
  "url": "https://acme.com"
}
```

**Output:**

```json
{
  "technologies": ["HubSpot", "Google Analytics", "Shopify"],
  "has_chatbot": true,
  "has_crm": true,
  "has_ecommerce": false,
  "raw_signals": ["hubspot.net", "googletagmanager.com"]
}
```

**Método:**

- HTTP GET con timeout 10s.
- User-Agent realista.
- Límite de descarga: 500KB.
- Solo homepage.
- String matching en HTML crudo:
  - HubSpot: `hubspot.net`, `hs-scripts.com`
  - Salesforce: `salesforce.com`
  - Intercom: `intercom.io`, `intercomcdn.com`
  - Zendesk: `zendesk.com`
  - Google Analytics: `googletagmanager.com`, `google-analytics.com`
  - Shopify: `myshopify.com`, `shopify.com`
  - WooCommerce: `woocommerce.com`
  - WordPress: `wp-content`, `wordpress.org`

### 3.3 `github_search_org`

**Descripción:** Busca organización pública de GitHub para detectar stack técnico y madurez.

**Input:**

```json
{
  "company_domain": "acme.com",
  "company_name": "Acme Corp"
}
```

**Output:**

```json
{
  "org_found": true,
  "org_name": "acme-corp",
  "public_repos": 12,
  "top_languages": ["Python", "TypeScript"],
  "recent_activity": true
}
```

**Método:**

- GitHub API pública.
- Probar dominio normalizado y variaciones de company name.
- Si hay 404/rate limit, devolver `org_found=false`.
- Es señal best-effort, nunca requisito para draft.

---

## 4. Guardrails del Draft Agent

### 4.1 `verify_claims_against_evidence`

**Input:** Estado del grafo con `email_draft` y `evidence_items`.

**Lógica MVP:**

1. Tokenizar el draft en oraciones.
2. Solo validar claims factuales fuertes:
   - números o métricas;
   - fechas;
   - contratación/hiring;
   - uso de herramientas concretas (`HubSpot`, `Intercom`, etc.);
   - funding, expansión, clientes, sedes, eventos.
3. Comparar cada claim contra:
   - `evidence_items[*].claim`
   - `evidence_items[*].quote_or_summary`
4. Si no hay match razonable: `needs_revision`.

**Regla conservadora:** Si el match es dudoso, marcar `needs_revision`. Es preferible pedir revisión humana que aprobar un claim inventado.

**No validar como claim fuerte:**

- hipótesis suaves;
- frases tipo "parece que están escalando";
- value props de NYVEX;
- CTA.

### 4.2 `language_validator`

El sistema solo soporta español.

**Lógica:**

- Si `country` es Brasil/Brazil: `status=discard` o `needs_manual_research`, sin draft.
- Para países soportados: verificar que el draft tenga señales de español y no esté en inglés/portugués.
- No exigir palabras específicas como `usted`; el español puede ser profesional y directo sin esas marcas.
- Permitir matices locales si el playbook los define.

### 4.3 `tone_checker`

**Lógica:**

- Usa `avoid_phrases` del playbook y una lista base.
- Detecta frases genéricas de outbound:
  - `i hope this email finds you well`
  - `i am reaching out because`
  - `just checking in`
  - `wanted to touch base`
  - `circle back`
  - `quick question`
  - `espero que este correo te encuentre bien`
  - `me pongo en contacto porque`
- Si encuentra alguna frase: `needs_revision`.

---

## 5. Revise en Flujo Enriquecido

### 5.1 Endpoint

```http
POST /enrichment/revise
```

**Request body:**

```json
{
  "source": "fake_sheet",
  "sheet_id": null,
  "tab_name": "Leads",
  "lead_ids": ["apollo_123"],
  "run_id": "manual_revise_001"
}
```

`revision_instruction` no viene necesariamente en el body. La fuente de verdad es la Sheet.

### 5.2 Comportamiento

1. Lee rows de `Leads`.
2. Filtra por `lead_ids` si vienen.
3. Procesa filas con:
   - `action = revise`, o
   - `status = needs_revision` y `revision_instruction` no vacío.
4. Valida que exista:
   - `enrichment_result`;
   - `email_draft` o `revised_draft`;
   - `revision_instruction`.
5. NO ejecuta enrichment.
6. Ejecuta `revise_enriched_draft_graph`.
7. Corre guardrails.
8. Actualiza la fila:
   - `email_draft` o `revised_draft`;
   - `status`;
   - `quality_score`;
   - `quality_issues`;
   - `revision_instruction_hash`;
   - `last_processed_revision_hash`;
   - `revision_count`;
   - `agent_note`.

### 5.3 Prompt del LLM para Revisión

```text
You are revising a Spanish outbound email draft based on user feedback.

Rules:
1. Keep all evidence-backed claims from the original draft unless the user asks to remove them.
2. Apply only the requested changes from the revision instruction.
3. Do not add new claims unless they are backed by the provided evidence items.
4. Keep the email in professional Spanish for a high-ticket B2B buyer.
5. Do not mention Brazil or Portuguese markets.
6. Keep the draft concise and aligned with the playbook.

Original draft: {previous_draft}
Revision instruction: {revision_instruction}
Evidence items: {evidence_items}
Enrichment result: {enrichment_result}
Playbook rules: {playbook}

Return the revised draft email body only.
```

---

## 6. Credit Budget y Cost Control

### 6.1 Enrichment Agent Iterativo

**Estimación de costo por lead:**

- 1-5 LLM calls dependiendo de tool loop.
- Tool calls gratuitas: `web_search`, `analyze_website_stack`, `github_search_org`.
- Total esperado MVP: bajo, pero variable por número de iteraciones.

### 6.2 Límites

| Límite | Valor | Dónde se aplica |
|--------|-------|-----------------|
| Max tool calls | 5 | middleware/state |
| Max web_search results | 5 por query | tool input |
| Max URLs en `analyze_website_stack` | 1 homepage | tool input |
| Timeout por tool call | 10 segundos | configuración |
| Max HTML download | 500KB | website analyzer |
| Budget mensual Apollo | configurable | `CreditBudgetService` |
| Budget mensual OpenAI | configurable | `CreditBudgetService` extendido |

### 6.3 Hard Stop OpenAI

El servicio actual debe extenderse para soportar OpenAI:

- `OPENAI_MONTHLY_TOKEN_BUDGET`
- `OPENAI_MONTHLY_USD_BUDGET` (opcional)
- `ProviderUsage(provider="openai")`
- estimación previa por batch;
- registro posterior cuando el provider devuelva usage metadata.

Antes de ejecutar enrichment batch:

```text
CreditBudgetService.check_budget("openai", estimated_tokens_or_cost)
```

Si `used + estimated > budget`: no se ejecuta.

---

## 7. Langfuse Observability

### 7.1 Tool Execution Tracing

Cada tool call se registra como span anidado:

```text
TRACE: enrichment-lead-123
|-- GENERATION: agent_decision
|-- SPAN: web_search
|   |-- input: {"query": "Acme Corp Mexico empleo"}
|   |-- output: [{"title": "...", "snippet": "..."}]
|   |-- timing: 1.2s
|-- GENERATION: agent_decision
|-- SPAN: analyze_website_stack
|   |-- input: {"url": "https://acme.com"}
|   |-- output: {"technologies": ["HubSpot"]}
|   |-- timing: 0.8s
|-- SPAN: validate_and_score
```

### 7.2 Implementación

Preferir la abstracción existente en `app/core/langfuse.py` (`Tracer`, `NoOpTracer`, `LangfuseTracer`) para mantener testabilidad.

Si `create_agent` permite callbacks/middleware limpio, integrarlo ahí. Si no, envolver tools con un tracer local.

---

## 8. Modelos de Datos

### 8.1 Cambios a `EnrichmentState`

```python
class EnrichmentState(TypedDict):
    run_id: str
    lead_id: str
    lead: dict[str, Any]
    enrichment_id: NotRequired[str]
    enrichment_result: NotRequired[dict[str, Any]]
    evidence_items: NotRequired[list[dict[str, Any]]]
    status: NotRequired[str]
    error_message: NotRequired[str]
    agent_note: NotRequired[str]
    iteration_count: NotRequired[int]
    tool_calls_history: NotRequired[list[dict]]
    agent_messages: NotRequired[list[dict[str, Any]]]
    structured_response: NotRequired[dict[str, Any]]
```

### 8.2 Cambios a `LeadState`

```python
class LeadState(TypedDict):
    run_id: str
    lead_id: str
    action: str
    lead: dict[str, Any]
    enrichment_result: NotRequired[dict[str, Any]]
    email_draft: NotRequired[str]
    email_subject: NotRequired[str]
    revision_instruction: NotRequired[str]
    previous_draft: NotRequired[str]
    # resto de campos existentes
```

### 8.3 `LeadRow`

Agregar si no existe:

```text
enrichment_result: str | dict | None
```

El valor se guarda en Sheet como JSON string y se parsea al ejecutar draft/revise.

---

## 9. Google Sheets

### 9.1 Tab `Enrichment`

Se mantiene. Registra historial de enriquecimientos.

### 9.2 Tab `Leads`

Agregar/asegurar columna:

- `enrichment_result`

Columnas ya existentes relevantes:

- `email_draft`
- `revised_draft`
- `revision_instruction`
- `revision_instruction_hash`
- `last_processed_revision_hash`
- `revision_count`
- `status`
- `agent_note`

### 9.3 Apps Script

Agregar opción de menú opcional:

```text
Revisar draft enriquecido
```

Esta opción llama `POST /enrichment/revise` y deja que el backend lea `revision_instruction` desde la Sheet.

---

## 10. Tests Requeridos

### 10.1 Unitarios por Tool

- `test_web_search_returns_snippets`
- `test_web_search_handles_failure_with_empty_list`
- `test_web_search_job_posting_snippets_mocked`
- `test_analyze_website_stack_detects_hubspot`
- `test_analyze_website_stack_limits_download_size`
- `test_github_search_org_found`
- `test_github_search_org_not_found`
- `test_github_search_org_rate_limited`

### 10.2 Integración del Enrichment Agent Iterativo

- `test_agent_stops_after_5_tool_calls`
- `test_agent_uses_web_search_then_stack`
- `test_agent_returns_structured_enrichment_result`
- `test_agent_handles_invalid_json_final_message`
- `test_agent_discards_brazil`
- `test_agent_falls_back_to_needs_manual_research`

### 10.3 Guardrails

- `test_verify_claims_detects_unsupported_number`
- `test_verify_claims_passes_with_claim_or_quote_match`
- `test_language_validator_rejects_non_spanish`
- `test_language_validator_discards_brazil`
- `test_tone_checker_detects_generic`

### 10.4 Revise desde Sheet

- `test_revise_reads_revision_instruction_from_sheet`
- `test_revise_uses_existing_enrichment`
- `test_revise_does_not_call_enrichment_graph`
- `test_revise_applies_instruction`
- `test_revise_runs_guardrails`
- `test_revise_skips_already_processed_hash`

---

## 11. Configuración (.env)

```env
# Web Search
DUCKDUCKGO_MAX_RESULTS=5
WEB_SEARCH_TIMEOUT_SECONDS=10

# Enrichment Agent
ENRICHMENT_MAX_ITERATIONS=5
ENRICHMENT_MAX_URLS_PER_LEAD=1
ENRICHMENT_MAX_HTML_BYTES=500000

# GitHub
GITHUB_API_TOKEN=

# ICP
SUPPORTED_COUNTRIES=Mexico,Colombia,Chile,Peru,Argentina,Uruguay,Costa Rica,Panama,Spain
UNSUPPORTED_COUNTRIES=Brazil,Brasil

# Langfuse
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com

# Budgets
APOLLO_MONTHLY_CREDIT_BUDGET=2500
OPENAI_MONTHLY_TOKEN_BUDGET=0
OPENAI_MONTHLY_USD_BUDGET=0
OPENAI_API_KEY=
```

---

## 12. Criterios de Éxito

El sistema será exitoso si:

- El enrichment agent encuentra evidence suficiente para >=60% de leads B2B hispanohablantes con website.
- Brasil y mercados no hispanohablantes no generan drafts.
- El draft agent no produce claims factuales fuertes sin evidence.
- El enrichment agent nunca excede 5 tool calls ni el budget mensual.
- `revise` lee instrucciones desde Google Sheets y mantiene el enrichment original.
- Todos los tests pasan y `ruff check .` está limpio.
- Langfuse muestra tool calls como spans anidados.
- El flujo original `POST /runs` sigue funcionando.
- La implementación puede explicarse como caso práctico de agentes modernos para ventas consultivas.

---

## 13. Riesgos y Mitigación

| Riesgo | Mitigación |
|--------|------------|
| DuckDuckGo bloquea IPs por volumen | Tests mockeados, retry, fallback futuro a Bing API. |
| `create_agent` requiere dependencias nuevas | Agregar `langchain`, `langchain-openai` y aislar en builder propio. |
| HTML pesado o lento | Timeout 10s + límite 500KB. |
| Tool loop innecesario | Max 5 tool calls + middleware de budget. |
| Structured output inválido | Parser robusto + tests de JSON inválido. |
| Guardrails demasiado estrictos | Validar solo claims fuertes; permitir hipótesis suaves. |
| Revise pierde evidence si Sheet trunca JSON | Guardar en DB y usar Sheet como fuente primaria cuando tenga JSON válido. |
| GitHub org discovery débil | Señal best-effort, nunca hard gate. |

---

## 14. Archivos Afectados (Resumen)

### Nuevos

- `app/graph/enrichment_tools.py` - definición de tools.
- `app/graph/enrichment_agent_builder.py` - agente iterativo con `create_agent`.
- `app/graph/draft_guardrails.py` - guardrails determinísticos.
- `app/graph/revise_builder.py` - revise enriquecido.
- `app/services/web_search_service.py`
- `app/services/website_stack_analyzer.py`
- `app/services/github_org_service.py`

### Modificados

- `pyproject.toml` - agregar `langchain`, `langchain-openai`, `duckduckgo-search`.
- `app/graph/enrichment_state.py`
- `app/graph/enrichment_builder.py` - deprecar o delegar al nuevo builder.
- `app/graph/enrich_and_draft_builder.py`
- `app/graph/state.py`
- `app/domain/leads.py` - agregar `enrichment_result` si falta.
- `app/services/enrich_and_draft_service.py`
- `app/services/lead_enrich_and_draft_service.py`
- `app/api/routes/enrichment.py`
- `app/core/config.py`
- `app/services/credit_budget_service.py`
- `app/integrations/sheets/constants.py`
- `apps_script/Code.gs` (opcional)

### Sin cambios

- `app/graph/builder.py` - agente original, intacto.
- `app/api/routes/runs.py` - flujo original intacto.
- `app/db/models.py` - no requiere nuevas tablas para MVP, salvo que se decida persistir `enrichment_result` completo.


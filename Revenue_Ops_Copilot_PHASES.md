# Revenue Ops Copilot - Fases De Desarrollo

**Fecha:** Mayo 2026  
**Propósito:** Plan de implementación incremental optimizado para desarrollo agéntico con IA.  
**Spec principal:** `Revenue_Ops_Copilot_SPECS.md`

---

## 0. Principios Para La Implementación

Este documento existe para evitar construir todo de una. El proyecto debe avanzar por capas pequeñas, verificables y reversibles.

Reglas:

1. No construir frontend en MVP.
2. No automatizar LinkedIn.
3. No auto-enviar emails.
4. Google Sheets es la UI principal.
5. Gmail solo crea drafts.
6. Playbook comercial vive en YAML.
7. Postgres guarda estado operacional.
8. LangGraph orquesta el flujo.
9. Langfuse observa el sistema.
10. Cada fase debe terminar con tests o verificación manual clara.

La implementación debe preferir primero un flujo local mockeado, luego Google Sheets, luego Gmail, luego CRM/export.

---

## 1. Mapa General De Fases

```text
Phase 0  - Bootstrap del proyecto
Phase 1  - Dominio, schemas y playbook YAML
Phase 2  - Google Sheets local abstraction con datos fake
Phase 3  - FastAPI async runs + Postgres control plane
Phase 4  - LangGraph core sin APIs externas + checkpointer
Phase 5  - Quality evaluator, evidence tracking y revision loop
Phase 6  - Worker simple, locking y límites de batch
Phase 7  - Google Sheets real + Apps Script
Phase 8  - Gmail drafts
Phase 9  - Langfuse tracing
Phase 10 - Email summary
Phase 11 - CSV exports
Phase 12 - HubSpot adapter opcional
Phase 13 - Hardening, docs y demo
```

Cada fase debe poder ejecutarse y validarse sin depender de las fases futuras.

---

## Phase 0 - Bootstrap Del Proyecto

### Objetivo

Crear la estructura base del proyecto, dependencias, configuración y tooling.

### Entregables

- Estructura de carpetas.
- `README.md` inicial.
- `.env.example`.
- `requirements.txt` o `pyproject.toml`.
- Configuración de `ruff`.
- Configuración mínima de `pytest`.
- App FastAPI mínima con `/health`.

### Archivos Esperados

```text
app/
  main.py
  core/config.py
  core/logging.py
tests/
  test_health.py
.env.example
README.md
```

### Validación

```bash
pytest
ruff check .
ruff format --check .
uvicorn app.main:app --reload
```

Endpoint:

```http
GET /health
```

Debe responder:

```json
{"status": "ok"}
```

### No Hacer Todavía

- No Google APIs.
- No LangGraph.
- No Postgres.
- No Gmail.
- No frontend.

---

## Phase 1 - Dominio, Schemas Y Playbook YAML

### Objetivo

Definir modelos internos estables antes de integrar APIs externas.

### Entregables

- Schemas Pydantic para filas de leads.
- Schemas para playbook.
- Loader de YAML.
- Fixture de playbook ejemplo.
- Dataset demo temprano con leads realistas.
- Validaciones básicas.

### Archivos Esperados

```text
app/playbook/schemas.py
app/playbook/loader.py
app/domain/leads.py
config/sales_playbook.yaml
examples/leads_demo.csv
tests/test_playbook_loader.py
tests/test_lead_schema.py
```

### Modelos Clave

- `LeadRow`
- `LeadAction`
- `LeadStatus`
- `SalesPlaybook`
- `BuyerPersona`
- `ValueProp`
- `CaseStudy`
- `Objection`

### Validación

```bash
pytest tests/test_playbook_loader.py tests/test_lead_schema.py
```

### Criterios De Éxito

- El playbook carga desde YAML.
- Campos requeridos se validan.
- Acciones inválidas fallan claramente.
- Estados inválidos fallan claramente.
- Existe dataset demo con casos buenos, débiles, fallidos y revisables.

### No Hacer Todavía

- No LLM.
- No Google Sheets real.
- No database.

---

## Phase 2 - Abstracción De Google Sheets Con Datos Fake

### Objetivo

Construir la interfaz interna para leer/escribir filas, usando primero almacenamiento local fake.

### Motivación

Antes de conectar Google Sheets real, el resto del sistema debe poder operar sobre una interfaz estable.

### Entregables

- `SheetClient` protocol/interface.
- `FakeSheetClient` basado en CSV/JSON.
- Selector de filas pendientes.
- Writer de resultados.
- Tests de selección y actualización.

### Archivos Esperados

```text
app/integrations/sheets/base.py
app/integrations/sheets/fake.py
app/services/row_selector.py
tests/fixtures/leads_sample.csv
tests/test_row_selector.py
tests/test_fake_sheet_client.py
```

### Reglas De Selección

Procesar:

```text
action IN ("research_and_draft", "revise", "create_gmail_draft")
AND status != "processing"
```

Revision:

```text
action = "revise"
AND revision_instruction != ""
AND revision_instruction_hash != last_processed_revision_hash
```

### Validación

```bash
pytest tests/test_row_selector.py tests/test_fake_sheet_client.py
```

### Criterios De Éxito

- Puede leer leads fake.
- Puede detectar pendientes.
- Puede marcar `processing`.
- Puede escribir outputs.
- Puede evitar reprocesar la misma revisión.
- Puede operar con la Sheet MVP visible y columnas avanzadas opcionales.

### No Hacer Todavía

- No Google API real.
- No Apps Script.

---

## Phase 3 - FastAPI Async Runs + Postgres Control Plane

### Objetivo

Crear runs asíncronos y persistencia operacional antes de integrar APIs reales.

### Entregables

- Endpoint `POST /runs` que devuelve `run_id` rápido.
- Endpoint `GET /runs/{run_id}`.
- Servicio `RunService`.
- Postgres básico para `runs` y `lead_runs`.
- Modelos/migraciones iniciales.
- Run states: `queued`, `running`, `completed`, `failed`.
- Procesamiento usando `FakeSheetClient`.

### Archivos Esperados

```text
app/api/routes/runs.py
app/services/run_service.py
app/db/models.py
app/db/session.py
app/db/repositories.py
alembic/
tests/test_runs_api.py
tests/test_run_persistence.py
```

### Validación

```bash
pytest tests/test_runs_api.py tests/test_run_persistence.py
```

### Criterios De Éxito

- `POST /runs` responde rápido con `run_id`.
- El run queda guardado.
- Cada fila procesada queda registrada.
- Errores por fila no rompen el run.

### No Hacer Todavía

- No Google Sheets real.
- No Gmail.
- No LangGraph checkpointer todavía si complica demasiado, pero dejar interfaz preparada.

---

## Phase 4 - LangGraph Core Sin APIs Externas + Checkpointer

### Objetivo

Construir el flujo agéntico principal con inputs fake y LLM configurable.

### Entregables

- `LeadState`.
- Graph builder.
- Nodos determinísticos.
- Nodos LLM mockeables.
- Flujo `research_and_draft`.
- Checkpointer LangGraph usando Postgres o alternativa compatible.
- `thread_id = "{run_id}:{lead_id}"`.
- Tests con LLM fake.

### Archivos Esperados

```text
app/graph/state.py
app/graph/builder.py
app/graph/nodes.py
app/graph/routing.py
app/prompts/extract_manual_context.md
app/prompts/draft_email.md
app/prompts/evaluate_message.md
tests/test_graph_research_and_draft.py
tests/test_graph_checkpointing.py
```

### Nodos MVP

```text
validate_input
load_playbook
extract_manual_context
score_fit
select_message_angle
draft_message
evaluate_draft
write_graph_result
```

### Decisión Importante

No todo debe ser LLM.

Determinístico:

- validación,
- routing,
- status,
- hashing,
- merging de outputs.

LLM:

- extracción de señales,
- hipótesis de dolor,
- draft,
- evaluación cualitativa.

### Validación

```bash
pytest tests/test_graph_research_and_draft.py
```

### Criterios De Éxito

- Un lead fake entra al graph.
- Sale con `email_draft`, `message_angle`, `fit_score`.
- Guarda/restaura estado del graph con `thread_id`.
- No requiere Google Sheets.
- No requiere Gmail.

### No Hacer Todavía

- No website scraping.
- No Gmail.
- No Postgres.

---

## Phase 5 - Quality Evaluator, Evidence Tracking Y Revision Loop

### Objetivo

Implementar el flujo que permite al vendedor pedir correcciones desde Sheets, con evidencia trazable y quality checks híbridos.

### Entregables

- Prompt de revisión.
- Nodo `revise_message`.
- Nodo o servicio `extract_evidence_items`.
- Tabla/modelo `evidence_items`.
- Hash de `revision_instruction`.
- Soporte para `revised_draft`.
- Quality evaluator determinístico + LLM judge.
- Tests de segunda revisión.

### Archivos Esperados

```text
app/prompts/revise_message.md
app/services/revision_hash.py
app/services/evidence.py
app/services/quality.py
tests/test_revision_flow.py
tests/test_evidence_items.py
tests/test_quality_checks.py
```

### Flujo

```text
previous draft + revision_instruction + playbook + context
    -> revised_draft
    -> quality evaluation
    -> updated row
```

### Validación

```bash
pytest tests/test_revision_flow.py
```

### Criterios De Éxito

- Si `revision_instruction` cambia, se procesa otra vez.
- Si no cambia, no se reprocesa.
- `revision_count` incrementa.
- `last_processed_revision_hash` se actualiza.
- `agent_note` explica qué cambió.
- Los claims usados tienen evidence items.
- Los mensajes con claims no soportados son marcados o rechazados.

### No Hacer Todavía

- No UI custom.
- No editor web.

---

## Phase 6 - Worker Simple, Locking Y Límites De Batch

### Objetivo

Hacer que el procesamiento sea confiable, limitado e idempotente antes de conectar Google Sheets real.

### Entregables

- Worker simple o FastAPI `BackgroundTasks` documentado.
- Locking por fila con `run_id` y `locked_at`.
- Expiración de locks.
- Límites configurables de batch.
- Reintentos básicos.
- Idempotencia para outputs.

### Archivos Esperados

```text
app/services/worker.py
app/services/locking.py
app/core/limits.py
tests/test_locking.py
tests/test_batch_limits.py
```

### Límites MVP

```text
manual_run_limit = 10 rows
scheduled_batch_limit = 50 rows
max_pages_per_company = 5
row_timeout_seconds = 120
max_revision_count_without_override = 2
```

### Validación

```bash
pytest tests/test_locking.py tests/test_batch_limits.py
```

### Criterios De Éxito

- Clicks duplicados no procesan dos veces la misma fila.
- Runs colgados pueden recuperarse por expiración de lock.
- Batch grande se limita.
- Costos/latencia quedan acotados.

### No Hacer Todavía

- No Google Sheets real.

---

## Phase 7 - Google Sheets Real + Apps Script

### Objetivo

Conectar Google Sheets real como UI operativa.

### Entregables

- `GoogleSheetClient`.
- OAuth/service account setup documentado.
- Lectura/escritura real de Sheet.
- Apps Script con menú.
- Botón "Procesar pendientes".
- Formato esperado de columnas.
- Botón que inicia `POST /runs`, recibe `run_id` y no espera a que termine el procesamiento.

### Archivos Esperados

```text
app/integrations/sheets/google.py
apps_script/Code.gs
docs/google_sheets_setup.md
tests/test_google_sheet_client_contract.py
```

### Apps Script Menu

```text
Revenue Copilot
  - Procesar pendientes
  - Crear borradores Gmail aprobados
  - Exportar CSV
```

### Validación Manual

1. Crear Google Sheet de prueba.
2. Agregar 3 leads.
3. Marcar `action = research_and_draft`.
4. Click en "Procesar pendientes".
5. Confirmar toast con `run_id`.
6. Confirmar que luego cambian `status`, `email_draft`, `agent_note`, `processed_at`.

### Criterios De Éxito

- El vendedor puede operar desde Sheets.
- No necesita CLI.
- Apps Script no bloquea esperando LLMs.
- La API actualiza filas reales.

### No Hacer Todavía

- No Gmail drafts.
- No HubSpot.

---

## Phase 8 - Gmail Drafts

### Objetivo

Crear borradores en Gmail para filas aprobadas.

### Entregables

- Gmail client.
- OAuth con scope mínimo.
- Endpoint o action `create_gmail_draft`.
- Escritura de `gmail_draft_id`.
- Idempotencia para evitar duplicados.

### Archivos Esperados

```text
app/integrations/gmail.py
docs/gmail_setup.md
tests/test_gmail_payload.py
```

### Scope Recomendado

```text
https://www.googleapis.com/auth/gmail.compose
```

### Validación Manual

1. Fila con `approved = TRUE`.
2. `action = create_gmail_draft`.
3. Procesar pendientes.
4. Confirmar draft en Gmail.
5. Confirmar `gmail_draft_id` en Sheet.

### Criterios De Éxito

- Crea draft.
- No envía.
- No duplica si ya existe draft.

### No Hacer Todavía

- No auto-send.
- No campañas.

---

## Phase 9 - Langfuse Tracing

### Objetivo

Agregar observabilidad LLM y trazabilidad por run/fila.

### Entregables

- Config Langfuse.
- Traces por run.
- Spans por node/tool.
- Metadata: `run_id`, `lead_id`, `action`, `quality_score`.
- Metadata adicional: `evidence_quality`, `personalization_depth`, `fit_score`.
- Scores de calidad como Langfuse scores cuando sea práctico.
- Docs de setup.

### Archivos Esperados

```text
app/core/langfuse.py
docs/langfuse_setup.md
tests/test_tracing_metadata.py
```

### Validación Manual

1. Ejecutar run de 2 filas.
2. Abrir Langfuse.
3. Confirmar traces con metadata correcta.

### Criterios De Éxito

- Se puede auditar por qué se generó un mensaje.
- Errores LLM quedan visibles.
- Token usage/latencia quedan registrados si proveedor lo permite.

---

## Phase 10 - Email Summary

### Objetivo

Enviar email automático al completar un run.

### Entregables

- Servicio de email summary.
- Template de resumen.
- Envío usando Gmail API o SMTP.
- Configurable por env.

### Archivos Esperados

```text
app/services/email_summary.py
app/templates/run_summary_email.txt
tests/test_email_summary_template.py
```

### Contenido

- run_id,
- sheet link,
- total procesadas,
- éxitos,
- errores,
- low evidence rows,
- drafts creados,
- links relevantes.

### Validación Manual

1. Procesar run.
2. Recibir email resumen.
3. Confirmar que incluye errores y links.

### Criterios De Éxito

- El vendedor sabe cuándo el agente terminó.
- No tiene que refrescar Sheets constantemente.

---

## Phase 11 - CSV Exports

### Objetivo

Exportar filas aprobadas a CSV compatible con Smartlead/Instantly.

### Entregables

- Export service.
- Endpoint export.
- Script CLI.
- Column mapping.

### Archivos Esperados

```text
app/services/export_service.py
scripts/export_smartlead_csv.py
scripts/export_instantly_csv.py
tests/test_csv_exports.py
```

### Validación

```bash
pytest tests/test_csv_exports.py
python scripts/export_smartlead_csv.py --fake
```

### Criterios De Éxito

- CSV incluye solo filas aprobadas/export_ready.
- Columnas son consistentes.
- No requiere API de Smartlead/Instantly.

---

## Phase 12 - HubSpot Adapter Opcional

### Objetivo

Permitir sincronizar contactos/notas/tareas a HubSpot para testear CRM real.

Esta fase es estrictamente opcional. No debe iniciarse hasta que el flujo Sheets -> revision -> Gmail draft -> email summary -> Langfuse funcione bien.

### Entregables

- HubSpot client.
- Adapter interface.
- Upsert company/contact.
- Create note.
- Create task.
- Docs de setup con free CRM.

### Archivos Esperados

```text
app/integrations/crm/base.py
app/integrations/crm/hubspot.py
docs/hubspot_setup.md
tests/test_hubspot_adapter_contract.py
```

### Validación Manual

1. Crear cuenta HubSpot Free.
2. Crear private app/token.
3. Procesar una fila.
4. Confirmar contacto y nota en HubSpot.

### Criterios De Éxito

- CRM es opcional.
- Sheets sigue funcionando sin CRM.
- Errores de CRM no rompen draft generation.

---

## Phase 13 - Hardening, Docs Y Demo

### Objetivo

Preparar el proyecto para ser usado como demo seria y base de implementación.

### Entregables

- README completo.
- Guía de setup.
- Guía de demo.
- Seed data.
- Playbook ejemplo.
- Sheet template.
- Error handling robusto.
- Screenshots opcionales.

### Archivos Esperados

```text
README.md
docs/demo_script.md
docs/setup.md
docs/sheet_template.md
examples/leads_demo.csv
examples/sales_playbook_demo.yaml
```

### Demo End-To-End

La demo debe mostrar:

1. Lead en Google Sheets.
2. Contexto manual pegado.
3. Botón "Procesar pendientes".
4. Draft generado.
5. Feedback del vendedor.
6. Draft revisado.
7. Aprobación.
8. Gmail draft creado.
9. Email resumen recibido.
10. Trace en Langfuse.

### Criterios De Éxito

- Demo completa en menos de 10 minutos.
- Setup reproducible.
- No hay pasos manuales ocultos.

---

## Checks Globales Antes De Pasar A Otra Fase

Antes de avanzar:

```bash
pytest
ruff check .
ruff format --check .
```

Además:

- No debe haber secretos hardcodeados.
- No debe haber auto-send.
- No debe haber scraping de LinkedIn.
- No debe haber frontend innecesario.
- No debe haber dependencia obligatoria de CRM.

---

## Orden Recomendado Para Una Sesión De Codex

Cuando una nueva sesión use este documento:

1. Leer `Revenue_Ops_Copilot_SPECS.md`.
2. Leer este archivo.
3. Identificar la fase actual.
4. Implementar solo esa fase.
5. Ejecutar validación de esa fase.
6. Actualizar README/docs mínimos si corresponde.
7. Reportar:
   - fase completada,
   - archivos modificados,
   - comandos ejecutados,
   - bloqueos,
   - siguiente fase recomendada.

---

## Fase Inicial Recomendada

La primera sesión de implementación debe empezar por:

```text
Phase 0 - Bootstrap Del Proyecto
```

No saltar directo a Google Sheets o LangGraph. Primero crear base limpia.

---

## Notas Para Desarrollo Agéntico

Para Codex:

- Mantener cambios pequeños.
- No implementar fases futuras por entusiasmo.
- Si una decisión no está clara, elegir la opción más simple alineada al spec.
- Preferir interfaces/protocols antes que acoplar APIs reales.
- Usar mocks/fakes antes de credenciales reales.
- Separar código determinístico de código LLM.
- Hacer tests alrededor de routing, estados y hashing.
- Mantener observabilidad desde que haya LLM real.
- Tratar Google Sheets como UI, no como base de datos confiable.
- Tratar Postgres como fuente operacional.
- Tratar Gmail como output revisable, no canal automático.

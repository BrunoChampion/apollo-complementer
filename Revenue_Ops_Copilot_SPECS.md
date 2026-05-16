# Revenue Ops Copilot - Especificaciones del Proyecto

**Autor:** Bruno Champion  
**Fecha:** Mayo 2026  
**Contexto:** Proyecto de aprendizaje y demostración comercial para agencia de IA enfocada en SMBs B2B de LATAM, especialmente empresas de 20 a 200 empleados.  
**Estado:** Especificación funcional y técnica para construir un MVP robusto, pragmático y vendible.

---

## 1. Resumen Ejecutivo

Revenue Ops Copilot es un sistema agéntico para equipos comerciales B2B que ayuda a investigar prospectos, priorizar cuentas, generar mensajes personalizados, revisar drafts con feedback humano, crear borradores en Gmail y registrar resultados en Google Sheets, con integración opcional a CRM y plataformas de outbound.

El objetivo no es construir un "AI SDR autónomo" que envía mensajes sin supervisión. El objetivo es construir un **copiloto comercial con human-in-the-loop** que aumente la calidad y velocidad del outbound, sin automatizar de forma riesgosa canales como LinkedIn ni enviar correos sin aprobación humana.

El sistema está diseñado para LATAM, donde muchas SMBs trabajan con una mezcla de Google Sheets, Gmail/Outlook, WhatsApp, CRMs parcialmente usados y procesos comerciales informales. Por eso el MVP evita una UI SaaS compleja y usa herramientas existentes: Google Sheets como interfaz operativa, Gmail Drafts como mecanismo de salida y FastAPI/LangGraph como motor agéntico.

---

## 2. Problema Que Resuelve

Muchas empresas B2B pequeñas y medianas tienen problemas comerciales repetidos:

- Hacen outbound genérico que no convierte.
- Los vendedores investigan prospectos manualmente y pierden mucho tiempo.
- La personalización real toma demasiado esfuerzo.
- El seguimiento comercial es inconsistente.
- El CRM, si existe, está incompleto o mal actualizado.
- El conocimiento comercial vive en la cabeza del founder o del mejor vendedor.
- La empresa no tiene un proceso sistemático para aprender qué mensajes, industrias o ángulos convierten.

El problema central no es solo "escribir mejores emails". El problema es convertir información dispersa sobre prospectos, ICP, oferta, casos de éxito, objeciones y señales de mercado en mensajes comerciales relevantes, revisables y medibles.

---

## 3. Principio De Producto

El sistema debe seguir esta tesis:

> Revenue Ops Copilot no reemplaza al vendedor. Convierte a un vendedor o founder en alguien con research, memoria, priorización y follow-up de un equipo comercial más grande.

El sistema debe:

- Ahorrar tiempo de research.
- Mejorar la calidad de personalización.
- Priorizar cuentas con mayor probabilidad de fit.
- Crear drafts listos para revisión humana.
- Permitir que el vendedor corrija y mejore los mensajes.
- Aprender de feedback y resultados.
- Mantener trazabilidad de fuentes, decisiones y outputs.
- Evitar scraping prohibido, especialmente en LinkedIn.
- Evitar auto-send en el MVP.

---

## 4. Alcance Del MVP

### 4.1 En Alcance

- Backend en Python + FastAPI.
- Google Sheets como UI principal.
- Playbook comercial en YAML.
- Postgres como base de datos operacional.
- LangGraph para orquestación agéntica.
- Langfuse para observabilidad.
- Gmail API para crear borradores, no enviar correos.
- Procesamiento bajo demanda desde Google Sheets mediante Apps Script.
- Runs asíncronos: Apps Script inicia el run y recibe `run_id` rápido; el backend procesa en background y avisa por email.
- Procesamiento batch programado para tareas no urgentes.
- Email automático de resumen al finalizar un run.
- Extracción estructurada de contexto manual pegado por el vendedor.
- Feedback loop para revisar mensajes.
- Tracking explícito de evidencia usada para research, scoring y drafts.
- Guardrails básicos contra prompt injection y outputs inseguros.
- Export CSV para Smartlead/Instantly.
- API adapters opcionales para Smartlead/Instantly en versión posterior.
- CRM adapter opcional para HubSpot en una fase posterior, con diseño extensible a Zoho/Pipedrive.

### 4.2 Fuera De Alcance Para MVP

- Frontend completo en Next.js.
- SaaS multi-tenant.
- Auto-send de emails.
- Automatización de LinkedIn.
- Scraping de LinkedIn.
- WhatsApp como UI principal.
- WhatsApp Business Platform API.
- Secuencias outbound complejas.
- Enriquecimiento pago obligatorio.
- Automatización agresiva de conexión/mensajes.
- Multiusuario avanzado con permisos complejos.
- Facturación/subscripciones.
- Deployment enterprise multi-tenant.
- CRM obligatorio para que el MVP funcione.
- Procesamiento masivo sin límites de batch/costo.

---

## 5. Decisiones Estratégicas Ya Tomadas

### 5.1 No Construir SaaS Desde El Inicio

El MVP debe funcionar como sistema interno/servicio implementable sobre el stack existente del cliente. Google Sheets y Gmail son la UI inicial.

Motivo:

- Menos desarrollo frontend.
- Menos fricción para clientes LATAM.
- Más fácil vender como implementación.
- Más rápido validar valor.
- Permite iterar sin diseñar producto completo.

### 5.2 No Depender De LinkedIn

LinkedIn prohíbe bots, crawlers, scraping y automatización no autorizada. El sistema no debe acceder automáticamente a LinkedIn, ni scrapear perfiles, ni automatizar mensajes.

El sistema sí puede usar contexto manual provisto por el vendedor:

- Texto copiado manualmente del perfil.
- Texto copiado manualmente de posts.
- Notas escritas por el vendedor.
- URL de referencia para trazabilidad.

Esto mantiene al humano en control y evita que la arquitectura dependa de scraping prohibido.

### 5.3 Gmail Drafts, No Auto-Send

El sistema debe crear borradores en Gmail, pero no enviarlos automáticamente.

Motivo:

- Reduce riesgo de spam.
- Mantiene aprobación humana.
- Evita quemar dominios.
- Facilita testing con clientes.
- Es más aceptable para SMBs.

### 5.4 Google Sheets Como Interfaz Operativa

Google Sheets será la UI principal del vendedor.

Motivo:

- Es familiar.
- Permite edición manual.
- Tiene formato condicional.
- Permite Apps Script.
- Exporta CSV.
- Es suficiente para MVP.

### 5.5 Playbook En YAML, No Vector DB Por Defecto

ICP, propuesta de valor, casos de éxito cortos, objeciones y tonos deben vivir en YAML estructurado, no en vector DB.

Motivo:

- Son datos pequeños, críticos y estructurados.
- Deben ser determinísticos.
- Es mejor inyectarlos como contexto canónico.
- RAG es innecesario para información compacta.

La vector DB solo se considera para corpus largo/no estructurado: llamadas transcritas, emails históricos, documentos extensos, casos largos o propuestas antiguas.

### 5.6 Langfuse Como Observabilidad

Usar Langfuse por ser open-source, integrable con LangChain/LangGraph y adecuado para self-hosting futuro.

---

## 6. Usuarios Objetivo

### 6.1 Usuario Primario

Vendedor, founder, account executive o responsable comercial de una empresa B2B pequeña o mediana.

### 6.2 Usuario Secundario

Administrador interno o consultor implementador, inicialmente Bruno, que configura playbooks, credenciales, integraciones, runs y debugging.

### 6.3 Cliente Ideal Para El Sistema

Empresas B2B LATAM con:

- 20 a 200 empleados.
- Ticket medio suficientemente alto para justificar outbound personalizado.
- Ciclo comercial consultivo.
- Founder o equipo comercial pequeño.
- Uso de Gmail/Google Workspace.
- Prospección activa o intención de iniciar prospección.
- Algún CRM o Google Sheets como CRM informal.

Ejemplos:

- Consultoras tecnológicas.
- Agencias B2B.
- Empresas de software B2B.
- Implementadoras ERP/CRM.
- Consultoras de ciberseguridad.
- Empresas de capacitación corporativa.
- Servicios profesionales de alto ticket.
- Proveedores B2B para retail, salud, educación, logística o finanzas.

---

## 7. Flujo General Del Sistema

### 7.1 Flujo De Research Y Draft Inicial

1. El vendedor agrega leads en Google Sheets.
2. Cada fila contiene datos mínimos: empresa, website, persona, cargo, email, país, source.
3. El vendedor marca `action = research_and_draft`.
4. El vendedor hace clic en un botón de Google Sheets: "Procesar pendientes".
5. Apps Script llama a FastAPI.
6. FastAPI crea un `run_id`.
7. FastAPI responde rápido con `run_id` y `status = queued`.
8. Un worker/background task busca filas pendientes.
9. El sistema bloquea cada fila con `run_id`, `locked_at` y `status = processing`.
10. LangGraph ejecuta el flujo agéntico:
   - valida datos mínimos,
   - obtiene contexto de empresa,
   - procesa contexto manual,
   - extrae evidence items,
   - calcula fit score,
   - genera hipótesis de dolor,
   - genera draft,
   - evalúa calidad/genericidad,
   - escribe resultados.
11. El sistema actualiza Google Sheets.
12. El sistema registra run y trazas en Postgres/Langfuse.
13. El sistema envía email resumen al vendedor.

### 7.2 Flujo De Revisión

1. El vendedor revisa `email_draft` o `linkedin_draft`.
2. Si quiere mejorar algo, escribe en `revision_instruction`.
3. Marca `action = revise`.
4. Hace clic en "Procesar pendientes".
5. El agente detecta que la fila requiere revisión.
6. El agente reescribe usando:
   - draft previo,
   - feedback del vendedor,
   - playbook,
   - contexto manual,
   - research ya existente.
7. Escribe `revised_draft`.
8. Actualiza `agent_note`.
9. Cambia `status = revised`.
10. Envía email resumen del run.

### 7.3 Flujo De Gmail Draft

1. El vendedor aprueba una fila.
2. Marca `action = create_gmail_draft`.
3. El sistema crea un borrador en Gmail usando Gmail API.
4. Escribe `gmail_draft_id` y, si es posible, `gmail_draft_url`.
5. Cambia `status = gmail_draft_created`.
6. El vendedor abre Gmail, revisa y envía manualmente.

### 7.4 Flujo De Export CSV

1. El vendedor filtra filas aprobadas.
2. El sistema o Sheets exporta CSV con columnas compatibles con Smartlead/Instantly.
3. En MVP, la carga puede hacerse manualmente.
4. En v2, se puede usar API.

---

## 8. Canales E Interfaces

### 8.1 UI Principal: Google Sheets

Google Sheets será la superficie diaria del vendedor.

Debe incluir:

- filas de leads/prospectos,
- columnas de control,
- columnas de contexto,
- columnas de output,
- formato condicional,
- botones Apps Script,
- filtros/vistas.

### 8.2 Gmail

Gmail se usa para borradores.

El sistema no enviará emails automáticamente.

### 8.3 Email Automático De Resumen

Al finalizar un run, el sistema enviará un email al usuario/admin con:

- run_id,
- número de filas procesadas,
- número de éxitos,
- número de errores,
- filas con drafts creados,
- filas revisadas,
- filas con baja confianza,
- link a Google Sheet,
- resumen de errores.

### 8.4 CLI / Script Programado

El CLI no es la UI del vendedor. Es una herramienta para:

- administración,
- debugging,
- ejecución local,
- cron,
- batch jobs,
- testing.

Ejemplos:

```bash
python scripts/run_pending.py --sheet-id SHEET_ID
python scripts/run_daily_batch.py
python scripts/export_smartlead_csv.py --run-id RUN_ID
```

### 8.5 WhatsApp

WhatsApp es relevante en LATAM, pero no será UI principal en MVP.

Puede considerarse en v2 para:

- notificaciones internas,
- alertas de drafts listos,
- resúmenes diarios,
- interacción simple tipo "aprobar/revisar".

No se debe implementar WhatsApp en v1 porque:

- requiere WhatsApp Business Platform/Cloud API,
- agrega costos y configuración,
- puede requerir plantillas,
- aumenta complejidad operativa,
- no es necesario para validar valor.

---

## 9. Arquitectura Técnica

### 9.1 Stack Principal

- Lenguaje: Python 3.11+
- API backend: FastAPI
- Orquestación agente: LangGraph
- Observabilidad LLM: Langfuse
- Base de datos: Postgres
- UI operativa: Google Sheets
- Automatización Sheets: Google Apps Script
- Email drafts: Gmail API
- Configuración comercial: YAML
- Validación: Pydantic
- Logging: structlog o logging JSON
- Tests: pytest
- Lint/format: ruff

### 9.2 Componentes

```text
Google Sheets
    |
    | Apps Script button / scheduled trigger
    v
FastAPI
    |
    | creates run_id
    v
Run Orchestrator
    |
    v
LangGraph Agent
    |         |          |          |
    |         |          |          |
Research   Scoring    Drafting   Revision
Tools      Tools      Tools      Tools
    |
    v
Postgres + Google Sheets + Gmail Drafts + Langfuse
```

### 9.3 FastAPI Endpoints

MVP endpoints:

```http
GET /health
POST /runs
POST /runs/{run_id}/process
POST /runs/process-row
GET /runs/{run_id}
POST /exports/smartlead-csv
POST /exports/instantly-csv
```

`POST /runs` debe crear el run y devolver rápido. El procesamiento puede ejecutarse con FastAPI `BackgroundTasks` en MVP local, o con un worker simple basado en Postgres cuando el sistema crezca.

Optional later:

```http
POST /crm/hubspot/sync
POST /gmail/create-draft
POST /webhooks/gmail
POST /webhooks/smartlead
```

### 9.4 Why FastAPI If Sheets Is UI?

FastAPI provides:

- stable API for Apps Script,
- separation between UI and engine,
- easy deployment,
- webhooks later,
- CRM/email integrations,
- easier testing,
- future frontend compatibility.

---

## 10. Google Sheets Specification

### 10.1 Sheet Name

Recommended workbook tabs:

- `Leads`
- `Runs`
- `Config`
- `Exports`

The MVP can start with only `Leads`.

### 10.2 Leads Tab Columns

La Sheet debe tener una versión MVP visible y una versión avanzada/oculta. La prioridad es que el vendedor no sienta que está operando un ERP.

#### MVP Visible Columns

Estas columnas deben bastar para una demo y primer uso real:

```text
lead_id
company_name
company_website
prospect_name
prospect_title
prospect_email
manual_context
action
status
fit_score
evidence_quality
message_angle
email_subject
email_draft
revision_instruction
revised_draft
approved
gmail_draft_url
agent_note
error_message
```

#### Advanced / Hidden Columns

Estas columnas pueden existir, pero deben estar ocultas o reservarse para versiones posteriores.

Required input columns:

```text
lead_id
company_name
company_website
country
industry
prospect_name
prospect_title
prospect_email
source
action
status
```

Optional context columns:

```text
company_description
manual_company_context
manual_person_context
manual_linkedin_notes
source_url
context_added_by
context_added_at
existing_relationship_notes
crm_contact_id
crm_company_id
```

Research/output columns:

```text
research_summary
company_offering
target_customer
business_model
detected_signals
likely_pains
fit_score
fit_score_reason
evidence_quality
personalization_depth
message_angle
email_subject
email_draft
linkedin_draft
quality_score
quality_issues
agent_note
```

Revision columns:

```text
revision_instruction
revision_instruction_hash
last_processed_revision_hash
revised_subject
revised_draft
revision_count
```

Approval/output columns:

```text
approved
final_subject
final_message
gmail_draft_id
gmail_draft_url
export_ready
sent_at
reply_status
reply_notes
```

Operational columns:

```text
run_id
locked_at
processed_at
error_message
last_updated_by_agent_at
```

Evidence columns:

```text
evidence_items_json
source_urls
personalization_depth
unsupported_claims
```

### 10.3 Action Values

Valid `action` values:

```text
research
draft
research_and_draft
revise
create_gmail_draft
export
skip
```

Recommended MVP actions:

- `research_and_draft`
- `revise`
- `create_gmail_draft`
- `skip`

### 10.4 Status Values

Valid `status` values:

```text
new
queued
processing
researched
drafted
needs_revision
revised
approved
gmail_draft_created
exported
sent
error
skipped
```

### 10.5 Row Processing Rules

The system processes rows based on `action` and `status`.

Initial draft:

```text
action IN ("research", "draft", "research_and_draft")
AND status NOT IN ("processing", "approved", "sent")
```

Revision:

```text
action = "revise"
AND revision_instruction IS NOT EMPTY
AND revision_instruction_hash != last_processed_revision_hash
AND status IN ("drafted", "needs_revision", "revised", "error")
```

Gmail draft:

```text
action = "create_gmail_draft"
AND approved = TRUE
AND final_message IS NOT EMPTY
AND status IN ("approved", "revised", "drafted")
```

### 10.6 Hash-Based Revision Detection

Use a stable hash of `revision_instruction`.

When a revision is processed:

```text
last_processed_revision_hash = revision_instruction_hash
revision_count += 1
status = "revised"
action = ""
```

If the seller edits `revision_instruction`, hash changes. The system can process again after `action = revise`.

### 10.7 Formatting

Use conditional formatting:

- `processing`: blue
- `drafted`: light green
- `needs_revision`: yellow
- `revised`: green
- `gmail_draft_created`: dark green
- `error`: red
- `low evidence_quality`: orange
- `quality_score < threshold`: orange/red

---

## 11. Playbook YAML

### 11.1 Purpose

The playbook is the canonical commercial context. It should be structured and deterministic.

It should not be retrieved via vector search by default.

### 11.2 File Location

```text
config/sales_playbook.yaml
```

### 11.3 Example Structure

```yaml
company:
  name: "Example Client"
  description: "B2B consulting firm helping mid-market companies implement ERP."
  website: "https://example.com"

icp:
  company_size: "20-200 employees"
  regions:
    - Peru
    - Chile
    - Colombia
    - Mexico
  industries:
    - B2B services
    - technology consulting
    - cybersecurity
    - ERP implementation
  exclusions:
    - companies with no B2B sales motion
    - microbusinesses under 10 employees

buyer_personas:
  - title_patterns:
      - CEO
      - Founder
      - Managing Partner
    priorities:
      - revenue growth
      - operational leverage
      - predictable pipeline
    tone: "strategic, concise, peer-to-peer"
  - title_patterns:
      - Head of Sales
      - Commercial Manager
      - Sales Director
    priorities:
      - qualified meetings
      - follow-up consistency
      - sales productivity
    tone: "practical, metric-oriented"

value_props:
  - id: "research_speed"
    pain: "manual prospect research consumes too much time"
    outcome: "reduce research time while improving relevance"
    proof: "system creates account dossiers and drafts for human review"
  - id: "followup_consistency"
    pain: "sales follow-up is inconsistent"
    outcome: "increase disciplined follow-up without hiring more SDRs"

case_studies:
  - id: "case_001"
    title: "Corporate RAG agent implementation"
    summary: "Implemented an AI agent/RAG workflow for a corporate client."
    result: "USD 7k project, 4-month implementation"
    use_when:
      - "prospect asks for credibility"
      - "AI implementation relevance is high"

objections:
  - objection: "We already use a CRM"
    response: "This does not replace the CRM; it improves research, prioritization and draft creation around it."
  - objection: "We do not want spam"
    response: "The system creates drafts for review. It does not auto-send."

message_rules:
  max_words_email: 120
  max_words_linkedin: 80
  avoid_phrases:
    - "I hope this email finds you well"
    - "revolutionize your business"
    - "unlock the power of AI"
  required_traits:
    - concise
    - specific
    - human
    - low hype
  call_to_action_examples:
    - "¿Tiene sentido conversar 15 minutos?"
    - "¿Vale la pena explorarlo?"
    - "¿Te parece si te mando una idea más concreta?"
```

---

## 12. LangGraph Design

### 12.1 Why LangGraph

LangGraph is needed because the workflow has explicit states and multiple possible paths:

- research,
- scoring,
- drafting,
- quality evaluation,
- revision,
- Gmail draft creation,
- error handling.

This is more complex than a single `create_agent` call.

### 12.1.1 Persistence And Durable Execution

Use a LangGraph checkpointer once Postgres persistence exists.

Recommended:

```text
thread_id = "{run_id}:{lead_id}"
```

Why:

- resume interrupted row processing,
- inspect previous graph state,
- avoid repeating expensive LLM work,
- support human-in-the-loop patterns later,
- improve debugging.

Side effects must be idempotent and should not be repeated on replay. API calls that create external objects, such as Gmail drafts or CRM notes, must check existing IDs before executing.

### 12.2 State Object

Recommended Pydantic/LangGraph state:

```python
class LeadState(BaseModel):
    run_id: str
    lead_id: str
    row_number: int
    action: str
    status: str

    company_name: str | None = None
    company_website: str | None = None
    country: str | None = None
    industry: str | None = None
    prospect_name: str | None = None
    prospect_title: str | None = None
    prospect_email: str | None = None

    manual_company_context: str | None = None
    manual_person_context: str | None = None
    manual_linkedin_notes: str | None = None
    existing_relationship_notes: str | None = None

    playbook: dict
    research_summary: str | None = None
    structured_context: dict | None = None
    detected_signals: list[str] = []
    evidence_items: list[dict] = []
    likely_pains: list[str] = []
    fit_score: int | None = None
    fit_score_reason: str | None = None
    evidence_quality: str | None = None
    personalization_depth: str | None = None
    message_angle: str | None = None

    email_subject: str | None = None
    email_draft: str | None = None
    linkedin_draft: str | None = None

    revision_instruction: str | None = None
    revised_subject: str | None = None
    revised_draft: str | None = None
    revision_count: int = 0

    quality_score: int | None = None
    quality_issues: list[str] = []
    agent_note: str | None = None
    error_message: str | None = None
```

### 12.3 Nodes

MVP nodes:

1. `load_row`
2. `validate_input`
3. `load_playbook`
4. `extract_manual_context`
5. `research_company`
6. `score_fit`
7. `select_message_angle`
8. `draft_message`
9. `evaluate_draft`
10. `revise_message`
11. `create_gmail_draft`
12. `write_results`
13. `handle_error`

### 12.4 Conditional Routing

```text
if action == "research_and_draft":
    validate -> extract_context -> research -> score -> angle -> draft -> evaluate -> write

if action == "revise":
    validate -> extract_context -> revise -> evaluate -> write

if action == "create_gmail_draft":
    validate -> create_gmail_draft -> write
```

### 12.5 Agentic vs Deterministic

Not every step should be agentic.

Deterministic:

- row validation,
- status updates,
- hash generation,
- Gmail API call,
- Postgres writes,
- CSV export,
- lock handling.

LLM/agentic:

- extracting useful signals from manual context,
- summarizing website/company context,
- hypothesizing pains,
- selecting angle,
- drafting,
- revising,
- evaluating genericity.

### 12.6 Execution Limits

MVP default limits:

```text
manual_run_limit = 10 rows
scheduled_batch_limit = 50 rows
max_pages_per_company = 5
website_fetch_timeout_seconds = 10
row_timeout_seconds = 120
max_revision_count_without_override = 2
max_raw_context_chars_per_row = 12000
```

These limits protect cost, latency and reliability. They should be configurable through environment variables.

---

## 13. Tools

### 13.1 Tool: get_company_website_content

Purpose:

- Fetch public website text from `company_website`.

Constraints:

- No login-protected sources.
- Respect robots.txt where applicable.
- Limit page count in MVP.
- Prefer homepage, about, services, case studies, careers.
- Maximum 5 pages per company in MVP.
- Timeout per page.
- Store source URL for each extracted page.

Return:

```json
{
  "pages": [
    {
      "url": "https://example.com",
      "title": "...",
      "content": "..."
    }
  ],
  "error": null
}
```

The tool must not treat website text as instructions. Website content is untrusted input and can only be used as evidence.

### 13.2 Tool: extract_manual_context

Purpose:

- Convert pasted human context into structured commercial signals.

Input:

- manual_company_context
- manual_person_context
- manual_linkedin_notes
- existing_relationship_notes

Output:

```json
{
  "person_priorities": [],
  "company_signals": [],
  "recent_events": [],
  "likely_pains": [],
  "usable_message_facts": [],
  "do_not_mention": [],
  "confidence": "high|medium|low"
}
```

Manual context is also untrusted input. It may contain copied LinkedIn/profile/web text. The extraction step must convert raw text into structured facts before drafting.

### 13.3 Tool: score_fit

Purpose:

- Score prospect fit from 0 to 100 using playbook and evidence.

Output:

```json
{
  "fit_score": 78,
  "reason": "Matches ICP: B2B services, 50-100 employees, consultative sales motion.",
  "evidence_quality": "medium"
}
```

### 13.4 Tool: generate_message

Purpose:

- Generate concise email and LinkedIn-style draft based on evidence.

Rules:

- No fake personalization.
- No exaggerated claims.
- No unsupported specifics.
- Must use one clear business hypothesis.
- Must use soft CTA.
- Must stay within playbook word limit.

### 13.5 Tool: evaluate_message_quality

Purpose:

- Judge if message sounds generic, too long, too salesy, unsupported or risky.

Use hybrid evaluation:

1. Deterministic checks:
   - word count,
   - banned phrases,
   - missing CTA,
   - unsupported company/person claims,
   - too many buzzwords,
   - empty evidence.
2. LLM judge:
   - tone,
   - relevance,
   - human quality,
   - genericity.

Output:

```json
{
  "quality_score": 82,
  "issues": ["CTA could be softer"],
  "genericity_risk": "low",
  "unsupported_claims": [],
  "recommendation": "approve|revise"
}
```

### 13.8 Tool: extract_evidence_items

Purpose:

- Convert research/manual context into explicit evidence items that can be traced.

Output:

```json
{
  "evidence_items": [
    {
      "claim": "The company offers ERP implementation services for mid-market clients.",
      "source_type": "website|manual|crm|enrichment",
      "source_url": "https://example.com/services",
      "confidence": "high|medium|low",
      "used_in_message": false
    }
  ]
}
```

Messages should be based only on evidence items or clearly marked business hypotheses. The system must not present a hypothesis as a fact.

### 13.6 Tool: revise_message

Purpose:

- Apply seller feedback to an existing draft.

Input:

- previous draft,
- revision instruction,
- playbook,
- context,
- quality issues.

Output:

- revised subject,
- revised draft,
- agent note.

### 13.7 Tool: create_gmail_draft

Purpose:

- Create Gmail draft but not send.

Inputs:

- recipient email,
- subject,
- body.

Return:

```json
{
  "gmail_draft_id": "...",
  "gmail_draft_url": "...",
  "status": "created"
}
```

---

## 14. Personalization Strategy

### 14.1 No Fake Hyperpersonalization

The system must never invent signals.

Bad:

```text
Vi que están creciendo rápidamente...
```

unless growth is supported by evidence.

Better:

```text
Por lo que vi en su sitio, trabajan con implementaciones consultivas para empresas medianas. En ese tipo de venta, el cuello de botella suele ser convertir conversaciones iniciales en propuestas y follow-ups consistentes.
```

### 14.2 Personalization Depth

Use one of:

```text
company_level
persona_level
weak
```

Definitions:

- `persona_level`: there is specific person context provided manually or via authorized enrichment.
- `company_level`: there is meaningful company context but little person-specific info.
- `weak`: little evidence; message must be more general and conservative.

### 14.3 Evidence Quality

Use one of:

```text
high
medium
low
```

The system should flag low evidence rows for human review.

### 14.4 Manual Context

Sellers can paste:

- LinkedIn profile text,
- LinkedIn company page text,
- posts,
- website snippets,
- event descriptions,
- notes from calls,
- personal observations.

The system must treat this as user-provided context and extract signals before drafting.

### 14.5 Two Modes For Manual Context

Quick note:

```text
Están contratando SDRs y expandiendo a Chile.
```

Full context:

```text
Pasted profile, company about, recent post, job description, etc.
```

The system should support both.

---

## 15. Message Guidelines

### 15.1 Email Draft

Recommended structure:

1. Specific observation or business context.
2. Plausible pain/hypothesis.
3. Relevant value angle.
4. Soft CTA.

Length:

- 70 to 120 words.

Tone:

- human,
- concise,
- low hype,
- professional,
- LATAM Spanish by default,
- can support English later.

### 15.2 LinkedIn Draft

This is only a draft for manual use. The system must not send via LinkedIn.

Length:

- 40 to 80 words.

### 15.3 Avoid

- "Espero que estés bien"
- "Revolucionar"
- "Desbloquear el poder de la IA"
- "Solución integral"
- "Te escribo porque vi tu perfil"
- Overly long intros.
- Unsupported claims.
- Fake familiarity.

### 15.4 CTA Examples

```text
¿Tiene sentido conversar 15 minutos?
¿Vale la pena explorarlo?
¿Te parece si te mando una idea más concreta?
¿Sería relevante para ustedes?
```

---

## 16. Postgres Schema

### 16.1 Tables

#### runs

```sql
CREATE TABLE runs (
    id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    sheet_id TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    total_rows INT DEFAULT 0,
    success_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    created_by TEXT,
    summary JSONB
);
```

#### lead_runs

```sql
CREATE TABLE lead_runs (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES runs(id),
    lead_id TEXT NOT NULL,
    row_number INT,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT now(),
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    input_snapshot JSONB,
    output_snapshot JSONB
);
```

#### prospects

```sql
CREATE TABLE prospects (
    lead_id TEXT PRIMARY KEY,
    company_name TEXT,
    company_website TEXT,
    prospect_name TEXT,
    prospect_title TEXT,
    prospect_email TEXT,
    country TEXT,
    industry TEXT,
    crm_contact_id TEXT,
    crm_company_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

#### messages

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    lead_id TEXT REFERENCES prospects(lead_id),
    run_id UUID REFERENCES runs(id),
    message_type TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    quality_score INT,
    quality_issues JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### gmail_drafts

```sql
CREATE TABLE gmail_drafts (
    id UUID PRIMARY KEY,
    lead_id TEXT REFERENCES prospects(lead_id),
    message_id UUID REFERENCES messages(id),
    gmail_draft_id TEXT NOT NULL,
    gmail_draft_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### evidence_items

```sql
CREATE TABLE evidence_items (
    id UUID PRIMARY KEY,
    lead_run_id UUID REFERENCES lead_runs(id),
    lead_id TEXT NOT NULL,
    claim TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT,
    confidence TEXT NOT NULL,
    used_in_message BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 16.2 Why Postgres If Sheets Stores Data?

Postgres stores:

- run history,
- traces of row processing,
- snapshots,
- errors,
- message versions,
- future CRM sync state.

Google Sheets remains the human-facing UI, but Postgres is the reliable operational store.

For MVP, Postgres is also the control plane for async runs:

- queued/running/completed/failed run state,
- row locks,
- retries,
- idempotency records,
- evidence snapshots.

---

## 17. Google Apps Script

### 17.1 Purpose

Apps Script provides buttons in Google Sheets to call FastAPI.

### 17.2 Buttons

Recommended menu:

```text
Revenue Copilot
  - Procesar pendientes
  - Crear borradores Gmail aprobados
  - Exportar CSV
  - Ver último resumen
```

### 17.3 Apps Script Behavior

When user clicks "Procesar pendientes":

1. Get current spreadsheet ID.
2. Call `POST /runs`.
3. Pass sheet ID and tab name.
4. Receive `run_id`.
5. Show toast: "Procesamiento iniciado: {run_id}".
6. Backend processes asynchronously.
7. Backend sends summary email when done.

Apps Script must not wait for LLM processing to finish. This avoids Apps Script runtime limits and keeps the UX responsive.

### 17.4 Auth

MVP can use a shared secret header:

```http
X-Revenue-Copilot-Secret: ...
```

Later:

- OAuth,
- service account,
- per-client API keys.

---

## 18. Gmail API

### 18.1 Required Behavior

The system must create drafts only.

### 18.2 OAuth

Use Google OAuth for Gmail account authorization.

Scopes should be minimal:

```text
https://www.googleapis.com/auth/gmail.compose
```

This allows creating and managing drafts, not full mailbox access.

### 18.3 Draft Creation

Use Gmail API:

```text
users.drafts.create
```

### 18.4 Safety

Never call Gmail send endpoints in MVP.

---

## 19. CRM Adapter

### 19.1 Purpose

CRM adapter lets the system sync prospect information and notes into an existing CRM.

### 19.2 Initial Adapter: HubSpot

HubSpot is recommended first because:

- it has a free CRM plan,
- has serious APIs,
- is known in LATAM,
- is good for testing personally,
- integrates with Gmail and sales workflows.

### 19.3 Other CRMs

Later:

- Zoho CRM: free edition exists and relevant in LATAM.
- Pipedrive: common but no permanent free plan, only trial.
- Bitrix24: free plan but heavier UX.
- Kommo: relevant in WhatsApp-heavy LATAM sales teams.

### 19.4 Adapter Interface

Define abstract interface:

```python
class CRMAdapter(Protocol):
    def upsert_company(self, company: CompanyRecord) -> CRMResult: ...
    def upsert_contact(self, contact: ContactRecord) -> CRMResult: ...
    def create_note(self, contact_id: str, note: str) -> CRMResult: ...
    def create_task(self, contact_id: str, task: TaskRecord) -> CRMResult: ...
```

### 19.5 MVP CRM Scope

MVP should not depend on CRM.

Initial CRM support can be:

- optional HubSpot sync,
- create/update contact,
- create note with research summary,
- create task: "Review AI-generated draft".

---

## 20. Smartlead / Instantly / Apollo

### 20.1 MVP

Export CSV only.

### 20.2 CSV Columns

For outbound tools:

```text
email
first_name
last_name
company_name
company_website
job_title
country
custom_intro
pain_hypothesis
message_angle
email_subject
email_body
```

### 20.3 API Later

Smartlead:

- create campaign,
- add leads to campaign.

Instantly:

- add leads to campaign/list.

Apollo:

- enrich people/company,
- add contacts to sequence depending on plan and API permissions.

### 20.4 Safety

Do not integrate sending automation until message quality and approval process is validated.

---

## 21. Observability With Langfuse

### 21.1 What To Trace

Trace:

- each run,
- each row,
- each LangGraph node,
- prompts,
- model outputs,
- tool calls,
- token usage,
- latency,
- quality scores,
- errors.

### 21.2 Metadata

Attach:

```json
{
  "run_id": "...",
  "lead_id": "...",
  "action": "research_and_draft",
  "company_name": "...",
  "evidence_quality": "medium",
  "quality_score": 82
}
```

### 21.3 Why This Matters

Observability is needed because sellers will ask:

- why did the agent write this?
- what source did it use?
- why did it score this lead highly?
- where did it fail?
- which prompts are producing generic messages?

---

## 22. Email Summary

### 22.1 Trigger

Send email when:

- run completes,
- run fails,
- batch finishes,
- Gmail drafts created.

### 22.2 Content

Subject:

```text
Revenue Copilot: 12 filas procesadas, 10 OK, 2 errores
```

Body:

```text
Run ID: ...
Sheet: ...
Started: ...
Finished: ...

Processed:
- Research + draft: 8
- Revisions: 3
- Gmail drafts: 1

Needs review:
- 3 low evidence rows
- 2 quality score < 70

Errors:
- Row 14: missing prospect_email
- Row 22: website fetch failed

Link:
https://docs.google.com/spreadsheets/...
```

---

## 23. Error Handling

### 23.1 Row-Level Errors

A failure on one row must not fail the whole run.

On row failure:

- set `status = error`,
- write `error_message`,
- record in Postgres,
- continue next row.

### 23.2 Run-Level Errors

If the run itself fails:

- mark run as failed,
- send email summary,
- preserve logs/traces.

### 23.3 Common Errors

- missing company name,
- missing website,
- missing email for Gmail draft,
- invalid action,
- Gmail auth expired,
- Google Sheets API error,
- website fetch timeout,
- LLM timeout,
- malformed model output.

---

## 24. Locking And Idempotency

### 24.1 Why Needed

If user clicks button twice, two processes may try to process same row.

### 24.2 Sheet-Level Lock

Use `locked_at` and `run_id`.

Before processing:

```text
if status != "processing" and locked_at is empty or expired:
    set status = "processing"
    set locked_at = now
    set run_id = current_run_id
```

### 24.3 Lock Expiry

If `locked_at` older than 30 minutes and status is `processing`, allow recovery.

### 24.4 Idempotent Gmail Drafts

Before creating Gmail draft:

- check if `gmail_draft_id` exists.
- if exists, do not create duplicate unless `force_create = true`.

---

## 25. Security

### 25.1 Secrets

Use environment variables:

```text
DATABASE_URL
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REFRESH_TOKEN
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
LANGFUSE_HOST
APPS_SCRIPT_SHARED_SECRET
HUBSPOT_PRIVATE_APP_TOKEN
```

### 25.2 Principle Of Least Privilege

- Gmail scope should be compose/drafts only.
- Google Sheets access should be limited to target spreadsheet when possible.
- CRM token should have minimal required scopes.

### 25.3 Data Sensitivity

Prospect data may include personal data.

Store only what is needed.

Avoid storing personal emails/phones unless necessary.

### 25.4 No LinkedIn Automation

Explicit rule:

- no LinkedIn scraping,
- no LinkedIn automated login,
- no automated connection requests,
- no automated LinkedIn messaging,
- no browser automation against LinkedIn.

### 25.5 Prompt Injection And Untrusted Content

Website text, pasted LinkedIn/profile text, manual notes and CRM notes must be treated as untrusted content.

Rules:

- Never let external content override system/developer instructions.
- Do not pass large raw external content directly into final drafting prompts when structured evidence is available.
- Extract facts first, then draft from facts.
- Keep source URLs and confidence for important claims.
- Reject or flag content that appears to instruct the model to ignore rules, reveal prompts or perform unrelated actions.
- Run output checks before writing final drafts.

---

## 26. Compliance And Ethics

### 26.1 Consent And Outreach

The system helps draft messages; the client remains responsible for lawful outreach.

### 26.2 Avoid Dark Patterns

Messages should not pretend:

- prior relationship,
- fake familiarity,
- false trigger event,
- fake referral,
- fake urgency.

### 26.3 Human Approval

Every outbound message must be reviewed by a human before sending in MVP.

---

## 27. Model Strategy

### 27.1 Recommended

Use a strong model for:

- final drafting,
- revision,
- quality evaluation.

Use cheaper/faster model for:

- classification,
- extraction,
- scoring.

### 27.2 Provider Flexibility

Support one provider first. Recommended:

- OpenAI for simplicity, structured outputs and reliability.

Later:

- Anthropic,
- Gemini,
- local models if needed.

### 27.3 Structured Outputs

Use Pydantic/JSON schema for:

- extracted context,
- fit score,
- quality evaluation.

Free-form only for final message text.

---

## 28. Evaluation

### 28.1 Automated Checks

Evaluate drafts for:

- word count,
- genericity,
- unsupported claims,
- CTA quality,
- tone,
- evidence alignment,
- overhype,
- personalization depth.

Automated evaluation must be hybrid:

- deterministic checks first,
- LLM judge second.

Deterministic checks should fail or warn on:

- banned phrases,
- too many words,
- missing CTA,
- unsupported claims,
- no evidence items,
- mention of LinkedIn automation,
- auto-send language.

### 28.2 Human Feedback

Track:

- approved without edits,
- approved after revision,
- rejected,
- reply positive,
- reply negative,
- no reply,
- meeting booked.

### 28.3 Business Metrics

Eventually measure:

- research time saved,
- drafts produced per hour,
- approval rate,
- positive reply rate,
- meetings booked,
- opportunity creation,
- revenue influenced.

Track these from v1 even if the analytics UI comes later:

```text
revision_count
approved_without_edit
approved_after_revision
quality_score
evidence_quality
reply_status
meeting_booked
estimated_research_minutes_saved
```

---

## 29. Testing Strategy

### 29.1 Unit Tests

Test:

- YAML loading,
- row parsing,
- action routing,
- hash generation,
- status transitions,
- Postgres repositories,
- Gmail draft payload creation,
- CSV export formatting.

### 29.2 Integration Tests

Test:

- Google Sheets read/write with test spreadsheet,
- Gmail draft creation in test account,
- LangGraph run with mocked LLM,
- HubSpot sandbox/free account sync.

### 29.3 Golden Tests

Create fixed prospect examples and expected properties:

- low evidence should not generate fake personalization.
- manual LinkedIn note should be used correctly.
- revision instruction should change the draft.
- quality evaluator should flag generic email.

---

## 30. Suggested Repo Structure

```text
.
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── routes.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── graph/
│   │   ├── builder.py
│   │   ├── state.py
│   │   ├── nodes.py
│   │   └── routing.py
│   ├── integrations/
│   │   ├── google_sheets.py
│   │   ├── gmail.py
│   │   ├── hubspot.py
│   │   └── outbound_exports.py
│   ├── playbook/
│   │   ├── loader.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── run_service.py
│   │   ├── row_selector.py
│   │   ├── email_summary.py
│   │   └── quality.py
│   ├── db/
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── migrations/
│   └── prompts/
│       ├── extract_manual_context.md
│       ├── draft_email.md
│       ├── revise_message.md
│       └── evaluate_message.md
├── config/
│   └── sales_playbook.yaml
├── scripts/
│   ├── run_pending.py
│   ├── run_daily_batch.py
│   └── export_smartlead_csv.py
├── apps_script/
│   └── Code.gs
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## 31. MVP Build Phases

The source of truth for implementation phases is:

```text
Revenue_Ops_Copilot_PHASES.md
```

Do not maintain a second competing phase plan in this file.

High-level order:

```text
1. Bootstrap
2. Domain schemas + playbook YAML
3. Fake Sheet abstraction + demo dataset
4. Async run orchestration + Postgres control plane
5. LangGraph core + durable execution/checkpointer
6. Quality evaluator + revision loop
7. Real Google Sheets + Apps Script
8. Gmail drafts
9. Langfuse tracing
10. Email summary
11. CSV exports
12. Optional HubSpot adapter
13. Hardening + demo
```

---

## 32. Success Criteria For MVP

The MVP is successful if:

- A seller can add 10 leads to Google Sheets.
- The agent can research/draft messages for those leads.
- The agent does not invent unsupported personalization.
- The seller can request revisions through Sheets.
- The agent can revise based on seller instruction.
- The system can create Gmail drafts for approved rows.
- The system sends an email summary after a run.
- Langfuse shows traces for debugging.
- Postgres stores run history.
- The system can be demonstrated end-to-end in under 10 minutes.

---

## 33. Known Risks

### 33.1 Data Quality

If leads are low quality, outputs will be low quality.

Mitigation:

- fit score,
- evidence quality,
- low confidence flags.

### 33.2 Generic Messages

LLMs may produce generic copy.

Mitigation:

- quality evaluator,
- banned phrases,
- playbook rules,
- seller revision loop.

### 33.3 Overengineering

Risk of building SaaS before validating value.

Mitigation:

- Sheets first,
- no Next.js in MVP,
- no WhatsApp in MVP,
- no auto-send.

### 33.4 LinkedIn Temptation

LinkedIn has valuable data but automation is prohibited.

Mitigation:

- manual context paste only,
- no scraping,
- no browser automation,
- explicit project rule.

### 33.5 CRM Fragmentation In LATAM

Clients may use different CRMs or none.

Mitigation:

- Sheets-first,
- CRM adapters optional,
- HubSpot first for testing.

---

## 34. Future Roadmap

### v1.1

- Better HubSpot adapter.
- Zoho adapter.
- Pipedrive adapter.
- Smartlead API.
- Instantly API.
- Reply tracking manually from Sheet.

### v1.2

- RAG over historical emails/call transcripts.
- Message performance analytics.
- Account-level memory.
- Objection handling generator.
- Follow-up sequence draft generator.

### v2

- WhatsApp notifications.
- Slack/Google Chat notifications.
- Lightweight web dashboard if needed.
- Multi-user roles.
- Team-level playbooks.
- Self-host Langfuse.
- Deployment templates.

### v3

- Full revenue intelligence dashboard.
- Automatic CRM enrichment.
- Meeting prep agent.
- Call transcript analysis.
- Opportunity coaching.
- Forecasting support.

---

## 35. Final Product Positioning

Do not position as:

```text
AI SDR autónomo que consigue clientes por ti.
```

Position as:

```text
Copiloto de Revenue Ops para equipos B2B que convierte research comercial, playbooks y contexto humano en mensajes personalizados, revisables y listos para Gmail, sin scraping riesgoso ni auto-send.
```

Short pitch:

```text
Revenue Ops Copilot ayuda a founders y equipos comerciales B2B a investigar prospectos, priorizar cuentas y generar mensajes personalizados en minutos, usando Google Sheets y Gmail, con aprobación humana y trazabilidad completa.
```

---

## 36. Implementation Notes For Future Codex Session

When implementing this project:

1. Start simple.
2. Build the local flow first.
3. Do not build frontend.
4. Do not add Redis/Celery unless volume requires it.
5. Do not add vector DB unless working with long unstructured corpora.
6. Do not automate LinkedIn.
7. Do not auto-send email.
8. Make Google Sheets the UI.
9. Make the system observable from day one.
10. Keep row-level processing idempotent.
11. Prefer structured outputs for intermediate reasoning.
12. Preserve human feedback as first-class data.
13. Treat website/manual/CRM content as untrusted input.
14. Track evidence items for claims used in messages.
15. Keep the visible Sheet small; hide advanced operational columns.
16. Return `run_id` quickly from Apps Script-triggered runs and process asynchronously.

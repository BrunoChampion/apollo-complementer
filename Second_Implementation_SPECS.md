# Revenue Ops Copilot - Specs Para Sourcing Y Enrichment

**Fecha:** Mayo 2026  
**Proyecto:** Extension del sistema actual de Revenue Ops Copilot para NYVEX  
**Alcance:** Apollo sourcing, CSV imports, enrichment agent, scoring ICP, personalizacion profunda y Google Sheets como cockpit operativo  
**Estado:** Documento de especificacion. No implica desarrollo inmediato.

---

## 1. Resumen Ejecutivo

El sistema actual ayuda a procesar prospectos ya conocidos: lee leads desde Google Sheets, evalua fit basico, redacta o revisa emails, crea Gmail drafts y registra actividad.

La siguiente evolucion debe resolver el problema anterior al draft:

```text
de donde salen buenos prospectos y como sabemos si valen la pena?
```

Para NYVEX, la respuesta no debe ser "mas volumen". La respuesta debe ser un flujo que combine:

- fuentes externas de candidatos, empezando por Apollo via CSV y luego API,
- enrichment automatico controlado por lead,
- scoring especifico para el ICP de NYVEX,
- evidencia trazable,
- mensajes personalizados basados en senales reales,
- revision humana final en Google Sheets.

El objetivo no es crear un SDR autonomo que scrapea y envia emails. El objetivo es que Bruno pueda entrar a Google Sheets, revisar oportunidades priorizadas, ajustar mensajes si hace falta y aprobar acciones.

---

## 2. Principios Del Producto

1. Google Sheets sigue siendo la UI principal.
2. No se debe automatizar LinkedIn ni scrapear fuentes con terminos restrictivos.
3. No se debe enviar email automaticamente en esta etapa.
4. Apollo/Snov/Hunter/Findymail son fuentes de datos, no fuentes de verdad.
5. El enrichment agent debe validar y contextualizar los leads antes de redactar.
6. La evidencia debe ser visible y trazable.
7. El sistema debe favorecer menos volumen y mayor precision.
8. La automatizacion debe ser progresiva: CSV primero, API despues.
9. Cualquier lead de baja confianza debe quedar marcado como `needs_review`, no forzado a draft.
10. El usuario debe poder corregir el input, pedir revision o descartar desde la Sheet.

---

## 3. Objetivos

### 3.1 Objetivos Comerciales

- Reducir tiempo de busqueda y research de prospectos.
- Priorizar cuentas B2B LATAM con mayor probabilidad de dolor y presupuesto.
- Detectar casos de uso relevantes para AI agents, RAG e internal automations.
- Crear emails que suenen especificos, humanos y basados en evidencia.
- Ayudar a NYVEX a aprender que segmentos y triggers generan conversaciones reales.

### 3.2 Objetivos Tecnicos

- Importar leads desde CSV de Apollo/Snov/Hunter/Findymail.
- Normalizar columnas externas al schema interno `LeadRow`.
- Deduplicar leads por email, dominio, company_name y source_url.
- Enriquecer leads con fuentes permitidas.
- Guardar enrichment outputs en Google Sheets y Postgres.
- Observar cada enrichment run en Langfuse.
- Preparar una interfaz interna para Apollo API.
- Mantener fallback local/testable sin APIs externas.

---

## 4. No Objetivos

No esta en alcance de esta extension:

- Enviar correos automaticamente.
- Automatizar LinkedIn.
- Comprar dominios o mailboxes desde Apollo.
- Reemplazar herramientas outbound como Smartlead, Instantly o Apollo Sequences.
- Construir un CRM completo.
- Construir una UI SaaS.
- Hacer scraping agresivo de sitios bloqueados.
- Garantizar email deliverability.
- Garantizar que Apollo tenga datos correctos en LATAM.

---

## 5. ICP NYVEX

El ICP no debe limitarse por sector. NYVEX esta en etapa de aprendizaje y debe buscar empresas B2B con senales de dolor y presupuesto.

### 5.1 Criterios De Cuenta

Prioridad alta:

- Empresa B2B.
- LATAM, con foco inicial en Argentina, Colombia, Mexico, Chile y Peru.
- 20-200 empleados.
- 10-19 empleados solo si hay funding, aceleradora, crecimiento claro o senal fuerte de presupuesto.
- Operaciones manuales visibles.
- Equipo de soporte, operaciones, customer success, ventas consultivas o implementacion.
- Producto o servicio donde conocimiento interno/documentacion/procesos repetitivos importan.

### 5.2 Senales Positivas

- Hiring en soporte, operaciones, customer success, data, implementation o engineering.
- Funding, expansion, apertura de mercado, rebrand, lanzamiento de producto.
- Help center, docs, knowledge base, academy o recursos publicos extensos.
- Muchas integraciones o producto con onboarding complejo.
- Equipo de soporte visible o muchas vacantes operativas.
- Founder/COO/CTO hablando de eficiencia, AI, automatizacion, soporte, escalabilidad o procesos.
- Empresa con herramientas SaaS visibles y stack relativamente maduro.

### 5.3 Senales Negativas

- B2C puro sin venta consultiva B2B.
- Microempresa sin presupuesto claro.
- Empresa con sitio pobre o sin senales verificables.
- Prospecto sin rol activo.
- Cargo no relacionado con decision, dolor o influencia.
- Industria irrelevante si no hay complejidad operativa.
- Email generico sin persona concreta, salvo investigacion manual posterior.

### 5.4 Buyers Prioritarios

Tier A:

- Founder
- CEO
- COO
- CTO
- Co-Founder

Tier B:

- Head of Operations
- Director of Operations
- Head of Customer Success
- Head of Support
- VP Engineering
- VP Product
- Head of Technology

Tier C:

- Product Manager
- Customer Support Manager
- Operations Manager
- Sales Director
- Commercial Manager

Tier C solo aplica si la empresa es pequena o el rol tiene influencia real.

---

## 6. Arquitectura Objetivo

```text
Apollo/Snov/Hunter CSV
        |
        v
CSV Importer / Column Mapper
        |
        v
Dedup + Lead Normalization
        |
        v
Google Sheet: Leads
        |
        v
Enrichment Agent
        |
        v
ICP Scoring + Evidence Tracking
        |
        v
Draft Agent
        |
        v
Google Sheet Review
        |
        v
Gmail Draft / CSV Export
```

Fase posterior:

```text
Apollo API
   -> Sourcing Jobs
   -> Candidate Queue
   -> Enrichment Agent
   -> Leads Sheet
```

---

## 7. Google Sheet Como Cockpit

### 7.1 Tabs

El workbook debe tener estas tabs:

- `Leads`
- `Runs`
- `Email Drafts`
- `Imports`
- `Enrichment`
- `Source Candidates`

`Leads`, `Runs` y `Email Drafts` ya existen conceptualmente. Las nuevas tabs agregan control sobre importacion y sourcing.

### 7.2 Tab: Source Candidates

Contiene candidatos antes de convertirse en leads procesables.

Columnas:

```text
candidate_id
source_provider
source_record_id
source_url
company_name
company_website
company_domain
company_linkedin_url
prospect_name
prospect_title
prospect_linkedin_url
prospect_email
country
region
industry
company_size
raw_headline
raw_company_description
raw_data_json
candidate_status
candidate_score
candidate_score_reason
dedupe_key
duplicate_of
import_batch_id
created_at
reviewed_by
reviewed_at
notes
```

Estados:

```text
new
imported
duplicate
needs_review
rejected
promoted_to_lead
```

### 7.3 Tab: Imports

Registra cada importacion CSV/API.

Columnas:

```text
import_batch_id
source_provider
source_type
file_name
created_by
created_at
total_rows
imported_count
duplicate_count
rejected_count
error_count
status
notes
```

Estados:

```text
running
completed
completed_with_errors
failed
```

### 7.4 Tab: Enrichment

Registra el enrichment por lead.

Columnas:

```text
enrichment_id
run_id
lead_id
company_name
company_website
prospect_name
prospect_title
enrichment_status
company_summary
b2b_fit
operational_pain_hypothesis
possible_ai_use_case
personalization_angle
trigger_summary
risk_flags
evidence_count
evidence_sources
confidence_score
created_at
error_message
```

Estados:

```text
pending
running
enriched
needs_review
insufficient_data
failed
```

---

## 8. Importador CSV

### 8.1 Fuentes Iniciales

El importador debe soportar CSV de:

- Apollo
- Snov.io
- Hunter
- Findymail
- CSV generico

La primera version puede funcionar con upload local/API endpoint o archivo en disco. La version Google Sheets puede pegar datos a una tab temporal o usar Apps Script.

### 8.2 Column Mapping

Debe existir un mapper por proveedor:

```text
ApolloCsvMapper
SnovCsvMapper
HunterCsvMapper
FindymailCsvMapper
GenericCsvMapper
```

Ejemplo de mapping:

```text
First Name + Last Name -> prospect_name
Title -> prospect_title
Email -> prospect_email
Company -> company_name
Company Website -> company_website
Company LinkedIn -> company_linkedin_url
Person LinkedIn -> prospect_linkedin_url
Country -> country
Industry -> industry
Employees -> company_size
```

### 8.3 Normalizacion

El importador debe:

- limpiar espacios,
- normalizar emails a lowercase,
- extraer dominio desde email o website,
- normalizar URLs,
- generar `candidate_id`,
- generar `dedupe_key`,
- preservar `raw_data_json`.

### 8.4 Deduplicacion

Prioridad de dedupe:

1. `prospect_email`
2. `prospect_linkedin_url`
3. `company_domain + prospect_name`
4. `company_domain + prospect_title`
5. fuzzy company name opcional en fase posterior

Si hay duplicado:

- no crear lead nuevo,
- marcar `candidate_status=duplicate`,
- llenar `duplicate_of`.

### 8.5 Promocion A Lead

Un candidato pasa a `Leads` cuando:

- no es duplicado,
- tiene company_name,
- tiene prospect_name o prospect_title,
- tiene prospect_email o una fuente para buscar/verificar email posteriormente,
- pasa filtros minimos ICP.

Valores por defecto:

```text
action=research_and_draft
status=new
approved=false
source=apollo|snov|hunter|findymail|csv
```

---

## 9. Apollo API

### 9.1 Proposito

Apollo API debe usarse para automatizar sourcing y enrichment despues de validar que Apollo tiene cobertura aceptable para LATAM.

No debe integrarse antes de tener:

- enrichment agent funcional,
- CSV import funcional,
- dedupe funcional,
- metricas basicas de calidad.

### 9.2 Variables De Entorno

```env
APOLLO_API_KEY=
APOLLO_BASE_URL=https://api.apollo.io
APOLLO_MAX_CANDIDATES_PER_RUN=50
APOLLO_ENRICH_EMAILS=false
APOLLO_MONTHLY_CREDIT_BUDGET=2500
APOLLO_MIN_CANDIDATE_SCORE=60
```

### 9.3 Uso De Creditos

Apollo usa creditos para varias acciones, incluyendo:

- acceder emails o telefonos,
- API enrichment,
- people/company search segun endpoint,
- AI research,
- waterfall enrichment,
- CSV/CRM/API enrichment segun plan.

El sistema debe tratar creditos como presupuesto limitado.

Reglas:

- No enriquecer todos los candidatos automaticamente.
- Buscar candidatos sin pedir email cuando sea posible.
- Enriquecer email solo despues de score minimo.
- Registrar creditos estimados por run si Apollo devuelve usage.
- Permitir limites por run y por mes.

### 9.4 Plan Apollo Recomendado

Para NYVEX, si se decide usar API, el plan razonable inicial es `Basico` mensual si incluye:

- 2,500 creditos/mes,
- filtros avanzados,
- API/CSV/CRM enrichment,
- waterfall enrichment.

No se recomienda `Profesional` hasta que:

- Apollo demuestre buena cobertura LATAM,
- haya un flujo semanal activo,
- los 2,500 creditos queden cortos,
- workflows de Apollo sean realmente necesarios.

No se recomienda `Organizacion` en esta etapa.

### 9.5 Jobs De Sourcing

El sistema debe permitir definir sourcing jobs:

```text
job_id
name
countries
industries
headcount_min
headcount_max
titles
seniority
keywords
exclude_keywords
max_candidates
enrich_emails
status
created_at
last_run_at
```

Los jobs deben guardar candidatos en `Source Candidates`, no enviar directo a drafts.

---

## 10. Enrichment Agent

### 10.1 Proposito

El enrichment agent toma un lead/candidate y produce contexto verificable antes de redactar.

Input:

```text
company_name
company_website
company_domain
prospect_name
prospect_title
prospect_email
country
industry
source_url
manual_context
raw_data_json
```

Output:

```text
company_summary
b2b_fit
operational_pain_hypothesis
possible_ai_use_case
personalization_angle
trigger_summary
risk_flags
evidence_items
confidence_score
recommended_action
```

### 10.2 Fuentes Permitidas

Fase inicial:

- company website homepage,
- about page,
- pricing page,
- product pages,
- careers/jobs page,
- help center/docs/knowledge base,
- public blog/news pages,
- Apollo raw data,
- manual context in Sheet.

Fase posterior:

- search API,
- news API,
- Google Custom Search o Brave Search API,
- Apollo news endpoints si el plan lo permite,
- provider-specific enrichment.

No permitido:

- scraping LinkedIn automatizado,
- login automation,
- datos personales no necesarios,
- fuentes que bloquean automatizacion explicitamente,
- inferencias sensibles.

### 10.3 Evidence Items

Cada claim importante debe tener evidencia:

```text
claim
source_type
source_url
quote_or_summary
confidence
used_in_message
created_at
```

Tipos:

```text
website
careers
help_center
blog
apollo
manual_context
search_result
unknown
```

### 10.4 Scoring

El enrichment agent debe calcular:

```text
fit_score: 0-100
confidence_score: 0-100
```

Factores positivos:

- B2B claro.
- Tamano 20-200.
- Buyer relevante.
- Dolor operativo probable.
- Caso de uso AI/RAG/internal automation.
- Senal reciente.
- Email verificado.
- Evidencia externa suficiente.

Factores negativos:

- No B2B.
- Tamano fuera de rango sin excepcion.
- Buyer irrelevante.
- Sin website o fuente verificable.
- Dolor demasiado especulativo.
- Email no verificado.
- Empresa sin senales de presupuesto.

### 10.5 Recommended Action

Valores:

```text
draft
needs_manual_research
needs_email_verification
discard
wait
```

Reglas:

- `draft`: fit alto y evidencia suficiente.
- `needs_manual_research`: fit posible pero falta evidencia.
- `needs_email_verification`: fit alto pero email ausente/no verificado.
- `discard`: no ICP o baja confianza.
- `wait`: posible fit pero sin trigger/timing.

---

## 11. Draft Agent Despues De Enrichment

El draft agent no debe redactar solo con nombre/cargo/empresa si enrichment es insuficiente.

Debe usar:

- `personalization_angle`,
- `operational_pain_hypothesis`,
- `possible_ai_use_case`,
- evidence items,
- `sales_playbook.yaml`.

Si no hay evidencia suficiente:

- crear `agent_note`,
- no inventar,
- marcar `status=needs_revision` o `needs_manual_research`.

El email debe:

- estar en espanol salvo que el lead indique otro idioma,
- ser corto,
- no prometer resultados no probados,
- no mencionar scraping,
- no sonar como plantilla,
- usar 1 senal real,
- proponer conversacion de baja friccion.

---

## 12. Estados Y Acciones Nuevas

### 12.1 Nuevas Actions

```text
import_candidates
enrich
enrich_and_draft
source_apollo
verify_email
```

### 12.2 Nuevos Statuses

```text
imported
duplicate
enrichment_pending
enriching
enriched
insufficient_data
needs_manual_research
needs_email_verification
discarded
candidate_promoted
```

---

## 13. API Endpoints

### 13.1 Imports

```http
POST /imports/csv
GET /imports/{import_batch_id}
```

Request:

```json
{
  "source_provider": "apollo",
  "file_path": "exports/apollo.csv",
  "promote_to_leads": true
}
```

### 13.2 Enrichment

```http
POST /enrichment/{lead_id}
POST /runs/{run_id}/enrich
GET /enrichment/{lead_id}
```

### 13.3 Apollo

```http
POST /sourcing/apollo/jobs
POST /sourcing/apollo/jobs/{job_id}/run
GET /sourcing/apollo/jobs/{job_id}
```

---

## 14. Data Model

### 14.1 Tables

Nuevas tablas recomendadas:

```text
import_batches
source_candidates
enrichment_runs
enrichment_evidence_items
sourcing_jobs
sourcing_job_runs
provider_usage
```

### 14.2 import_batches

```text
id
source_provider
source_type
file_name
created_by
created_at
finished_at
total_rows
imported_count
duplicate_count
rejected_count
error_count
status
summary
```

### 14.3 source_candidates

```text
id
source_provider
source_record_id
source_url
company_name
company_website
company_domain
prospect_name
prospect_title
prospect_email
country
industry
company_size
raw_data
candidate_status
candidate_score
candidate_score_reason
dedupe_key
duplicate_of
import_batch_id
created_at
updated_at
```

### 14.4 enrichment_runs

```text
id
run_id
lead_id
status
company_summary
b2b_fit
operational_pain_hypothesis
possible_ai_use_case
personalization_angle
trigger_summary
risk_flags
confidence_score
recommended_action
error_message
created_at
finished_at
```

---

## 15. Observabilidad

Langfuse debe trazar:

- import batch,
- candidate normalization,
- dedupe decision,
- Apollo API request,
- enrichment fetch,
- enrichment LLM call,
- scoring decision,
- draft decision.

Metadata minima:

```text
run_id
lead_id
candidate_id
source_provider
company_domain
fit_score
confidence_score
recommended_action
model
token_usage
error_type
```

---

## 16. Seguridad Y Compliance

- API keys solo en `.env` o secret manager.
- No guardar Apollo API key en Google Sheets.
- No exponer raw personal data innecesaria.
- No usar datos sensibles para personalizacion.
- No automatizar LinkedIn.
- No auto-send.
- Respetar robots/TOS en fuentes web.
- Agregar timeouts y rate limits.
- Registrar fuente de cada claim.

---

## 17. Configuracion

Variables nuevas:

```env
APOLLO_API_KEY=
APOLLO_BASE_URL=https://api.apollo.io
APOLLO_MAX_CANDIDATES_PER_RUN=50
APOLLO_ENRICH_EMAILS=false
APOLLO_MONTHLY_CREDIT_BUDGET=2500
APOLLO_MIN_CANDIDATE_SCORE=60

ENRICHMENT_PROVIDER=openai
ENRICHMENT_MODEL=gpt-5.5
ENRICHMENT_REASONING_EFFORT=medium
ENRICHMENT_MAX_URLS_PER_LEAD=5
ENRICHMENT_HTTP_TIMEOUT_SECONDS=20
ENRICHMENT_MIN_CONFIDENCE_TO_DRAFT=65
ENRICHMENT_REQUIRE_EVIDENCE=true

GOOGLE_SHEETS_IMPORTS_TAB=Imports
GOOGLE_SHEETS_ENRICHMENT_TAB=Enrichment
GOOGLE_SHEETS_SOURCE_CANDIDATES_TAB=Source Candidates
```

---

## 18. Criterios De Exito

El sistema sera exitoso si:

- Bruno puede importar leads desde CSV sin editar columnas manualmente.
- El sistema deduplica correctamente.
- El enrichment agent descarta o pausa leads flojos.
- Los drafts usan senales reales y no inventan.
- Google Sheets muestra suficiente evidencia para revisar rapido.
- Apollo API se usa solo cuando hay prueba de cobertura LATAM.
- El flujo permite 25-40 emails altamente personalizados por semana sin trabajo manual excesivo.

---

## 19. Riesgos

1. Apollo puede tener baja cobertura LATAM.
2. Enrichment web puede ser lento o incompleto.
3. El LLM puede inferir demasiado si no hay guardrails.
4. Demasiada automatizacion puede llenar la Sheet de ruido.
5. Costos de Apollo credits pueden subir si se enriquece sin filtro.
6. El usuario puede confiar demasiado en scores automatizados.

Mitigacion:

- CSV antes de API.
- Enrichment antes de draft.
- Limites por run.
- Evidence required.
- Human review.
- Benchmarks semanales.


# Revenue Ops Copilot - Fases Para Sourcing Y Enrichment

**Fecha:** Mayo 2026  
**Spec:** `SPECS.md`  
**Objetivo:** Implementar sourcing/importacion/enrichment de forma incremental, evitando automatizar ruido.

---

## 0. Principios De Implementacion

1. No construir envio automatico.
2. No automatizar LinkedIn.
3. CSV antes de API.
4. Enrichment antes de draft.
5. Evidence required antes de personalizacion profunda.
6. Google Sheets sigue siendo cockpit principal.
7. Cada fase debe tener tests.
8. Cada integracion externa debe tener fake adapter.
9. Apollo API solo despues de validar CSV/import/enrichment.
10. El usuario debe poder revisar y corregir todo desde Sheets.

---

## 1. Mapa General De Fases

```text
Phase 0  - Preparacion de schemas y configuracion
Phase 1  - Google Sheet tabs para Imports, Source Candidates y Enrichment
Phase 2  - CSV import framework
Phase 3  - Provider mappers: Apollo/Snov/Hunter/Findymail
Phase 4  - Deduplicacion y candidate promotion
Phase 5  - Enrichment data model y persistence
Phase 6  - Web enrichment fetcher controlado
Phase 7  - Enrichment agent con OpenAI + evidence
Phase 8  - Enrichment scoring y recommended actions
Phase 9  - Draft gating basado en enrichment
Phase 10 - Apps Script menu para imports/enrichment
Phase 11 - Apollo API client fake + real
Phase 12 - Apollo sourcing jobs
Phase 13 - Apollo credit budget y usage tracking
Phase 14 - End-to-end sourcing to draft workflow
Phase 15 - Hardening, docs y benchmark LATAM
```

---

## Phase 0 - Preparacion De Schemas Y Configuracion

### Objetivo

Agregar configuracion y enums para sourcing/enrichment sin cambiar comportamiento actual.

### Entregables

- Nuevas variables en `.env.example`.
- Nuevos statuses/actions.
- Schemas Pydantic para:
  - `SourceCandidate`,
  - `ImportBatch`,
  - `EnrichmentResult`,
  - `EvidenceItem`.
- Tests unitarios de validacion.

### Archivos Esperados

```text
app/domain/candidates.py
app/domain/enrichment.py
app/core/config.py
tests/test_candidate_schema.py
tests/test_enrichment_schema.py
```

### Validacion

```bash
pytest tests/test_candidate_schema.py tests/test_enrichment_schema.py
ruff check .
```

### No Hacer

- No Apollo API.
- No web fetch.
- No LLM calls.

---

## Phase 1 - Google Sheet Tabs Nuevas

### Objetivo

Extender Google Sheets como cockpit para nuevas tabs:

- `Imports`
- `Source Candidates`
- `Enrichment`

### Entregables

- Apps Script crea/actualiza headers.
- Backend conoce nombres de tabs por env.
- GoogleSheetClient puede append/update en tabs nuevas.
- Docs actualizados.

### Tests

- Test de headers esperados.
- Test de append en tabs nuevas.

### Validacion Manual

```text
Revenue Copilot -> Configurar plantilla
```

Debe crear:

```text
Leads
Runs
Email Drafts
Imports
Source Candidates
Enrichment
```

---

## Phase 2 - CSV Import Framework

### Objetivo

Crear framework generico para importar CSVs a `Source Candidates`.

### Entregables

- Servicio `CsvImportService`.
- Endpoint `POST /imports/csv`.
- Registro en `Imports`.
- Append de candidatos a `Source Candidates`.
- Fake/local file mode.

### Archivos Esperados

```text
app/services/import_service.py
app/api/routes/imports.py
app/integrations/imports/base.py
tests/test_csv_import_service.py
tests/test_imports_api.py
```

### Validacion

Importar CSV generico y ver filas nuevas en `Source Candidates`.

---

## Phase 3 - Provider Mappers

### Objetivo

Soportar CSVs comunes de proveedores.

### Entregables

- `ApolloCsvMapper`
- `SnovCsvMapper`
- `HunterCsvMapper`
- `FindymailCsvMapper`
- `GenericCsvMapper`
- Fixtures de CSV por proveedor.

### Tests

Cada mapper debe convertir columnas externas a schema interno.

### No Hacer

- No llamar APIs externas.

---

## Phase 4 - Deduplicacion Y Promocion A Lead

### Objetivo

Evitar que el sistema llene Google Sheets con duplicados o leads flojos.

### Entregables

- Dedupe service por email, LinkedIn URL, dominio+nombre.
- Candidate scoring preliminar.
- Candidate promotion a `Leads`.
- `candidate_status` correcto.

### Reglas

Promocionar solo si:

- no duplicado,
- company_name presente,
- prospect_name o prospect_title presente,
- email o fuente de contacto presente,
- no falla filtros minimos ICP.

### Tests

- duplicate by email,
- duplicate by LinkedIn URL,
- duplicate by company_domain + prospect_name,
- rejected incomplete record,
- promoted candidate.

---

## Phase 5 - Enrichment Data Model Y Persistence

### Objetivo

Guardar resultados de enrichment de forma trazable.

### Entregables

- Tablas:
  - `enrichment_runs`,
  - `enrichment_evidence_items`.
- Repository.
- Alembic migration.
- Sheet append a tab `Enrichment`.

### Tests

- create enrichment run,
- add evidence items,
- serialize to Sheet.

---

## Phase 6 - Web Enrichment Fetcher Controlado

### Objetivo

Recolectar datos publicos permitidos de la empresa.

### Entregables

- HTTP fetcher con timeout.
- URL discovery limitado:
  - homepage,
  - about,
  - pricing,
  - careers,
  - blog,
  - help/docs.
- HTML text extraction.
- Robots/TOS-aware guardrails basicos.
- Max URLs por lead.

### Variables

```env
ENRICHMENT_MAX_URLS_PER_LEAD=5
ENRICHMENT_HTTP_TIMEOUT_SECONDS=20
```

### Tests

Usar fixtures HTML locales, no internet real.

---

## Phase 7 - Enrichment Agent Con OpenAI + Evidence

### Objetivo

Crear agente que convierta datos crudos en contexto comercial accionable.

### Entregables

- LangGraph enrichment flow.
- Prompt estructurado.
- Output JSON validado.
- Evidence items requeridos.
- Fallback deterministico para tests.

### Output

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

### Tests

- no inventar si input es debil,
- produce evidence,
- marca `insufficient_data`,
- recomienda `draft` solo con evidencia suficiente.

---

## Phase 8 - Enrichment Scoring Y Recommended Actions

### Objetivo

Convertir enrichment en decision operativa.

### Entregables

- Scoring service 0-100.
- Confidence scoring.
- Recommended action:
  - `draft`,
  - `needs_manual_research`,
  - `needs_email_verification`,
  - `discard`,
  - `wait`.

### Tests

Casos positivos/negativos del ICP NYVEX.

---

## Phase 9 - Draft Gating Basado En Enrichment

### Objetivo

Evitar drafts genericos cuando no hay contexto suficiente.

### Entregables

- `enrich_and_draft` action.
- Draft agent usa enrichment output.
- Si confidence baja, no redacta; marca revision.
- Email incluye solo claims con evidencia.

### Tests

- lead con buen enrichment -> draft.
- lead sin evidencia -> needs_manual_research.
- quality/evidence guardrails.

---

## Phase 10 - Apps Script Menu Para Imports/Enrichment

### Objetivo

Permitir operar desde Google Sheets.

### Entregables

Menu:

```text
Importar candidatos CSV
Promover candidatos seleccionados
Enriquecer pendientes
Enriquecer y redactar
```

Nota: si Apps Script no puede subir archivo comodamente, esta fase puede limitarse a procesar datos pegados en una tab temporal.

### Validacion Manual

Usuario pega CSV en tab temporal y ejecuta import.

---

## Phase 11 - Apollo API Client Fake + Real

### Objetivo

Preparar integracion Apollo sin gastar creditos en tests.

### Entregables

- `ApolloClientProtocol`.
- `FakeApolloClient`.
- `HttpApolloClient`.
- Auth por `APOLLO_API_KEY`.
- Rate limit/timeouts.
- Tests con fake responses.

### Endpoints Iniciales

- people/company search,
- organization enrichment,
- people enrichment,
- optional job postings/news si plan lo permite.

### No Hacer

- No enriquecer emails masivamente.

---

## Phase 12 - Apollo Sourcing Jobs

### Objetivo

Definir busquedas repetibles por ICP.

### Entregables

- CRUD de sourcing jobs.
- Run job -> Source Candidates.
- Limites por run.
- No pedir emails por defecto.

### Ejemplo

```json
{
  "countries": ["Argentina", "Colombia", "Mexico", "Chile", "Peru"],
  "titles": ["COO", "Head of Operations", "CTO", "Founder"],
  "headcount_min": 10,
  "headcount_max": 200,
  "max_candidates": 50,
  "enrich_emails": false
}
```

---

## Phase 13 - Apollo Credit Budget Y Usage Tracking

### Objetivo

Evitar consumo accidental de creditos.

### Entregables

- `provider_usage` table.
- Estimacion o registro de creditos.
- Budget mensual.
- Hard stop si se supera presupuesto.
- Warnings en `Runs`.

### Tests

- stops when budget exceeded.
- enriches only above min candidate score.

---

## Phase 14 - End-To-End Sourcing To Draft

### Objetivo

Flujo completo:

```text
Apollo job / CSV
-> Source Candidates
-> promote
-> enrich
-> score
-> draft
-> Sheet review
```

### Entregables

- Endpoint orquestador.
- Apps Script action.
- Langfuse traces.
- Docs de operacion semanal.

### Validacion Manual

Con 10 leads de prueba:

- candidatos importados,
- duplicados marcados,
- leads promovidos,
- enrichment visible,
- drafts creados solo cuando hay evidencia.

---

## Phase 15 - Hardening, Docs Y Benchmark LATAM

### Objetivo

Dejar el sistema listo para uso real controlado.

### Entregables

- Guia de benchmark Apollo/Snov/Hunter para LATAM.
- Guia de costos y creditos.
- Guia de operacion semanal.
- Checklist de calidad de leads.
- Tests completos.
- Demo script actualizado.

### Benchmark Recomendado

Probar 50-100 leads por fuente:

```text
provider
company_found
person_found
email_found
email_verified
title_current
country
cost_per_valid_contact
fit_after_enrichment
reply_result
notes
```

### Criterio De Decision

Integrar Apollo API en operacion real solo si:

- cobertura LATAM aceptable,
- costo por contacto usable razonable,
- enrichment agent descarta ruido con precision,
- Bruno puede revisar mensajes sin investigar cada lead desde cero.

---

## Orden Recomendado De Ejecucion Real

No empezar por Apollo API.

Orden correcto:

```text
1. CSV import
2. Dedupe
3. Enrichment agent
4. Draft gating
5. Benchmark LATAM con CSV
6. Apollo API
```

Razon:

```text
Apollo automatiza entrada.
Enrichment decide calidad.
Sin enrichment, Apollo puede automatizar ruido.
```


# Revenue Ops Copilot

Sistema interno de prospeccion outbound para NYVEX. Usa Google Sheets como interfaz operativa, FastAPI como backend, LangGraph/LangChain para enriquecimiento con agentes, OpenAI para razonamiento y redaccion, Postgres para historial operativo, y Gmail para crear borradores revisables.

El objetivo no es automatizar spam. El objetivo es ayudar a investigar prospectos, validar si calzan con el ICP, enriquecer con evidencia verificable y generar primeros correos sobrios, personalizados y revisables por un humano.

## Estado Actual

El sistema esta preparado para un flujo controlado de prospeccion B2B:

- Importa candidatos exportados manualmente desde Apollo.
- Mapea candidatos a una tab normalizada en Google Sheets.
- Obliga a pegar contenido de LinkedIn de la persona y de la empresa antes de enriquecer.
- Valida identidad, mercado, ICP y readiness.
- Promueve solo candidatos listos a la tab `Leads`.
- Enriquece leads con evidencia web y contexto manual.
- Bloquea drafts cuando falta evidencia, hay conflicto de identidad, mercado no soportado o review pendiente.
- Genera drafts solo cuando hay una senal operativa concreta.
- Crea Gmail drafts, nunca envia automaticamente.

## Arquitectura

```text
Apollo CSV export
        |
        v
Google Sheets - Source Candidates
        |
        | 1. Validar LinkedIn + ICP
        v
Readiness gate
        |
        | 2. Promover candidatos validados
        v
Google Sheets - Leads
        |
        | 3. Enriquecer leads listos
        v
FastAPI + LangGraph enrichment agent
        |
        v
Google Sheets - Enrichment
        |
        | 4. Generar drafts enriquecidos
        v
Draft gate + OpenAI draft writer
        |
        v
Google Sheets / Gmail Drafts
```

## Componentes

- `app/`: backend FastAPI, servicios, dominio y agentes.
- `apps_script/Code.gs`: menu y funciones para Google Sheets.
- `config/sales_playbook.yaml`: ICP, reglas comerciales, mensajes y guardrails.
- `infra/app/docker-compose.yml`: Postgres local para produccion pequena.
- `alembic/`: migraciones de base de datos.
- `docs/`: guias complementarias.
- `tests/`: suite de pruebas.

## Reglas Criticas Del Sistema

### LinkedIn es obligatorio antes de enriquecer

Antes de enriquecer cualquier lead, el usuario debe pegar manualmente:

- `company_linkedin_url`
- `prospect_linkedin_url`
- `manual_company_linkedin_text`
- `manual_person_linkedin_text`

Sin LinkedIn de empresa o sin LinkedIn de persona, el sistema no debe proceder.

### No inventar informacion

El agente no puede asumir datos por parecido de nombres. Si el perfil de LinkedIn, Apollo o la web no permiten confirmar identidad, el lead debe quedar bloqueado o en revision.

Ejemplos de informacion que no debe inventarse:

- headcount
- cargo actual
- empresa actual
- fit B2B
- autoridad de compra
- mercado
- evidencia de dolor operativo

### ICP actual

NYVEX apunta a empresas B2B con complejidad operativa real.

Rango de empresa:

- Ideal: 15-100 empleados.
- Aceptable: 10-200 empleados.
- 10-19 empleados solo si hay senales fuertes de presupuesto, crecimiento, funding, aceleradora, dolor operativo o complejidad B2B.
- Mas de 200 empleados solo como excepcion clara de startup/scaleup o dolor operativo muy evidente.

Mercados soportados:

- Mexico
- Colombia
- Chile
- Peru
- Argentina
- Uruguay
- Costa Rica
- Panama
- Spain

Mercados excluidos:

- Brazil
- Brasil
- mercados no hispanohablantes, salvo excepcion manual explicita.

Buyer personas preferidas:

- Founder / CEO / Co-Founder
- COO / Head of Operations
- CTO / Head of Technology
- Head of Customer Success
- Head of Support
- lideres con autoridad real sobre procesos, soporte, operaciones o tecnologia.

### Drafting

El primer correo debe seguir esta estructura:

1. Senal concreta y relevante.
2. Friccion operativa formulada como hipotesis general, no como diagnostico.
3. Credibilidad sobria de NYVEX.
4. CTA liviano para compartir 2-3 hipotesis.

El sistema debe evitar:

- "podria estar atravesando..."
- "ya hemos logrado solucionar..."
- "conversar 15 minutos" como primer CTA.
- claims no respaldados por evidencia.
- plantillas genericas.
- hype sobre IA.

Ejemplo de direccion deseada:

```text
Hola [Nombre],

Vi que [Empresa] tiene [senal concreta].

En empresas B2B con ese tipo de operacion suele aparecer una friccion: [friccion operativa general].

Desde NYVEX trabaje recientemente en un sistema de IA/RAG para una empresa B2B de HR software, enfocado en convertir conocimiento disperso en flujos operativos reales.

Tiene sentido que te comparta 2-3 hipotesis brevemente?
```

## Tabs De Google Sheets

El template crea y usa tabs como:

- `Source Candidates`
- `Leads`
- `Enrichment`
- `Runs`
- `Email Drafts`
- `Imports`

Campos importantes:

- `manual_company_linkedin_text`
- `manual_person_linkedin_text`
- `identity_validation_status`
- `identity_validation_reason`
- `icp_status`
- `icp_score`
- `icp_score_reason`
- `ready_for_enrichment`
- `ready_for_draft`
- `review_required`
- `review_category`
- `review_summary`
- `review_evidence`
- `suggested_action`
- `suggested_action_reason`
- `user_decision`
- `user_decision_notes`

## Menu En Google Sheets

El menu `Revenue Copilot` incluye:

1. `Importar export Apollo`
2. `Validar LinkedIn + ICP`
3. `Promover candidatos validados`
4. `Enriquecer leads listos`
5. `Generar drafts enriquecidos`

Por seguridad operativa, los pasos de enriquecimiento y drafting estan pensados para procesar filas seleccionadas en lotes pequenos.

## Estados Importantes

- `ready_for_enrichment`: el lead tiene datos obligatorios y paso el gate ICP/identidad.
- `ready_for_draft`: el enriquecimiento permite redactar.
- `needs_review`: el agente encontro evidencia util, pero hay una incertidumbre que requiere decision humana.
- `needs_manual_research`: no debe avanzar automaticamente.
- `discarded`: el lead no debe procesarse.
- `enriched`: el lead fue enriquecido.
- `drafted`: el draft fue generado.

Si `review_required=true`, el sistema debe explicar el motivo en:

- `review_summary`
- `review_evidence`
- `suggested_action`
- `suggested_action_reason`

## Setup Local

Requisitos:

- Python 3.11+
- Docker
- Docker Compose
- Google service account configurada
- OpenAI API key

Instalar dependencias:

```bash
pip install -e ".[dev]"
```

Crear `.env`:

```bash
cp .env.example .env
```

Levantar Postgres local:

```bash
docker compose --env-file .env -f infra/app/docker-compose.yml up -d
```

Ejecutar migraciones:

```bash
alembic upgrade head
```

Iniciar API:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

## Variables De Entorno Principales

```env
APP_ENV=production
LOG_LEVEL=INFO

APP_POSTGRES_USER=revenue_ops
APP_POSTGRES_PASSWORD=change-me
APP_POSTGRES_DB=revenue_ops_copilot
APP_POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://revenue_ops:change-me@localhost:5432/revenue_ops_copilot

OPENAI_API_KEY=change-me
OPENAI_MODEL=gpt-5.4-mini
OPENAI_REASONING_EFFORT=low

ENRICHMENT_PROVIDER=openai
ENRICHMENT_MODEL=gpt-5.4-mini
ENRICHMENT_REASONING_EFFORT=medium
ENRICHMENT_FORCE_BATCH_LIMIT=3
ENRICHMENT_MAX_TOOL_CALLS=6
DUCKDUCKGO_MAX_RESULTS=5

GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/apps/revenue-ops-copilot/service-account.json
GOOGLE_SHEETS_DEFAULT_TAB=Leads
GOOGLE_SHEETS_SOURCE_CANDIDATES_TAB=Source Candidates
GOOGLE_SHEETS_ENRICHMENT_TAB=Enrichment

APPS_SCRIPT_SHARED_SECRET=change-me

SUPPORTED_COUNTRIES=Mexico,Colombia,Chile,Peru,Argentina,Uruguay,Costa Rica,Panama,Spain
UNSUPPORTED_COUNTRIES=Brazil,Brasil
```

## Apps Script

En Google Apps Script, configurar Script Properties:

```text
REVENUE_COPILOT_API_BASE_URL=https://api.tudominio.com
REVENUE_COPILOT_SHARED_SECRET=mismo_valor_que_APPS_SCRIPT_SHARED_SECRET
```

El backend valida llamadas con el header:

```http
x-revenue-copilot-secret: <secret>
```

## Despliegue En VPS

Configuracion recomendada inicial:

- Hetzner CX23 o equivalente.
- Ubuntu 24.04.
- 2 vCPU.
- 2-4 GB RAM idealmente.
- 40 GB SSD.
- Postgres local con Docker Compose.
- Nginx como reverse proxy.
- HTTPS con Certbot.

Un VPS de 1 GB puede funcionar para pruebas o uso muy pequeno, pero conviene agregar swap y mantener lotes pequenos.

### Instalar Dependencias En Ubuntu

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  git curl nano ufw nginx \
  python3 python3-venv python3-pip \
  docker.io docker-compose-plugin

sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Cerrar sesion y volver a entrar para que aplique el grupo `docker`.

### Clonar Repo

```bash
mkdir -p ~/apps
cd ~/apps

git clone TU_REPO_URL revenue-ops-copilot
cd revenue-ops-copilot
```

### Python

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .
```

### Configurar Env

```bash
cp .env.example .env
nano .env
```

Subir `service-account.json` al servidor:

```text
/home/ubuntu/apps/revenue-ops-copilot/service-account.json
```

Si entras como `root`, puedes usar:

```text
/root/apps/revenue-ops-copilot/service-account.json
```

Pero para produccion es mejor crear un usuario no-root.

### Postgres

```bash
docker compose --env-file .env -f infra/app/docker-compose.yml up -d
```

### Migraciones

```bash
source .venv/bin/activate
alembic upgrade head
```

### Probar API

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

En otra terminal:

```bash
curl http://127.0.0.1:8000/health
```

## Systemd

Crear servicio:

```bash
sudo nano /etc/systemd/system/revenue-ops.service
```

Contenido si el usuario es `ubuntu`:

```ini
[Unit]
Description=Revenue Ops Copilot API
After=network.target docker.service
Requires=docker.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/apps/revenue-ops-copilot
EnvironmentFile=/home/ubuntu/apps/revenue-ops-copilot/.env
ExecStart=/home/ubuntu/apps/revenue-ops-copilot/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now revenue-ops
sudo systemctl status revenue-ops
```

Logs:

```bash
journalctl -u revenue-ops -f
```

## Nginx

Crear config:

```bash
sudo nano /etc/nginx/sites-available/revenue-ops
```

Contenido:

```nginx
server {
    listen 80;
    server_name api.tudominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activar:

```bash
sudo ln -s /etc/nginx/sites-available/revenue-ops /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.tudominio.com
```

## Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

No abrir publicamente:

- `8000`
- `5432`

## VPS De 1 GB RAM

Si se usa un VPS de 1 GB, agregar swap:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Y bajar limites:

```env
ENRICHMENT_FORCE_BATCH_LIMIT=1
ENRICHMENT_MAX_TOOL_CALLS=4
ENRICHMENT_HTTP_TIMEOUT_SECONDS=15
DUCKDUCKGO_MAX_RESULTS=3
```

## Endpoints Principales

```http
GET /health
POST /imports/csv
POST /imports/from_sheet_tab
POST /candidates/validate
POST /candidates/promote
POST /enrichment/run
POST /enrichment/enrich_and_draft
POST /enrichment/revise
POST /exports/smartlead-csv
POST /exports/instantly-csv
POST /orchestrate
```

Ejemplo:

```bash
curl -X POST https://api.tudominio.com/enrichment/run \
  -H "Content-Type: application/json" \
  -H "x-revenue-copilot-secret: $APPS_SCRIPT_SHARED_SECRET" \
  -d '{"run_id":"manual","selected_leads":"all","force":false}'
```

## Comandos Utiles

Tests:

```bash
pytest
```

Lint:

```bash
ruff check .
```

Formato:

```bash
ruff format .
```

Ver contenedores:

```bash
docker compose --env-file .env -f infra/app/docker-compose.yml ps
```

Ver logs Postgres:

```bash
docker compose --env-file .env -f infra/app/docker-compose.yml logs -f revenue-ops-postgres
```

Reiniciar API:

```bash
sudo systemctl restart revenue-ops
```

Ver logs API:

```bash
journalctl -u revenue-ops -f
```

## Backup Basico

Backup de Postgres:

```bash
docker exec -t revenue-ops-copilot-revenue-ops-postgres-1 \
  pg_dump -U revenue_ops revenue_ops_copilot > backup.sql
```

Restaurar:

```bash
cat backup.sql | docker exec -i revenue-ops-copilot-revenue-ops-postgres-1 \
  psql -U revenue_ops revenue_ops_copilot
```

Tambien conviene usar snapshots/backups del proveedor VPS.

## Troubleshooting

### GitHub muestra el README como un bloque raro

Esto suele pasar por encoding corrupto, caracteres nulos o contenido pegado en formato incorrecto. Este README debe estar en UTF-8 normal y con saltos de linea Markdown reales.

### Apps Script dice que falta API base URL

Faltan Script Properties:

```text
REVENUE_COPILOT_API_BASE_URL
REVENUE_COPILOT_SHARED_SECRET
```

### El backend responde 401 o 403

El secret de Apps Script no coincide con `APPS_SCRIPT_SHARED_SECRET`.

### Enrichment tarda mucho

Reducir:

```env
ENRICHMENT_FORCE_BATCH_LIMIT=1
ENRICHMENT_MAX_TOOL_CALLS=4
DUCKDUCKGO_MAX_RESULTS=3
```

### Lead queda en `needs_review`

Revisar:

- `review_summary`
- `review_evidence`
- `suggested_action`
- `suggested_action_reason`

Luego decidir en `user_decision`.

Valores comunes:

- `approve_exception`
- `pause`
- `discard`
- `change_target`
- `needs_more_context`

### Brazil/Brasil aparece en candidatos

Puede estar en `Source Candidates`, pero no debe avanzar a enrichment/draft si el pais esta marcado como Brasil/Brazil.

## Filosofia Operativa

Este sistema esta disenado para una agencia unipersonal que quiere vender proyectos de USD 5k-10k con alto criterio, no volumen masivo. Por eso prioriza:

- evidencia antes que suposicion;
- pocos leads bien trabajados antes que muchos leads genericos;
- revision humana antes que automatizacion agresiva;
- ICP flexible, pero con gates claros;
- correos sobrios que suenan a founder tecnico, no a plantilla de sales automation.

## Licencia

Proyecto interno de NYVEX.

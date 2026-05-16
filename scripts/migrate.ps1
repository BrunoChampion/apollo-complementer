param(
    [switch]$Docker
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ($Docker) {
    docker compose --env-file .env -f infra\app\docker-compose.yml up -d revenue-ops-postgres
    docker build -f infra\app\migration.Dockerfile -t revenue-ops-copilot-migrate .

    $envValues = @{}
    Get-Content .env | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $key, $value = $line.Split("=", 2)
        $envValues[$key] = $value.Trim('"')
    }
    $databaseUrl = "postgresql+psycopg://$($envValues.APP_POSTGRES_USER):$($envValues.APP_POSTGRES_PASSWORD)@revenue-ops-postgres:5432/$($envValues.APP_POSTGRES_DB)"

    docker run --rm `
        --env-file .env `
        --network app_default `
        -e DATABASE_URL="$databaseUrl" `
        revenue-ops-copilot-migrate
    exit
}

$python = ".\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "C:\Users\bruno\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
}

& $python -m alembic upgrade head

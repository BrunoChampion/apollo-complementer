from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NYVEX Revenue Ops Copilot"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./revenue_ops_copilot.db"
    fake_sheet_path: str = "examples/leads_demo.csv"
    llm_provider: str = "deterministic"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_reasoning_effort: str = "low"
    openai_base_url: str = "https://api.openai.com/v1"
    google_application_credentials: str | None = None
    google_sheets_default_tab: str = "Leads"
    google_sheets_runs_tab: str = "Runs"
    google_sheets_email_drafts_tab: str = "Email Drafts"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_refresh_token: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    manual_run_limit: int = 10
    scheduled_batch_limit: int = 50
    lock_expiry_minutes: int = 30
    row_timeout_seconds: int = 120
    max_revision_count_without_override: int = 2
    apps_script_shared_secret: str | None = None
    summary_email_to: str | None = None
    summary_email_from: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    hubspot_private_app_token: str | None = None

    # Apollo
    apollo_api_key: str | None = None
    apollo_base_url: str = "https://api.apollo.io"
    apollo_max_candidates_per_run: int = 50
    apollo_enrich_emails: bool = False
    apollo_email_enrichment_min_score: int = 75
    apollo_monthly_credit_budget: int = 2500
    apollo_min_candidate_score: int = 60
    openai_monthly_token_budget: int = 0
    openai_monthly_usd_budget: float = 0

    # Enrichment
    enrichment_provider: str = "openai"
    enrichment_model: str = "gpt-5.4-mini"
    enrichment_reasoning_effort: str = "medium"
    enrichment_max_urls_per_lead: int = 5
    enrichment_http_timeout_seconds: int = 20
    enrichment_min_confidence_to_draft: int = 65
    enrichment_require_evidence: bool = True
    enrichment_max_iterations: int = 5
    enrichment_max_tool_calls: int = 6
    enrichment_force_batch_limit: int = 3
    enrichment_max_html_bytes: int = 500_000
    duckduckgo_max_results: int = 5
    web_search_timeout_seconds: int = 10
    github_api_token: str | None = None
    supported_countries: str = (
        "Mexico,Colombia,Chile,Peru,Argentina,Uruguay,Costa Rica,Panama,Spain"
    )
    unsupported_countries: str = "Brazil,Brasil"

    # Google Sheets extra tabs
    google_sheets_imports_tab: str = "Imports"
    google_sheets_enrichment_tab: str = "Enrichment"
    google_sheets_source_candidates_tab: str = "Source Candidates"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url_with_timeout(self) -> str:
        if not self.database_url.startswith("postgresql"):
            return self.database_url
        parts = urlsplit(self.database_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.setdefault("connect_timeout", "5")
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

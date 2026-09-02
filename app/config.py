from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    admin_contact_email: str = "info@example.lt"
    crawler_user_agent: str = "MostaiGalimybiuRadaras/0.1 (+mailto:info@example.lt)"

    database_url: str = "sqlite+pysqlite:///./mostai.db"
    test_database_url: str = "sqlite+pysqlite:///./test.db"

    admin_username: str = "admin"
    admin_password_hash: str = ""

    scheduler_enabled: bool = True
    daily_crawl_time: str = "06:30"
    timezone: str = "Europe/Vilnius"

    crawler_max_urls_per_source: int = 60
    crawler_max_depth: int = 2
    crawler_request_timeout_seconds: int = 20
    crawler_min_delay_seconds: float = 1.5
    crawler_max_retries: int = 3
    crawler_max_download_mb: int = 15

    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "Mostai galimybių radaras <noreply@example.lt>"
    smtp_to: str = ""
    smtp_use_tls: bool = True
    weekly_empty_summary: bool = False

    ocr_enabled: bool = True
    ocr_languages: str = "lit+eng"

    document_retention_days: int = 365
    max_document_size_mb: int = 20

    # --- Pasirenkama S3 suderinama objektų saugykla originaliems dokumentams ---
    # Web ir cron servisai NEPRIKLAUSO nuo bendro lokalaus disko (žr.
    # app/storage/object_store.py). Jei S3_ENABLED=false (numatyta), originalūs
    # PDF/DOCX failai po teksto ištraukimo tiesiog NESAUGOMI — DB (ištrauktas
    # tekstas, hash, metaduomenys) yra vienintelis šaltinis tiesai.
    s3_enabled: bool = False
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = ""

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_to)

    @property
    def llm_configured(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

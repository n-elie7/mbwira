"""App configuration. Loads settings from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"

    # Database
    database_url: str = "sqlite+aiosqlite:///./mbwira.db"

    # LLM provider: "anthropic" or "openai"
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-8"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Africa's Talking (USSD + SMS)
    at_username: str = ""
    at_api_key: str = ""
    at_shortcode: str = ""

    # Meta WhatsApp Cloud API
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    # Support / escalation
    counselor_dashboard_password: str = ""
    emergency_hotline: str = "112"
    isange_hotline: str = "3029"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "LLM Prognoz API"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/llm_prognoz"

    # LLM provider API keys — populated via .env, never committed
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None


settings = Settings()

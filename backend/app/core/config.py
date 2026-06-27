from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "LLM Prognoz API"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/llm_prognoz"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24 * 7

    # LLM provider API keys — populated via .env, never committed
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None

    # Self-hosted LLM via Ollama — no API key needed, just a reachable server.
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:1b"


settings = Settings()

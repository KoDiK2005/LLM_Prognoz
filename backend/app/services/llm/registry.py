from app.core.config import settings
from app.models.llm_insight import LLMProvider
from app.services.llm.base import LLMClient
from app.services.llm.mock_client import MockLLMClient


def get_client(provider: LLMProvider) -> LLMClient:
    """Real client if that provider's API key is configured, mock otherwise.

    Ollama is self-hosted (no API key) and is always attempted for real;
    if the server is unreachable, generate() raises and the caller decides
    how to surface that. Google's client isn't implemented yet, so it
    always falls back to mock.
    """
    if provider == LLMProvider.OPENAI and settings.openai_api_key:
        from app.services.llm.openai_client import OpenAIClient

        return OpenAIClient(api_key=settings.openai_api_key)

    if provider == LLMProvider.ANTHROPIC and settings.anthropic_api_key:
        from app.services.llm.anthropic_client import AnthropicClient

        return AnthropicClient(api_key=settings.anthropic_api_key)

    if provider == LLMProvider.OLLAMA:
        from app.services.llm.ollama_client import OllamaClient

        return OllamaClient(base_url=settings.ollama_base_url, model_name=settings.ollama_model)

    return MockLLMClient()

from app.services.llm.base import LLMResponse


class MockLLMClient:
    """Deterministic stand-in used when a provider's API key isn't configured.

    Lets the insight pipeline (prompt building, storage, API shape) be
    built and tested before any real provider key exists.
    """

    model_name = "mock-llm"

    async def generate(self, prompt: str) -> LLMResponse:
        text = (
            "[mock response — configure an API key to get a real interpretation]\n\n"
            f"Prompt received ({len(prompt)} chars): {prompt[:200]}..."
        )
        return LLMResponse(
            text=text,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(text) // 4,
            cost_usd=0.0,
        )

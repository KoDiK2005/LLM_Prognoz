import httpx

from app.services.llm.base import LLMResponse


class OllamaClient:
    """Self-hosted model served by Ollama. No per-token cost, no API key."""

    def __init__(self, base_url: str, model_name: str) -> None:
        self.model_name = model_name
        self._base_url = base_url.rstrip("/")

    async def generate(self, prompt: str) -> LLMResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={"model": self.model_name, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            text=data.get("response", ""),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            cost_usd=0.0,
        )

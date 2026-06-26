from openai import AsyncOpenAI

from app.services.llm.base import LLMResponse

# USD per token, gpt-4o-mini pricing as of late 2024. Update if you change
# DEFAULT_MODEL or pricing changes.
_PRICE_PER_PROMPT_TOKEN = 0.15 / 1_000_000
_PRICE_PER_COMPLETION_TOKEN = 0.60 / 1_000_000

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIClient:
    def __init__(self, api_key: str, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate(self, prompt: str) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        return LLMResponse(
            text=response.choices[0].message.content or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=prompt_tokens * _PRICE_PER_PROMPT_TOKEN
            + completion_tokens * _PRICE_PER_COMPLETION_TOKEN,
        )

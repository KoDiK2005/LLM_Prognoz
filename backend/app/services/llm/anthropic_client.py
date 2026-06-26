from anthropic import AsyncAnthropic

from app.services.llm.base import LLMResponse

# USD per token, claude-3-5-haiku pricing as of late 2024. Update if you
# change DEFAULT_MODEL or pricing changes.
_PRICE_PER_PROMPT_TOKEN = 0.80 / 1_000_000
_PRICE_PER_COMPLETION_TOKEN = 4.00 / 1_000_000

DEFAULT_MODEL = "claude-3-5-haiku-20241022"


class AnthropicClient:
    def __init__(self, api_key: str, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._client = AsyncAnthropic(api_key=api_key)

    async def generate(self, prompt: str) -> LLMResponse:
        response = await self._client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens

        return LLMResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=prompt_tokens * _PRICE_PER_PROMPT_TOKEN
            + completion_tokens * _PRICE_PER_COMPLETION_TOKEN,
        )

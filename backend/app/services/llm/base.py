from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class LLMClient(Protocol):
    model_name: str

    async def generate(self, prompt: str) -> LLMResponse: ...

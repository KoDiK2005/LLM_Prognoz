import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.llm_insight import LLMProvider


class GenerateInsightsRequest(BaseModel):
    providers: list[LLMProvider]


class LLMInsightOut(BaseModel):
    id: uuid.UUID
    provider: LLMProvider
    model_name: str
    response_text: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}

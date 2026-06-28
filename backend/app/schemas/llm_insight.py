import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.llm_insight import LLMInsightStatus, LLMProvider


class GenerateInsightsRequest(BaseModel):
    providers: list[LLMProvider]


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    provider: LLMProvider = LLMProvider.OPENAI


class AskQuestionResponse(BaseModel):
    question: str
    answer: str
    provider: LLMProvider
    model_name: str

    model_config = {"protected_namespaces": ()}


class LLMInsightOut(BaseModel):
    id: uuid.UUID
    provider: LLMProvider
    model_name: str
    status: LLMInsightStatus
    response_text: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}

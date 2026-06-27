import uuid
from enum import Enum

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class LLMInsightStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMInsight(UUIDPkMixin, TimestampMixin, Base):
    """A single LLM's narrative interpretation of a forecast run."""

    __tablename__ = "llm_insights"

    forecast_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("forecast_runs.id"), nullable=False, index=True
    )

    provider: Mapped[LLMProvider] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[LLMInsightStatus] = mapped_column(
        String(20), nullable=False, default=LLMInsightStatus.PENDING
    )

    response_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Numeric] = mapped_column(Numeric(10, 6), nullable=False, default=0)

    forecast_run: Mapped["ForecastRun"] = relationship(back_populates="llm_insights")

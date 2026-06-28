import uuid
from enum import Enum

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class ForecastRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ForecastRun(UUIDPkMixin, TimestampMixin, Base):
    """A single, versioned forecast: data snapshot + model params + result."""

    __tablename__ = "forecast_runs"

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    status: Mapped[ForecastRunStatus] = mapped_column(
        String(20), nullable=False, default=ForecastRunStatus.PENDING
    )

    # e.g. {"model": "prophet", "horizon": 30, "seasonality_mode": "multiplicative"}
    forecast_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Numeric forecast output (chart-ready series), produced by the statistical/ML engine.
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="forecast_runs")
    # passive_deletes=True: let the DB's ON DELETE CASCADE remove these rows
    # instead of the ORM issuing per-row UPDATE ... SET forecast_run_id=NULL
    # (which would violate the NOT NULL constraint).
    llm_insights: Mapped[list["LLMInsight"]] = relationship(
        back_populates="forecast_run", passive_deletes=True
    )

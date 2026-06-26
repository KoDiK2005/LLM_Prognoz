import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Dataset(UUIDPkMixin, TimestampMixin, Base):
    """An uploaded source of time-series data (e.g. a CSV file)."""

    __tablename__ = "datasets"

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Resolved column roles, e.g. {"date_column": "order_date", "value_column": "revenue"}
    column_mapping: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    organization: Mapped["Organization"] = relationship(back_populates="datasets")
    forecast_runs: Mapped[list["ForecastRun"]] = relationship(back_populates="dataset")

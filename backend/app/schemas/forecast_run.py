import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.forecast_run import ForecastRunStatus


class ForecastRunCreate(BaseModel):
    dataset_id: uuid.UUID
    horizon: int = Field(default=30, gt=0, le=365)


class ForecastRunOut(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: ForecastRunStatus
    forecast_params: dict
    result: dict | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

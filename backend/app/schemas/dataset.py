import uuid
from datetime import datetime

from pydantic import BaseModel


class DatasetOut(BaseModel):
    id: uuid.UUID
    name: str
    column_mapping: dict
    created_at: datetime

    model_config = {"from_attributes": True}

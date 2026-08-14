from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MLTaskMessage(BaseModel):
    task_id: UUID
    features: dict[str, Any] = Field(min_length=1)
    model: str = Field(min_length=1, max_length=50)
    timestamp: datetime


class MLTaskResult(BaseModel):
    task_id: UUID
    prediction: float | None
    worker_id: str
    status: str

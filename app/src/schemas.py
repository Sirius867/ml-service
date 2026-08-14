from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    balance: float


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BalanceResponse(BaseModel):
    balance: float


class TopUpRequest(BaseModel):
    amount: float = Field(gt=0)


class PredictionRequest(BaseModel):
    model: str = Field(min_length=1, max_length=50)
    features: dict[str, Any] = Field(min_length=1)


class PredictionAcceptedResponse(BaseModel):
    task_id: UUID
    status: str


class PredictionStatusResponse(BaseModel):
    task_id: UUID
    model: str
    prediction: Any | None
    invalid_data: list[Any]
    status: str
    charged_amount: float
    created_at: datetime


class PredictionHistoryItem(BaseModel):
    id: UUID
    model_code: str
    input_data: Any
    prediction: Any | None
    invalid_data: list[Any]
    status: str
    charged_amount: float
    created_at: datetime


class TransactionHistoryItem(BaseModel):
    id: UUID
    transaction_type: str
    amount: float
    request_id: UUID | None
    created_at: datetime


class ErrorBody(BaseModel):
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody

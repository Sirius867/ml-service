from typing import Annotated

from fastapi import APIRouter, Depends, status

from .dependencies import get_current_user, get_service
from .orm_models import UserRecord
from .schemas import (
    BalanceResponse,
    LoginRequest,
    PredictionHistoryItem,
    PredictionRequest,
    PredictionResponse,
    RegisterRequest,
    TokenResponse,
    TopUpRequest,
    TransactionHistoryItem,
    UserResponse,
)
from .security import create_access_token
from .services import MLService


router = APIRouter()
Service = Annotated[MLService, Depends(get_service)]
CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


@router.post(
    "/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(data: RegisterRequest, service: Service) -> UserResponse:
    user = service.register_user(data.email, data.password)
    return _user_response(user)


@router.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, service: Service) -> TokenResponse:
    user = service.authenticate(data.email, data.password)
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/users/me", response_model=UserResponse)
def get_profile(user: CurrentUser) -> UserResponse:
    return _user_response(user)


@router.get("/balance", response_model=BalanceResponse)
def get_balance(user: CurrentUser) -> BalanceResponse:
    return BalanceResponse(balance=float(user.balance))


@router.post("/balance/top-up", response_model=BalanceResponse)
def top_up_balance(
    data: TopUpRequest, user: CurrentUser, service: Service
) -> BalanceResponse:
    service.top_up_balance(user.id, data.amount)
    updated_user = service.get_user(user.id)
    return BalanceResponse(balance=float(updated_user.balance))


@router.post("/predict", response_model=PredictionResponse)
def predict(
    data: PredictionRequest, user: CurrentUser, service: Service
) -> PredictionResponse:
    request = service.run_prediction(user.id, data.model_code, data.data)
    updated_user = service.get_user(user.id)
    return PredictionResponse(
        id=request.id,
        model_code=data.model_code,
        prediction=request.prediction,
        invalid_data=request.invalid_data,
        status=request.status,
        charged_amount=float(request.charged_amount),
        balance=float(updated_user.balance),
        created_at=request.created_at,
    )


@router.get("/history/predictions", response_model=list[PredictionHistoryItem])
def get_prediction_history(
    user: CurrentUser, service: Service
) -> list[PredictionHistoryItem]:
    history = service.get_prediction_history(user.id)
    return [
        PredictionHistoryItem(
            id=item.id,
            model_code=item.model.code,
            input_data=item.input_data,
            prediction=item.prediction,
            invalid_data=item.invalid_data,
            status=item.status,
            charged_amount=float(item.charged_amount),
            created_at=item.created_at,
        )
        for item in history
    ]


@router.get("/history/transactions", response_model=list[TransactionHistoryItem])
def get_transaction_history(
    user: CurrentUser, service: Service
) -> list[TransactionHistoryItem]:
    history = service.get_transactions(user.id)
    return [
        TransactionHistoryItem(
            id=item.id,
            transaction_type=item.transaction_type,
            amount=float(item.amount),
            request_id=item.request_id,
            created_at=item.created_at,
        )
        for item in history
    ]


def _user_response(user: UserRecord) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        balance=float(user.balance),
    )

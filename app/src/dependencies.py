from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import SessionFactory
from .exceptions import AuthenticationError
from .orm_models import UserRecord
from .publisher import RabbitPublisher
from .security import get_user_id_from_token
from .services import MLService


bearer_scheme = HTTPBearer(auto_error=False)


def get_service() -> MLService:
    return MLService(SessionFactory)


def get_publisher() -> RabbitPublisher:
    return RabbitPublisher()


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    service: Annotated[MLService, Depends(get_service)],
) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Требуется авторизация")

    user_id = get_user_id_from_token(credentials.credentials)
    user = service.get_user(user_id)
    if user is None:
        raise AuthenticationError("Пользователь не найден")
    return user

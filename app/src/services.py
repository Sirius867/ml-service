from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker, selectinload

from .orm_models import MLModelRecord, MLRequestRecord, TransactionRecord, UserRecord


def as_credits(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class MLService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_user(
        self, email: str, password_hash: str, role: str = "user"
    ) -> UserRecord:
        if not email.strip() or not password_hash:
            raise ValueError("Email и хеш пароля обязательны")
        if role not in {"user", "admin"}:
            raise ValueError("Неизвестная роль пользователя")

        with self._session_factory.begin() as session:
            existing = session.scalar(select(UserRecord).where(UserRecord.email == email))
            if existing:
                raise ValueError("Пользователь с таким email уже существует")

            user = UserRecord(email=email, password_hash=password_hash, role=role)
            session.add(user)
            session.flush()
            return user

    def get_user(self, user_id: UUID) -> UserRecord | None:
        with self._session_factory() as session:
            return session.get(UserRecord, user_id)

    def top_up_balance(
        self, user_id: UUID, amount: Decimal | float | int | str
    ) -> TransactionRecord:
        credits = as_credits(amount)
        if credits <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")

        with self._session_factory.begin() as session:
            user = self._get_user_for_update(session, user_id)
            user.balance += credits
            transaction = TransactionRecord(
                user=user, transaction_type="deposit", amount=credits
            )
            session.add(transaction)
            session.flush()
            return transaction

    def debit_balance(
        self, user_id: UUID, amount: Decimal | float | int | str
    ) -> TransactionRecord:
        credits = as_credits(amount)
        if credits <= 0:
            raise ValueError("Сумма списания должна быть положительной")

        with self._session_factory.begin() as session:
            user = self._get_user_for_update(session, user_id)
            if user.balance < credits:
                raise ValueError("Недостаточно средств на балансе")

            user.balance -= credits
            transaction = TransactionRecord(
                user=user, transaction_type="debit", amount=credits
            )
            session.add(transaction)
            session.flush()
            return transaction

    def run_prediction(
        self, user_id: UUID, model_code: str, input_data: list[Any]
    ) -> MLRequestRecord:
        valid_data, invalid_data = self._validate_data(input_data)
        if not valid_data:
            raise ValueError("Нет корректных данных для предсказания")

        with self._session_factory.begin() as session:
            user = self._get_user_for_update(session, user_id)
            model = session.scalar(
                select(MLModelRecord).where(MLModelRecord.code == model_code)
            )
            if model is None:
                raise ValueError("ML-модель не найдена")
            if user.balance < model.prediction_cost:
                raise ValueError("Недостаточно средств на балансе")

            prediction = self._predict(model.code, valid_data)
            request = MLRequestRecord(
                user=user,
                model=model,
                input_data=input_data,
                prediction=prediction,
                invalid_data=invalid_data,
                status="completed",
                charged_amount=model.prediction_cost,
            )
            session.add(request)
            session.flush()

            user.balance -= model.prediction_cost
            session.add(
                TransactionRecord(
                    user=user,
                    request=request,
                    transaction_type="debit",
                    amount=model.prediction_cost,
                )
            )
            session.flush()
            return request

    def get_transactions(self, user_id: UUID) -> list[TransactionRecord]:
        with self._session_factory() as session:
            statement = (
                select(TransactionRecord)
                .where(TransactionRecord.user_id == user_id)
                .order_by(TransactionRecord.created_at.desc())
            )
            return list(session.scalars(statement))

    def get_prediction_history(self, user_id: UUID) -> list[MLRequestRecord]:
        with self._session_factory() as session:
            statement = (
                select(MLRequestRecord)
                .options(selectinload(MLRequestRecord.model))
                .where(MLRequestRecord.user_id == user_id)
                .order_by(MLRequestRecord.created_at.desc())
            )
            return list(session.scalars(statement))

    @staticmethod
    def _get_user_for_update(session: Session, user_id: UUID) -> UserRecord:
        statement = select(UserRecord).where(UserRecord.id == user_id).with_for_update()
        user = session.scalar(statement)
        if user is None:
            raise ValueError("Пользователь не найден")
        return user

    @staticmethod
    def _validate_data(data: list[Any]) -> tuple[list[float], list[Any]]:
        valid_data: list[float] = []
        invalid_data: list[Any] = []
        for value in data:
            try:
                valid_data.append(float(value))
            except (TypeError, ValueError):
                invalid_data.append(value)
        return valid_data, invalid_data

    @staticmethod
    def _predict(model_code: str, data: list[float]) -> float:
        if model_code == "average":
            return sum(data) / len(data)
        if model_code == "sum":
            return sum(data)
        raise ValueError("Для ML-модели не реализовано предсказание")

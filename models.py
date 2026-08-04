from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"


class TaskStatus(Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TransactionType(Enum):
    DEPOSIT = "deposit"
    DEBIT = "debit"


@dataclass(frozen=True)
class PredictionResult:
    id: UUID
    prediction: Any
    invalid_data: list[Any]
    created_at: datetime


class User:
    def __init__(
        self,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        user_id: UUID | None = None,
    ) -> None:
        if not email.strip():
            raise ValueError("Email не может быть пустым")
        if not password_hash:
            raise ValueError("Хеш пароля не может быть пустым")

        self.id: UUID = user_id or uuid4()
        self.email: str = email
        self._password_hash: str = password_hash
        self.role: UserRole = role
        self.__balance: float = 0.0

    @property
    def balance(self) -> float:
        return self.__balance

    def check_password(self, password_hash: str) -> bool:
        return self._password_hash == password_hash

    def change_balance(self, amount: float) -> None:
        new_balance = self.__balance + amount
        if new_balance < 0:
            raise ValueError("Недостаточно средств на балансе")
        self.__balance = round(new_balance, 2)


class AdminUser(User):
    def __init__(
        self, email: str, password_hash: str, user_id: UUID | None = None
    ) -> None:
        super().__init__(email, password_hash, UserRole.ADMIN, user_id)

    def top_up_user(self, user: User, amount: float) -> DepositTransaction:
        transaction = DepositTransaction(amount, user)
        transaction.apply()
        return transaction


class MLModel(ABC):
    def __init__(
        self,
        name: str,
        description: str,
        prediction_cost: float,
        model_id: UUID | None = None,
    ) -> None:
        if prediction_cost <= 0:
            raise ValueError("Стоимость предсказания должна быть положительной")

        self.id: UUID = model_id or uuid4()
        self.name: str = name
        self.description: str = description
        self.prediction_cost: float = prediction_cost

    @abstractmethod
    def predict(self, data: list[Any]) -> Any:
        raise NotImplementedError


class AverageValueModel(MLModel):
    def predict(self, data: list[Any]) -> float:
        values = [float(value) for value in data]
        if not values:
            raise ValueError("Нет данных для предсказания")
        return sum(values) / len(values)


class Transaction(ABC):
    transaction_type: TransactionType

    def __init__(
        self,
        amount: float,
        user: User,
        task: MLTask | None = None,
        transaction_id: UUID | None = None,
    ) -> None:
        if amount <= 0:
            raise ValueError("Сумма транзакции должна быть положительной")

        self.id: UUID = transaction_id or uuid4()
        self.amount: float = amount
        self.user: User = user
        self.task: MLTask | None = task
        self.created_at: datetime = datetime.now()

    @abstractmethod
    def apply(self) -> None:
        raise NotImplementedError


class DepositTransaction(Transaction):
    transaction_type = TransactionType.DEPOSIT

    def apply(self) -> None:
        self.user.change_balance(self.amount)


class DebitTransaction(Transaction):
    transaction_type = TransactionType.DEBIT

    def apply(self) -> None:
        self.user.change_balance(-self.amount)


class MLTask:
    def __init__(
        self,
        user: User,
        model: MLModel,
        input_data: list[Any],
        task_id: UUID | None = None,
    ) -> None:
        self.id: UUID = task_id or uuid4()
        self.user: User = user
        self.model: MLModel = model
        self.input_data: list[Any] = input_data
        self.status: TaskStatus = TaskStatus.CREATED
        self.result: PredictionResult | None = None
        self.transaction: DebitTransaction | None = None
        self.created_at: datetime = datetime.now()

    def run(self) -> DebitTransaction:
        if self.user.balance < self.model.prediction_cost:
            self.status = TaskStatus.FAILED
            raise ValueError("Недостаточно средств на балансе")

        self.status = TaskStatus.PROCESSING
        valid_data, invalid_data = self._validate_data()

        try:
            prediction = self.model.predict(valid_data)
            result = PredictionResult(
                id=uuid4(),
                prediction=prediction,
                invalid_data=invalid_data,
                created_at=datetime.now(),
            )
            transaction = DebitTransaction(
                amount=self.model.prediction_cost,
                user=self.user,
                task=self,
            )
            transaction.apply()
        except (TypeError, ValueError):
            self.status = TaskStatus.FAILED
            raise

        self.result = result
        self.transaction = transaction
        self.status = TaskStatus.COMPLETED
        return transaction

    def _validate_data(self) -> tuple[list[Any], list[Any]]:
        valid_data: list[Any] = []
        invalid_data: list[Any] = []

        for value in self.input_data:
            try:
                float(value)
                valid_data.append(value)
            except (TypeError, ValueError):
                invalid_data.append(value)

        return valid_data, invalid_data


class RequestHistory:
    def __init__(self, user: User) -> None:
        self.user: User = user
        self._tasks: list[MLTask] = []

    def add(self, task: MLTask) -> None:
        if task.user.id != self.user.id:
            raise ValueError("Нельзя добавить чужую задачу в историю")
        self._tasks.append(task)

    def get_all(self) -> tuple[MLTask, ...]:
        return tuple(self._tasks)

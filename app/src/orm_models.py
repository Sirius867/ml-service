from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def current_time() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=current_time
    )

    requests: Mapped[list[MLRequestRecord]] = relationship(back_populates="user")
    transactions: Mapped[list[TransactionRecord]] = relationship(back_populates="user")


class MLModelRecord(Base):
    __tablename__ = "ml_models"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    prediction_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=current_time
    )

    requests: Mapped[list[MLRequestRecord]] = relationship(back_populates="model")


class MLRequestRecord(Base):
    __tablename__ = "ml_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    model_id: Mapped[UUID] = mapped_column(ForeignKey("ml_models.id"), nullable=False)
    input_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    prediction: Mapped[Any] = mapped_column(JSON, nullable=False)
    invalid_data: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    charged_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=current_time
    )

    user: Mapped[UserRecord] = relationship(back_populates="requests")
    model: Mapped[MLModelRecord] = relationship(back_populates="requests")
    transactions: Mapped[list[TransactionRecord]] = relationship(back_populates="request")


class TransactionRecord(Base):
    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ml_requests.id"), nullable=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=current_time
    )

    user: Mapped[UserRecord] = relationship(back_populates="transactions")
    request: Mapped[MLRequestRecord | None] = relationship(back_populates="transactions")

from decimal import Decimal

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from .database import SessionFactory, engine
from .orm_models import Base, MLModelRecord, TransactionRecord, UserRecord
from .security import hash_password


def seed_database(session_factory: sessionmaker[Session]) -> None:
    with session_factory.begin() as session:
        demo_user = session.scalar(
            select(UserRecord).where(UserRecord.email == "demo@example.com")
        )
        if demo_user is None:
            demo_user = UserRecord(
                email="demo@example.com",
                password_hash=hash_password("demo1234"),
                role="user",
                balance=Decimal("100.00"),
            )
            session.add(demo_user)
            session.flush()
            session.add(
                TransactionRecord(
                    user=demo_user,
                    transaction_type="deposit",
                    amount=Decimal("100.00"),
                )
            )
        elif not demo_user.password_hash.startswith("pbkdf2_sha256$"):
            demo_user.password_hash = hash_password("demo1234")

        demo_admin = session.scalar(
            select(UserRecord).where(UserRecord.email == "admin@example.com")
        )
        if demo_admin is None:
            session.add(
                UserRecord(
                    email="admin@example.com",
                    password_hash=hash_password("admin1234"),
                    role="admin",
                )
            )
        elif not demo_admin.password_hash.startswith("pbkdf2_sha256$"):
            demo_admin.password_hash = hash_password("admin1234")

        models = (
            ("average", "Среднее значение", "Вычисляет среднее числовых значений", "10.00"),
            ("sum", "Сумма значений", "Вычисляет сумму числовых значений", "5.00"),
        )
        for code, name, description, cost in models:
            exists = session.scalar(
                select(MLModelRecord).where(MLModelRecord.code == code)
            )
            if exists is None:
                session.add(
                    MLModelRecord(
                        code=code,
                        name=name,
                        description=description,
                        prediction_cost=Decimal(cost),
                    )
                )


def initialize_database(
    database_engine: Engine = engine,
    session_factory: sessionmaker[Session] = SessionFactory,
) -> None:
    Base.metadata.create_all(database_engine)
    seed_database(session_factory)


if __name__ == "__main__":
    initialize_database()

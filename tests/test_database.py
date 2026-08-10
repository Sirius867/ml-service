import unittest
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.src.init_db import seed_database
from app.src.orm_models import Base, MLModelRecord, UserRecord
from app.src.services import MLService


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine, expire_on_commit=False, class_=Session
        )
        self.service = MLService(self.session_factory)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_create_and_load_user(self) -> None:
        created = self.service.create_user("user@example.com", "password_hash")
        loaded = self.service.get_user(created.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.email, "user@example.com")
        self.assertEqual(loaded.balance, Decimal("0.00"))

    def test_balance_and_transaction_history(self) -> None:
        user = self.service.create_user("user@example.com", "password_hash")
        self.service.top_up_balance(user.id, 50)
        self.service.debit_balance(user.id, 15)

        loaded = self.service.get_user(user.id)
        transactions = self.service.get_transactions(user.id)

        self.assertEqual(loaded.balance, Decimal("35.00"))
        self.assertEqual(len(transactions), 2)
        self.assertEqual({item.transaction_type for item in transactions}, {"deposit", "debit"})

    def test_debit_is_rejected_when_balance_is_insufficient(self) -> None:
        user = self.service.create_user("user@example.com", "password_hash")

        with self.assertRaisesRegex(ValueError, "Недостаточно средств"):
            self.service.debit_balance(user.id, 10)

        self.assertEqual(self.service.get_user(user.id).balance, Decimal("0.00"))
        self.assertEqual(self.service.get_transactions(user.id), [])

    def test_prediction_is_saved_and_charged(self) -> None:
        seed_database(self.session_factory)
        with self.session_factory() as session:
            user = session.scalar(
                select(UserRecord).where(UserRecord.email == "demo@example.com")
            )

        request = self.service.run_prediction(
            user.id, "average", [10, "ошибка", 20, 30]
        )
        second_request = self.service.run_prediction(user.id, "sum", [1, 2, 3])
        history = self.service.get_prediction_history(user.id)

        self.assertEqual(request.prediction, 20.0)
        self.assertEqual(request.invalid_data, ["ошибка"])
        self.assertEqual(request.charged_amount, Decimal("10.00"))
        self.assertEqual(self.service.get_user(user.id).balance, Decimal("85.00"))
        self.assertEqual([item.id for item in history], [second_request.id, request.id])
        self.assertEqual(history[1].model.code, "average")

    def test_seed_is_idempotent(self) -> None:
        seed_database(self.session_factory)
        seed_database(self.session_factory)

        with self.session_factory() as session:
            users = list(session.scalars(select(UserRecord)))
            models = list(session.scalars(select(MLModelRecord)))

        self.assertEqual(len(users), 2)
        self.assertEqual(len(models), 2)


if __name__ == "__main__":
    unittest.main()

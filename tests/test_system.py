import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.src.dependencies import get_publisher, get_service
from app.src.init_db import seed_database
from app.src.main import create_app
from app.src.orm_models import Base
from app.src.services import MLService


class TestPublisher:
    def __init__(self) -> None:
        self.messages = []

    def publish(self, message) -> None:
        self.messages.append(message)


class SystemTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine, expire_on_commit=False, class_=Session
        )
        seed_database(self.session_factory)
        self.service = MLService(self.session_factory)
        self.publisher = TestPublisher()

        app = create_app(initialize=False)
        app.dependency_overrides[get_service] = lambda: self.service
        app.dependency_overrides[get_publisher] = lambda: self.publisher
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def register_and_login(self, email: str = "system@example.com") -> dict[str, str]:
        registration = self.client.post(
            "/auth/register",
            json={"email": email, "password": "password123"},
        )
        self.assertEqual(registration.status_code, 201)
        login = self.client.post(
            "/auth/login",
            json={"email": email, "password": "password123"},
        )
        self.assertEqual(login.status_code, 200)
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def process_last_task(self):
        message = self.publisher.messages[-1]
        return self.service.process_prediction_task(
            message.task_id, message.model, message.features
        )

    def test_user_creation_and_repeated_authorization(self) -> None:
        headers = self.register_and_login()

        second_login = self.client.post(
            "/auth/login",
            json={"email": "system@example.com", "password": "password123"},
        )
        wrong_login = self.client.post(
            "/auth/login",
            json={"email": "system@example.com", "password": "wrong-password"},
        )
        profile = self.client.get("/users/me", headers=headers)

        self.assertEqual(second_login.status_code, 200)
        self.assertEqual(wrong_login.status_code, 401)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["email"], "system@example.com")

    def test_balance_top_up_and_transaction(self) -> None:
        headers = self.register_and_login()
        initial_balance = self.client.get("/balance", headers=headers)
        updated_balance = self.client.post(
            "/balance/top-up", json={"amount": 40}, headers=headers
        )
        transactions = self.client.get("/history/transactions", headers=headers)

        self.assertEqual(initial_balance.json()["balance"], 0.0)
        self.assertEqual(updated_balance.json()["balance"], 40.0)
        self.assertEqual(len(transactions.json()), 1)
        self.assertEqual(transactions.json()[0]["transaction_type"], "deposit")
        self.assertEqual(transactions.json()[0]["amount"], 40.0)

    def test_successful_prediction_with_partially_valid_data(self) -> None:
        headers = self.register_and_login()
        self.client.post("/balance/top-up", json={"amount": 40}, headers=headers)

        accepted = self.client.post(
            "/predict",
            json={
                "model": "average",
                "features": {"x1": 10, "bad": "ошибка", "x2": 20, "x3": 30},
            },
            headers=headers,
        )
        self.assertEqual(accepted.status_code, 202)
        self.process_last_task()

        result = self.client.get(
            f"/predict/{accepted.json()['task_id']}", headers=headers
        )
        balance = self.client.get("/balance", headers=headers)

        self.assertEqual(result.json()["status"], "completed")
        self.assertEqual(result.json()["prediction"], 20.0)
        self.assertEqual(
            result.json()["invalid_data"],
            [{"feature": "bad", "value": "ошибка"}],
        )
        self.assertEqual(result.json()["charged_amount"], 10.0)
        self.assertEqual(balance.json()["balance"], 30.0)

    def test_failed_prediction_does_not_charge_balance(self) -> None:
        headers = self.register_and_login()
        self.client.post("/balance/top-up", json={"amount": 20}, headers=headers)

        accepted = self.client.post(
            "/predict",
            json={
                "model": "sum",
                "features": {"bad": "ошибка", "empty": None, "number": "NaN"},
            },
            headers=headers,
        )
        self.process_last_task()
        result = self.client.get(
            f"/predict/{accepted.json()['task_id']}", headers=headers
        )
        balance = self.client.get("/balance", headers=headers)
        transactions = self.client.get("/history/transactions", headers=headers)

        self.assertEqual(result.json()["status"], "failed")
        self.assertEqual(result.json()["charged_amount"], 0.0)
        self.assertEqual(len(result.json()["invalid_data"]), 3)
        self.assertEqual(balance.json()["balance"], 20.0)
        self.assertEqual(len(transactions.json()), 1)

    def test_insufficient_balance_and_complete_history(self) -> None:
        headers = self.register_and_login()
        rejected = self.client.post(
            "/predict",
            json={"model": "sum", "features": {"x1": 1, "x2": 2}},
            headers=headers,
        )
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(len(self.publisher.messages), 0)

        self.client.post("/balance/top-up", json={"amount": 20}, headers=headers)
        accepted = self.client.post(
            "/predict",
            json={"model": "sum", "features": {"x1": 1, "x2": 2}},
            headers=headers,
        )
        self.process_last_task()

        predictions = self.client.get("/history/predictions", headers=headers).json()
        transactions = self.client.get("/history/transactions", headers=headers).json()

        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]["id"], accepted.json()["task_id"])
        self.assertEqual(predictions[0]["status"], "completed")
        self.assertEqual(predictions[0]["charged_amount"], 5.0)
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0]["transaction_type"], "debit")
        self.assertEqual(transactions[0]["request_id"], accepted.json()["task_id"])


if __name__ == "__main__":
    unittest.main()

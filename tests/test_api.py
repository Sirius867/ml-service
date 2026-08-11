import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.src.dependencies import get_service
from app.src.init_db import seed_database
from app.src.main import create_app
from app.src.orm_models import Base
from app.src.services import MLService


class ApiTestCase(unittest.TestCase):
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

        app = create_app(initialize=False)
        app.dependency_overrides[get_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_full_user_scenario(self) -> None:
        registration = self.client.post(
            "/auth/register",
            json={"email": "user@example.com", "password": "password123"},
        )
        self.assertEqual(registration.status_code, 201)
        self.assertEqual(registration.json()["balance"], 0.0)

        login = self.client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        self.assertEqual(login.status_code, 200)
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        balance = self.client.post(
            "/balance/top-up", json={"amount": 30}, headers=headers
        )
        self.assertEqual(balance.status_code, 200)
        self.assertEqual(balance.json()["balance"], 30.0)

        prediction = self.client.post(
            "/predict",
            json={"model_code": "average", "data": [10, "ошибка", 20, 30]},
            headers=headers,
        )
        self.assertEqual(prediction.status_code, 200)
        self.assertEqual(prediction.json()["prediction"], 20.0)
        self.assertEqual(prediction.json()["invalid_data"], ["ошибка"])
        self.assertEqual(prediction.json()["charged_amount"], 10.0)
        self.assertEqual(prediction.json()["balance"], 20.0)

        predictions = self.client.get("/history/predictions", headers=headers)
        transactions = self.client.get("/history/transactions", headers=headers)
        self.assertEqual(len(predictions.json()), 1)
        self.assertEqual(len(transactions.json()), 2)
        self.assertEqual(transactions.json()[0]["request_id"], prediction.json()["id"])

    def test_authentication_and_validation_errors(self) -> None:
        unauthorized = self.client.get("/balance")
        self.assertEqual(unauthorized.status_code, 401)
        self.assertIn("error", unauthorized.json())

        invalid_token = self.client.get(
            "/balance", headers={"Authorization": "Bearer invalid-token"}
        )
        self.assertEqual(invalid_token.status_code, 401)
        self.assertIn("error", invalid_token.json())

        invalid_registration = self.client.post(
            "/auth/register", json={"email": "wrong", "password": "short"}
        )
        self.assertEqual(invalid_registration.status_code, 422)
        self.assertEqual(
            invalid_registration.json()["error"]["message"],
            "Ошибка валидации данных",
        )

    def test_duplicate_registration_and_wrong_password(self) -> None:
        data = {"email": "user@example.com", "password": "password123"}
        self.assertEqual(self.client.post("/auth/register", json=data).status_code, 201)
        self.assertEqual(self.client.post("/auth/register", json=data).status_code, 409)

        wrong_password = self.client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "wrong-password"},
        )
        self.assertEqual(wrong_password.status_code, 401)

    def test_prediction_requires_sufficient_balance(self) -> None:
        self.client.post(
            "/auth/register",
            json={"email": "user@example.com", "password": "password123"},
        )
        login = self.client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response = self.client.post(
            "/predict",
            json={"model_code": "average", "data": [1, 2, 3]},
            headers=headers,
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("Недостаточно средств", response.json()["error"]["message"])

        self.client.post("/balance/top-up", json={"amount": 20}, headers=headers)
        invalid_data = self.client.post(
            "/predict",
            json={"model_code": "average", "data": ["ошибка", None]},
            headers=headers,
        )
        self.assertEqual(invalid_data.status_code, 400)
        self.assertIn("Нет корректных данных", invalid_data.json()["error"]["message"])


if __name__ == "__main__":
    unittest.main()

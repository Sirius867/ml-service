import os
import time

import httpx


base_url = os.getenv("API_URL", "http://localhost")
email = f"system-test-{int(time.time())}@example.com"
password = "password123"


def wait_for_task(client, task_id, headers):
    deadline = time.time() + 30
    while time.time() < deadline:
        response = client.get(f"/predict/{task_id}", headers=headers)
        response.raise_for_status()
        task = response.json()
        if task["status"] in {"completed", "failed"}:
            return task
        time.sleep(1)
    raise RuntimeError(f"Задача {task_id} не обработана за 30 секунд")


with httpx.Client(base_url=base_url, timeout=10) as client:
    registration = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert registration.status_code == 201

    first_login = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    second_login = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    wrong_login = client.post(
        "/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert first_login.status_code == 200
    assert second_login.status_code == 200
    assert wrong_login.status_code == 401
    headers = {"Authorization": f"Bearer {first_login.json()['access_token']}"}

    initial_balance = client.get("/balance", headers=headers)
    assert initial_balance.json()["balance"] == 0

    top_up = client.post("/balance/top-up", json={"amount": 40}, headers=headers)
    assert top_up.json()["balance"] == 40

    valid_request = client.post(
        "/predict",
        json={
            "model": "average",
            "features": {"x1": 10, "bad": "ошибка", "x2": 20, "x3": 30},
        },
        headers=headers,
    )
    valid_request.raise_for_status()
    valid_result = wait_for_task(client, valid_request.json()["task_id"], headers)
    assert valid_result["status"] == "completed"
    assert valid_result["prediction"] == 20
    assert valid_result["charged_amount"] == 10
    assert len(valid_result["invalid_data"]) == 1

    failed_request = client.post(
        "/predict",
        json={
            "model": "sum",
            "features": {"bad": "ошибка", "empty": None, "number": "NaN"},
        },
        headers=headers,
    )
    failed_request.raise_for_status()
    failed_result = wait_for_task(client, failed_request.json()["task_id"], headers)
    assert failed_result["status"] == "failed"
    assert failed_result["charged_amount"] == 0

    final_balance = client.get("/balance", headers=headers)
    assert final_balance.json()["balance"] == 30

    predictions = client.get("/history/predictions", headers=headers)
    transactions = client.get("/history/transactions", headers=headers)
    predictions.raise_for_status()
    transactions.raise_for_status()
    assert len(predictions.json()) == 2
    assert len(transactions.json()) == 2
    assert {item["status"] for item in predictions.json()} == {"completed", "failed"}
    assert {item["transaction_type"] for item in transactions.json()} == {
        "deposit",
        "debit",
    }

    second_email = f"empty-balance-{int(time.time())}@example.com"
    client.post(
        "/auth/register", json={"email": second_email, "password": password}
    ).raise_for_status()
    second_login = client.post(
        "/auth/login", json={"email": second_email, "password": password}
    )
    second_headers = {
        "Authorization": f"Bearer {second_login.json()['access_token']}"
    }
    insufficient = client.post(
        "/predict",
        json={"model": "sum", "features": {"x1": 1, "x2": 2}},
        headers=second_headers,
    )
    assert insufficient.status_code == 409

print("Сквозная проверка завершена успешно")

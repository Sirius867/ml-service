import os
import time

import httpx


base_url = os.getenv("API_URL", "http://localhost")
email = f"rabbit-test-{int(time.time())}@example.com"
password = "password123"

with httpx.Client(base_url=base_url, timeout=10) as client:
    registration = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    registration.raise_for_status()

    login = client.post("/auth/login", json={"email": email, "password": password})
    login.raise_for_status()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    top_up = client.post("/balance/top-up", json={"amount": 100}, headers=headers)
    top_up.raise_for_status()

    task_ids = []
    for number in range(6):
        response = client.post(
            "/predict",
            json={
                "model": "sum",
                "features": {"x1": number, "x2": number + 1},
            },
            headers=headers,
        )
        response.raise_for_status()
        task_ids.append(response.json()["task_id"])

    deadline = time.time() + 30
    pending = set(task_ids)
    while pending and time.time() < deadline:
        for task_id in list(pending):
            response = client.get(f"/predict/{task_id}", headers=headers)
            response.raise_for_status()
            task = response.json()
            if task["status"] in {"completed", "failed"}:
                print(task)
                pending.remove(task_id)
        if pending:
            time.sleep(1)

    if pending:
        raise RuntimeError(f"Не обработано задач: {len(pending)}")

print("Проверьте распределение: docker compose logs worker-1 worker-2")

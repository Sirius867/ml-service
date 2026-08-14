import unittest

from fastapi.testclient import TestClient

from app.src.main import create_app


class WebInterfaceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(initialize=False))

    def tearDown(self) -> None:
        self.client.close()

    def test_web_pages_are_available(self) -> None:
        pages = {
            "/": "Простые ML-предсказания",
            "/auth": "Регистрация",
            "/dashboard": "Новое предсказание",
            "/history": "История операций",
        }
        for path, expected_text in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers["content-type"])
                self.assertIn(expected_text, response.text)

    def test_static_files_are_available(self) -> None:
        files = (
            "/static/css/styles.css",
            "/static/js/common.js",
            "/static/js/auth.js",
            "/static/js/dashboard.js",
            "/static/js/history.js",
        )
        for path in files:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.text.strip())

    def test_dashboard_contains_required_controls(self) -> None:
        response = self.client.get("/dashboard")
        self.assertIn('id="top-up-form"', response.text)
        self.assertIn('id="prediction-form"', response.text)
        self.assertIn('id="features-file"', response.text)
        self.assertIn('id="processed-data"', response.text)
        self.assertIn('id="invalid-data"', response.text)


if __name__ == "__main__":
    unittest.main()

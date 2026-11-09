import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from app import app, initialize_db


def setup_module():
    initialize_db()


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_lookup_returns_known_product():
    client = app.test_client()
    response = client.get("/lookup?name=keyboard")
    assert response.status_code == 200
    assert response.get_json()["results"][0]["name"] == "keyboard"

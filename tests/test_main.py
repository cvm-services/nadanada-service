"""HTTP surface: health + the contract. No HTTP messages endpoint exists."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app


def _client():
    return TestClient(create_app(Config(dashboard_url="")))


def test_health_reports_ok():
    r = _client().get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "nadanada"
    assert body["surface"] == "cvm"


def test_contract_is_served_at_the_advertised_path():
    r = _client().get("/cvm/llms.txt")
    assert r.status_code == 200
    assert "phone.messages.list" in r.text
    assert "cvm:service:phone-inbox" in r.text


def test_llms_full_is_served():
    r = _client().get("/llms-full.txt")
    assert r.status_code == 200
    assert "nadanada-service" in r.text

"""The REST backend for API-purchased numbers (offline, via httpx MockTransport)."""
from __future__ import annotations

import httpx
import pytest

from app.config import Config
from app.nadanada_dashboard import (
    ApiFetcher,
    PlaywrightFetcher,
    parse_snapshot,
    reader_for,
)

NUMBER = "+447366934621"


def _client(numbers_status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/phone/numbers":
            if numbers_status != 200:
                return httpx.Response(numbers_status, json={"error": "Invalid credentials"})
            return httpx.Response(200, json={
                "numbers": [{"phoneNumber": NUMBER, "totalMessages": 1}]})
        if request.url.path.startswith("/api/v2/phone/messages/"):
            return httpx.Response(200, json={"messages": [
                {"id": "m1", "from": "OpenAI", "body": "code 123456",
                 "receivedAt": "2026-10-06T10:00:00Z"}]})
        return httpx.Response(404, json={"error": "not found"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_api_fetcher_reads_numbers_and_messages():
    cfg = Config(reader="api", api_user_id="u", api_user_secret="s")
    raw = ApiFetcher(cfg, client=_client()).fetch()
    snap = parse_snapshot(raw)
    assert [n.number for n in snap.numbers] == [NUMBER]
    assert snap.messages[NUMBER][0].body == "code 123456"


def test_api_fetcher_requires_credentials():
    cfg = Config(reader="api")
    with pytest.raises(RuntimeError, match="API_USER"):
        ApiFetcher(cfg, client=_client()).fetch()


def test_api_401_is_a_clear_error():
    cfg = Config(reader="api", api_user_id="u", api_user_secret="wrong")
    with pytest.raises(RuntimeError, match="auth failed"):
        ApiFetcher(cfg, client=_client(numbers_status=401)).fetch()


def test_reader_for_selects_the_backend():
    assert isinstance(reader_for(Config(reader="api")).fetcher, ApiFetcher)
    assert isinstance(reader_for(Config(reader="playwright")).fetcher, PlaywrightFetcher)

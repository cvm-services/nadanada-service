"""Config is env-driven and must tolerate garbage without taking the service down."""
from __future__ import annotations

from app.config import DEFAULT_RELAYS, Config


def test_defaults_are_sane():
    c = Config.from_env({})
    assert c.service == "nadanada"
    assert c.price_sats == 1000
    assert c.mint_url == "https://testnut.cashu.space"
    assert c.relays == DEFAULT_RELAYS
    assert c.dashboard_url == ""


def test_env_overrides_parse_and_split():
    c = Config.from_env({
        "NADANADA_PRICE_SATS": "2500",
        "NADANADA_RELAYS": "wss://a.example, wss://b.example",
        "NADANADA_BROWSER_HEADLESS": "false",
        "NADANADA_MAX_MESSAGES": "7",
        "NADANADA_DASHBOARD_URL": " https://nadanada.me/phone-numbers/user/tok ",
    })
    assert c.price_sats == 2500
    assert c.relays == ("wss://a.example", "wss://b.example")
    assert c.browser_headless is False
    assert c.max_messages == 7
    assert c.dashboard_url == "https://nadanada.me/phone-numbers/user/tok"


def test_garbage_int_falls_back_to_default():
    c = Config.from_env({"NADANADA_PRICE_SATS": "not-a-number"})
    assert c.price_sats == 1000


def test_overrides_apply():
    c = Config.from_env({}, price_sats=1234)
    assert c.price_sats == 1234

"""The announced contract must match what the service actually charges and does."""
from __future__ import annotations

from app.config import Config
from app.cvm import load_announcement_tags, load_fixture


def _t_values(tags):
    return [t[1] for t in tags if t[0] == "t"]


def test_fixture_conforms_and_declares_the_class():
    tags = load_announcement_tags()
    t = _t_values(tags)
    assert "cvm:service:phone-inbox" in t
    assert "cvm:req:payment.amount" in t
    assert "cvm:tier:financial" in t
    assert t.count("cvm:tier:financial") == 1
    # exactly one tier tag (max-only rule)
    assert len([v for v in t if v.startswith("cvm:tier:")]) == 1


def test_no_geohash_for_a_locationless_service():
    tags = load_announcement_tags()
    assert [t for t in tags if t[0] == "g"] == []


def test_cap_matches_the_configured_price():
    fixture = load_fixture()
    caps = [t for t in fixture["tags"] if t[0] == "cap"]
    assert len(caps) == 1
    assert caps[0][1] == "tool:phone.messages.list"
    assert caps[0][2] == str(Config().price_sats)
    assert caps[0][3] == "sats"
    assert fixture["price_sats"] == Config().price_sats


def test_pmi_declares_cashu_explicit_gating():
    fixture = load_fixture()
    pmi = [t for t in fixture["tags"] if t[0] == "pmi"]
    assert pmi == [["pmi", "bitcoin-cashu", "explicit_gating"]]


def test_contract_url_rides_the_r_tag_not_a_contract_tag():
    fixture = load_fixture()
    rs = [t for t in fixture["tags"] if t[0] == "r"]
    assert fixture["contract_url"] in [r[1] for r in rs]
    assert not [t for t in fixture["tags"] if t[0] == "contract"]

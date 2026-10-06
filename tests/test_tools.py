"""Tool behaviour: owner-free, payment-required, and NIP-44 to the caller."""
from __future__ import annotations

import json

from app import nadanada_tools
from app.cvm import ContractContext
from app.nadanada_dashboard import DashboardSnapshot, Message, PhoneNumber
from app.nadanada_tools import (
    TOOL_MESSAGES_LIST,
    TOOL_NUMBERS_LIST,
    CvmTools,
)
from app.nip44 import decrypt

from tests.conftest import OWNER_SK, SERVER_SK, STRANGER_SK, pub_hex

NUMBER = "+447366934621"


class FakeReader:
    def __init__(self, snap):
        self.snap = snap

    def read(self):
        return self.snap

    def messages_for(self, phone_number, snap):
        if phone_number:
            return list(snap.messages.get(phone_number, []))
        out = {}
        for msgs in snap.messages.values():
            for m in msgs:
                out.setdefault(m.id, m)
        return list(out.values())


class FakeToken:
    def __init__(self, amount):
        self.amount = amount
        self.mint = "https://testnut.cashu.space"
        self.proofs = [{"id": "00", "amount": amount, "secret": "s", "C": "c"}]


class FakeMint:
    mint_url = "https://testnut.cashu.space"

    def check_states(self, proofs):
        return ["UNSPENT"] * len(proofs)

    def fee_ppk_for(self, keyset_id):
        return 0

    def swap(self, inputs, amounts):
        return [{"id": "00", "amount": a, "secret": "x", "C": "y"} for a in amounts]


def _snapshot():
    snap = DashboardSnapshot()
    snap.numbers = [PhoneNumber(number=NUMBER, total_messages=1)]
    snap.messages[NUMBER] = [
        Message(id="m1", from_addr="OpenAI", body="Your code is 123456")]
    return snap


def _tools():
    return CvmTools(FakeReader(_snapshot()), docs={"llms": "contract"},
                    owner_pubkeys={pub_hex(OWNER_SK)}, mint=FakeMint(),
                    contract=ContractContext(), price_sats=1000,
                    server_secret_hex=SERVER_SK, max_messages=50)


def _open(res, sk_hex):
    payload = json.loads(res["content"][0]["text"])
    return json.loads(decrypt(sk_hex, pub_hex(SERVER_SK), payload["ciphertext"]))


def test_numbers_list_is_free_and_reports_the_number():
    res = _tools().call(TOOL_NUMBERS_LIST, {}, caller=pub_hex(STRANGER_SK))
    assert not res.get("isError")
    data = json.loads(res["content"][0]["text"])
    assert [n["number"] for n in data["numbers"]] == [NUMBER]
    assert data["source"] == "dashboard-scrape"


def test_owner_reads_free_and_gets_plaintext_after_decrypt():
    res = _tools().call(TOOL_MESSAGES_LIST, {}, caller=pub_hex(OWNER_SK))
    assert not res.get("isError")
    data = _open(res, OWNER_SK)
    assert data["owner_free"] is True
    assert data["count"] == 1
    assert data["messages"][0]["body"] == "Your code is 123456"


def test_stranger_without_token_is_refused_visibly():
    res = _tools().call(TOOL_MESSAGES_LIST, {}, caller=pub_hex(STRANGER_SK))
    assert res.get("isError") is True
    body = json.loads(res["content"][0]["text"])
    assert body["reason"] == "payment_required"
    assert body["price_sats"] == 1000
    assert body["pmi"] == "bitcoin-cashu"


def test_stranger_pays_and_the_token_is_captured(monkeypatch):
    monkeypatch.setattr(nadanada_tools, "decode_token", lambda token: FakeToken(1000))
    tools = _tools()
    res = tools.call(TOOL_MESSAGES_LIST, {"cashu_token": "cashuBxxx"},
                     caller=pub_hex(STRANGER_SK))
    assert not res.get("isError"), res
    data = _open(res, STRANGER_SK)
    assert data["owner_free"] is False
    assert len(tools.payments) == 1 and tools.payments[0]["sats"] == 1000


def test_underpaid_token_is_refused(monkeypatch):
    monkeypatch.setattr(nadanada_tools, "decode_token", lambda token: FakeToken(100))
    res = _tools().call(TOOL_MESSAGES_LIST, {"cashu_token": "cashuBxxx"},
                        caller=pub_hex(STRANGER_SK))
    assert res.get("isError") is True
    assert json.loads(res["content"][0]["text"])["reason"] == "insufficient_funds"


def test_unknown_tool_is_a_visible_error():
    res = _tools().call("phone.nuke", {}, caller=pub_hex(OWNER_SK))
    assert res.get("isError") is True
    assert json.loads(res["content"][0]["text"])["reason"] == "unsupported method"

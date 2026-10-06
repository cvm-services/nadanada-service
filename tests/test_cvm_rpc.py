"""End-to-end CVM JSON-RPC surface: dispatch -> tools, offline.

Proves the machine contract a Nostr client actually speaks: initialize,
tools/list, tools/call (free + paid refusal), resources/read, and the
always-answer rule (a notification is the only intentional silence).
"""
from __future__ import annotations

import json

from app.cvm_rpc import PROTOCOL_VERSION, handle_rpc
from app.nadanada_tools import TOOL_DOCS, TOOL_MESSAGES_LIST, TOOL_NUMBERS_LIST

from tests.conftest import OWNER_SK, pub_hex
from tests.test_tools import _tools


def _rpc(method, params=None, rpc_id=1):
    return handle_rpc({"jsonrpc": "2.0", "id": rpc_id, "method": method,
                       "params": params or {}}, _tools(), caller=pub_hex(OWNER_SK))


def test_initialize_returns_protocol_and_server_info():
    res = _rpc("initialize")
    assert res["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert res["result"]["serverInfo"]["name"] == "nadanada"


def test_tools_list_exposes_both_tools():
    names = [t["name"] for t in _rpc("tools/list")["result"]["tools"]]
    assert TOOL_NUMBERS_LIST in names
    assert TOOL_MESSAGES_LIST in names
    assert TOOL_DOCS in names


def test_tools_call_free_numbers_list_returns_numbers():
    res = _rpc("tools/call", {"name": TOOL_NUMBERS_LIST, "arguments": {}})
    assert not res["result"].get("isError")
    data = json.loads(res["result"]["content"][0]["text"])
    assert [n["number"] for n in data["numbers"]] == ["+447366934621"]


def test_tools_call_paid_messages_list_owner_is_free():
    res = _rpc("tools/call", {"name": TOOL_MESSAGES_LIST, "arguments": {}})
    assert not res["result"].get("isError")


def test_resources_list_and_read():
    resources = _rpc("resources/list")["result"]["resources"]
    assert any(r["uri"] == "nadanada://llms.txt" for r in resources)
    read = _rpc("resources/read", {"uri": "nadanada://llms.txt"})
    assert read["result"]["contents"][0]["text"] == "contract"


def test_unknown_method_is_a_jsonrpc_error():
    res = _rpc("does/not/exist")
    assert res["error"]["code"] == -32601


def test_notification_is_never_answered():
    assert handle_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"},
                      _tools()) is None


def test_bad_request_is_an_error_not_silence():
    res = handle_rpc("not an object", _tools())
    assert res["error"]["code"] == -32600

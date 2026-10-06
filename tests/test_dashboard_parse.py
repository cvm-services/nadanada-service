"""The pure parser: JSON-first, then rendered text. Never fabricates."""
from __future__ import annotations

import json

from app.nadanada_dashboard import parse_snapshot


def test_parses_messages_from_captured_json():
    body = json.dumps({
        "phoneNumber": "+447366934621",
        "messages": [
            {"id": "a1", "from": "OpenAI", "body": "Your code is 123456",
             "receivedAt": "2026-10-06T10:00:00Z", "read": False},
            {"id": "a2", "fromAddr": "+15550001111", "text": "hello",
             "timestamp": "2026-10-06T09:00:00Z", "isRead": True},
        ],
    })
    snap = parse_snapshot({"json": [{"url": "https://x/api", "body": body}], "text": "", "html": ""})
    assert [n.number for n in snap.numbers] == ["+447366934621"]
    msgs = snap.messages["+447366934621"]
    assert {m.id for m in msgs} == {"a1", "a2"}
    assert msgs[0].body == "Your code is 123456"
    assert msgs[0].read is False
    assert msgs[1].from_addr == "+15550001111"


def test_empty_dashboard_is_labelled_not_fabricated():
    html = "<html><body><h1>Your Phone Numbers</h1><div>+447366934621</div>" \
           "<div>Total Messages 0</div><div>Expires: 1/6/2027</div></body></html>"
    snap = parse_snapshot({"json": [], "text": "Total Messages 0 Expires: 1/6/2027",
                           "html": html})
    assert [n.number for n in snap.numbers] == ["+447366934621"]
    assert snap.numbers[0].total_messages == 0
    assert snap.numbers[0].expires == "1/6/2027"
    assert snap.messages["+447366934621"] == []
    assert snap.source == "dashboard-scrape"
    assert any("no message-shaped JSON" in n for n in snap.notes)


def test_no_number_notes_the_gap():
    snap = parse_snapshot({"json": [], "text": "nothing here", "html": ""})
    assert snap.numbers == []
    assert any("no E.164 number" in n for n in snap.notes)


def test_parser_handles_multiple_numbers_without_attribution():
    body = json.dumps({"numbers": ["+447366934621", "+447700900123"], "messages": []})
    snap = parse_snapshot({"json": [{"url": "u", "body": body}], "text": "", "html": ""})
    assert set(n.number for n in snap.numbers) == {"+447366934621", "+447700900123"}
    assert "*" in snap.messages

"""Read the operator's nadanada number dashboard.

nadanada separates *website* numbers from *API* numbers: a number bought on the
website is not readable through the REST API, and its private dashboard
(`https://nadanada.me/phone-numbers/user/<token>`) sits behind a Cloudflare
non-interactive challenge. So the reader drives a real browser.

Two layers, deliberately split:

* ``parse_snapshot(raw)`` is PURE. It turns captured JSON responses / rendered
  text into a :class:`DashboardSnapshot`. It is what the unit tests exercise
  (against recorded fixtures) with no browser.
* ``PlaywrightFetcher`` produces ``raw``. It is the only part that needs a
  browser and a network, so it is omitted from unit coverage and proven by the
  live evidence run.

Honesty rule: a read that finds nothing returns an explicit, labelled empty
snapshot (with ``notes`` describing what was seen), never fabricated data.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

#: keys that carry a message body, in preference order.
_BODY_KEYS = ("body", "text", "content", "message", "messageText", "msg")
#: keys that carry the sender.
_FROM_KEYS = ("from", "fromAddr", "sender", "fromNumber", "source", "originator")
#: keys that carry a timestamp.
_TIME_KEYS = ("receivedAt", "createdAt", "timestamp", "date", "received_at", "time")
#: keys that carry an id.
_ID_KEYS = ("id", "messageId", "uuid", "_id")
#: keys that carry a phone number (string).
_NUMBER_KEYS = ("phoneNumber", "number", "numbers", "msisdn", "phone", "did")
#: keys that carry a list of messages.
_MESSAGE_LIST_KEYS = ("messages", "sms", "items", "data", "results")

_E164 = re.compile(r"\+[1-9]\d{6,14}")


@dataclass
class Message:
    id: str
    from_addr: str
    body: str
    received_at: str | None = None
    read: bool | None = None

    def as_dict(self) -> dict:
        return {"id": self.id, "from": self.from_addr, "body": self.body,
                "received_at": self.received_at, "read": self.read}


@dataclass
class PhoneNumber:
    number: str
    total_messages: int | None = None
    expires: str | None = None

    def as_dict(self) -> dict:
        return {"number": self.number, "total_messages": self.total_messages,
                "expires": self.expires}


@dataclass
class DashboardSnapshot:
    numbers: list[PhoneNumber] = field(default_factory=list)
    messages: dict[str, list[Message]] = field(default_factory=dict)
    source: str = "dashboard-scrape"
    as_of: float = field(default_factory=time.time)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "as_of": self.as_of,
            "numbers": [n.as_dict() for n in self.numbers],
            "messages": {k: [m.as_dict() for m in v] for k, v in self.messages.items()},
            "notes": self.notes,
        }


def _first(d: dict, keys) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _looks_like_message(d: dict) -> bool:
    if not isinstance(d, dict):
        return False
    body = _first(d, _BODY_KEYS)
    sender = _first(d, _FROM_KEYS)
    return isinstance(body, str) and body.strip() != "" and (sender is not None or
                                                             _first(d, _TIME_KEYS) is not None)


def _normalize_message(d: dict, idx: int) -> Message:
    body = _first(d, _BODY_KEYS) or ""
    sender = _first(d, _FROM_KEYS) or "unknown"
    ts = _first(d, _TIME_KEYS)
    ident = _first(d, _ID_KEYS)
    read = d.get("read", d.get("isRead"))
    return Message(
        id=str(ident) if ident is not None else f"m{idx}",
        from_addr=str(sender),
        body=str(body),
        received_at=str(ts) if ts is not None else None,
        read=bool(read) if read is not None else None,
    )


def _collect_messages(obj: Any, out: list[Message]) -> None:
    """Recursively walk decoded JSON, collecting message-shaped dicts."""
    if isinstance(obj, dict):
        for key in _MESSAGE_LIST_KEYS:
            val = obj.get(key)
            if isinstance(val, list):
                for item in val:
                    if _looks_like_message(item):
                        out.append(_normalize_message(item, len(out)))
        if _looks_like_message(obj):
            out.append(_normalize_message(obj, len(out)))
        for val in obj.values():
            if isinstance(val, (dict, list)):
                _collect_messages(val, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_messages(item, out)


def _collect_numbers(obj: Any, out: list[str]) -> None:
    if isinstance(obj, dict):
        for key in _NUMBER_KEYS:
            val = obj.get(key)
            items = [val] if isinstance(val, str) else (val if isinstance(val, list) else [])
            for s in items:
                m = _E164.search(s) if isinstance(s, str) else None
                if m:
                    out.append(m.group(0))
        for val in obj.values():
            if isinstance(val, (dict, list)):
                _collect_numbers(val, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_numbers(item, out)


def parse_snapshot(raw: dict) -> DashboardSnapshot:
    """Turn captured JSON responses / text / html into a snapshot. Pure."""
    snap = DashboardSnapshot()
    json_bodies = raw.get("json") or []
    messages: list[Message] = []
    numbers: list[str] = []
    for entry in json_bodies:
        body = entry.get("body") if isinstance(entry, dict) else entry
        if isinstance(body, str):
            try:
                import json as _json
                body = _json.loads(body)
            except Exception:                                  # noqa: BLE001
                continue
        _collect_messages(body, messages)
        _collect_numbers(body, numbers)

    text = (raw.get("text") or "") + "\n" + (raw.get("html") or "")
    numbers.extend(m.group(0) for m in _E164.finditer(text))
    if not messages:
        snap.notes.append("no message-shaped JSON found in captured responses; "
                          "see evidence screenshot / raw dump")

    # de-dupe numbers, preserve order
    seen = set()
    uniq_numbers = [n for n in numbers if not (n in seen or seen.add(n))]
    total = None
    m = re.search(r"Total Messages\s*(\d+)", text)
    if m:
        total = int(m.group(1))
    expires = None
    m = re.search(r"Expires:?\s*([0-9/.\-]+)", text)
    if m:
        expires = m.group(1)

    if not uniq_numbers:
        snap.notes.append("no E.164 number found in captured responses or page text")
    snap.numbers = [PhoneNumber(number=n, total_messages=total, expires=expires)
                    for n in uniq_numbers]
    # With one number, its messages are the whole set; with several, we cannot
    # attribute reliably, so the caller must pass phone_number to filter.
    if len(snap.numbers) == 1:
        snap.messages[snap.numbers[0].number] = messages
    elif snap.numbers:
        for n in snap.numbers:
            snap.messages.setdefault(n.number, [])
        snap.messages.setdefault("*", messages)
    else:
        snap.messages["*"] = messages
    return snap


class DashboardReader:
    """Read the dashboard through an injected fetcher (Playwright in prod)."""

    def __init__(self, config, fetcher=None):
        self.config = config
        self.fetcher = fetcher or PlaywrightFetcher(config)

    def read(self) -> DashboardSnapshot:
        return parse_snapshot(self.fetcher.fetch())

    def messages_for(self, phone_number: str | None, snap: DashboardSnapshot) -> list[Message]:
        if phone_number:
            return list(snap.messages.get(phone_number, []))
        # no filter: return the union, de-duplicated by id
        seen: dict[str, Message] = {}
        for msgs in snap.messages.values():
            for m in msgs:
                seen.setdefault(m.id, m)
        return list(seen.values())


class PlaywrightFetcher:
    """Produce ``raw`` (captured JSON + rendered text/html) via a real browser.

    Not unit-tested: needs a browser. Proven by scripts/discover_dashboard.py and
    the live evidence run.
    """

    def __init__(self, config):
        self.config = config

    def fetch(self) -> dict:
        if not self.config.dashboard_url:
            raise RuntimeError("NADANADA_DASHBOARD_URL is not set")
        from playwright.sync_api import sync_playwright

        profile = f"{self.config.state_dir.rstrip('/')}/chromium-profile"
        import pathlib
        pathlib.Path(profile).mkdir(parents=True, exist_ok=True)

        captured: list[dict] = []
        with sync_playwright() as pw:
            launch_kwargs = {"headless": self.config.browser_headless}
            if self.config.browser_channel and self.config.browser_channel != "chromium":
                launch_kwargs["channel"] = self.config.browser_channel
            context = pw.chromium.launch_persistent_context(
                profile, args=["--no-sandbox"], **launch_kwargs)
            page = context.new_page()
            page.on("response", lambda r: _capture_json(r, captured))
            page.goto(self.config.dashboard_url, wait_until="domcontentloaded",
                      timeout=self.config.page_timeout_ms)
            # give the client app + any CF challenge time to resolve
            try:
                page.wait_for_load_state("networkidle", timeout=self.config.page_timeout_ms)
            except Exception:                                  # noqa: BLE001
                pass
            html = page.content()
            try:
                text = page.inner_text("body")
            except Exception:                                  # noqa: BLE001
                text = ""
            context.close()
        return {"json": captured, "html": html, "text": text}


def _capture_json(response, sink: list[dict]) -> None:
    try:
        ctype = (response.headers or {}).get("content-type", "")
        if "json" not in ctype.lower():
            return
        if response.request.resource_type not in ("xhr", "fetch"):
            return
        sink.append({"url": response.url, "body": response.text()})
    except Exception:                                          # noqa: BLE001
        return

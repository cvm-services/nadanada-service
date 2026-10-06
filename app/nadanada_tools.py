"""nadanada-service CVM tool surface — MCP tools over Nostr with CEP-8 postage.

Two tools, one contract:

* ``phone.numbers.list`` — free, read-only. The numbers on the dashboard.
* ``phone.messages.list`` — PAID (CEP-8 ``explicit_gating``). The operator
  (owner npub) reads free; everyone else must attach a Cashu token. The result
  is a NIP-44 v2 payload **encrypted to the caller's npub** — message bodies are
  OTPs, so plaintext never leaves the service.

Design rules, each one a test:

* **A refusal is visible.** Every branch returns an MCP result or an
  ``isError`` result; nothing is silent.
* **Nothing is read before payment lands** for a non-owner caller, and the
  token is captured with a NUT-03 swap (value genuinely held, not assumed).
* **The secret never travels.** The dashboard URL is held server-side and is not
  in any tool result or announcement.
* **Owner reads free.** Charging yourself is pointless.
"""
from __future__ import annotations

import secrets
import time
from typing import Any

from .cashu import CashuError, decode_token, fee_for, split_amounts
from .cvm import (
    SERVER_ABOUT,
    SERVER_NAME,
    SERVER_VERSION,
    ContractContext,
    ToolError,
    mcp_tool_error,
    mcp_tool_result,
)
from .nip44 import Nip44Error, encrypt

TOOL_NUMBERS_LIST = "phone.numbers.list"
TOOL_MESSAGES_LIST = "phone.messages.list"
TOOL_DOCS = "docs"
DOCS_ALIASES = (TOOL_DOCS, "llms")
DOCS_FULL_ALIASES = ("llms-full", "llms_full")

FREE_TOOLS = (TOOL_NUMBERS_LIST, TOOL_DOCS, "llms", "llms-full", "llms_full")


class CvmTools:
    """The MCP tool surface. Reader, mint, docs and key are injected."""

    def __init__(self, reader, docs: dict[str, str] | None = None,
                 owner_pubkeys: set[str] | None = None, *,
                 mint=None, contract: ContractContext | None = None,
                 price_sats: int = 1000, server_secret_hex: str = "",
                 max_messages: int = 50):
        self.reader = reader
        self.docs = docs or {}
        self.owner_pubkeys = {p.lower() for p in (owner_pubkeys or set())}
        self.mint = mint
        self.contract = contract or ContractContext()
        self.price_sats = int(price_sats)
        self.server_secret_hex = server_secret_hex
        self.max_messages = int(max_messages)
        self.payments: list[dict] = []

    # --- free tools -------------------------------------------------------

    def phone_numbers_list(self) -> dict:
        snap = self.reader.read()
        return {
            "source": snap.source,
            "as_of": snap.as_of,
            "numbers": [n.as_dict() for n in snap.numbers],
            "notes": snap.notes,
        }

    # --- paid tool --------------------------------------------------------

    def _capture_payment(self, token: str, price: int, caller: str) -> dict:
        """Capture a Cashu token with a NUT-03 swap for a read (no refund path)."""
        if self.mint is None:
            raise ToolError("rail_not_configured",
                            "No mint is configured; postage cannot be escrowed.")
        try:
            token_obj = decode_token(token)
        except CashuError as exc:
            raise ToolError(exc.reason, exc.hint) from exc
        mint_url = getattr(self.mint, "mint_url", None)
        if mint_url and token_obj.mint.rstrip("/") != str(mint_url).rstrip("/"):
            raise ToolError("token_wrong_mint",
                            f"This service escrows against {mint_url}; that token is "
                            f"from {token_obj.mint}.")
        states = list(self.mint.check_states(token_obj.proofs))
        if any(str(s) == "SPENT" for s in states):
            raise ToolError("token_already_spent", "At least one proof was already redeemed.")
        if any(str(s) != "UNSPENT" for s in states):
            raise ToolError("token_state_unknown", "The mint reports a non-final proof state.")
        try:
            ppk = int(self.mint.fee_ppk_for(token_obj.proofs[0]["id"]))
        except Exception:                                      # noqa: BLE001
            ppk = 0
        mint_fee = fee_for(ppk, len(token_obj.proofs))
        net = token_obj.amount - mint_fee
        if net < price:
            raise ToolError(
                "insufficient_funds",
                f"token is {token_obj.amount} sats; the price is {price} sats "
                f"(short {price - net}; the mint takes a {mint_fee} sat input fee).",
                shortfall_sats=price - net, price_sats=price,
                token_sats=token_obj.amount, mint_fee_sats=mint_fee, net_sats=net)
        change = net - price
        keep_amounts = split_amounts(price)
        change_amounts = split_amounts(change)
        try:
            captured = list(self.mint.swap(token_obj.proofs, keep_amounts + change_amounts))
        except CashuError as exc:
            raise ToolError("mint_error", exc.hint) from exc
        except Exception as exc:                               # noqa: BLE001
            raise ToolError("mint_error",
                            f"Escrow swap failed ({type(exc).__name__}); no sats taken."
                            ) from exc
        self.payments.append({"caller": caller, "sats": price, "at": time.time()})
        return {"escrow_proofs": captured[:len(keep_amounts)],
                "change_proofs": captured[len(keep_amounts):],
                "change_sats": change, "mint_fee": mint_fee,
                "token_sats": token_obj.amount}

    def _encrypt_to_caller(self, caller: str, payload: dict) -> dict:
        import json
        if not self.server_secret_hex:
            raise ToolError("no_server_key",
                            "The server has no NIP-44 key, so it cannot address the "
                            "caller privately; refusing rather than leaking in the clear.")
        if not caller:
            raise ToolError("no_caller",
                            "A caller npub is required to address the encrypted payload.")
        try:
            ciphertext = encrypt(self.server_secret_hex, caller, json.dumps(payload))
        except Nip44Error as exc:                              # noqa: BLE001
            raise ToolError("encrypt_failed", str(exc)) from exc
        return {"enc": "nip44-v2", "to": caller, "ciphertext": ciphertext,
                "issued_at": int(time.time())}

    def phone_messages_list(self, caller: str = "", cashu_token: str | None = None,
                            settlement_receipt: str | None = None,
                            phone_number: str | None = None,
                            limit: int | None = None) -> dict:
        owner = caller.lower() in self.owner_pubkeys
        if not owner:
            if cashu_token:
                self._capture_payment(cashu_token, self.price_sats, caller)
            elif not settlement_receipt:
                raise ToolError(
                    "payment_required",
                    "CEP-8 explicit_gating: attach a Cashu token (or a settlement "
                    "receipt) — nothing is read before payment lands.",
                    cap=f"cap:tool:{TOOL_MESSAGES_LIST}:{self.price_sats}:sats",
                    price_sats=self.price_sats, pmi="bitcoin-cashu",
                    gating="explicit_gating")

        snap = self.reader.read()
        msgs = self.reader.messages_for(phone_number, snap)
        cap = self.max_messages if limit is None else min(int(limit), self.max_messages)
        msgs = msgs[:cap]

        payload: dict[str, Any] = {
            "source": snap.source,
            "as_of": snap.as_of,
            "phone_number": phone_number,
            "count": len(msgs),
            "messages": [m.as_dict() for m in msgs],
            "notes": list(snap.notes),
            "owner_free": owner,
        }
        if not msgs:
            payload["notes"].append(
                "no messages matched; the number may simply have none right now")
        return self._encrypt_to_caller(caller, payload)

    # --- docs / resources -------------------------------------------------

    def docs_tool(self, name: str = TOOL_DOCS) -> str:
        key = "llms-full" if name in DOCS_FULL_ALIASES else "llms"
        if key not in self.docs:
            raise ToolError("not_found", f"Document {key!r} is not bundled.")
        return self.docs[key]

    def resource_list(self) -> list[dict]:
        return [
            {"uri": "nadanada://llms.txt", "name": "llms.txt",
             "description": "The nadanada-service contract, verbatim.",
             "mimeType": "text/plain"},
            {"uri": "nadanada://llms-full.txt", "name": "llms-full.txt",
             "description": "The nadanada-service manual.", "mimeType": "text/plain"},
        ]

    def read_resource(self, uri: str) -> str:
        key = "llms-full" if str(uri).endswith("llms-full.txt") else "llms"
        if key not in self.docs:
            raise ToolError("not_found", f"Document {key!r} is not bundled.")
        return self.docs[key]

    # --- MCP dispatch -----------------------------------------------------

    def tool_definitions(self) -> list[dict]:
        return [
            {"name": TOOL_NUMBERS_LIST,
             "description": "List the rented numbers on the dashboard (free, read-only).",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": TOOL_MESSAGES_LIST,
             "description": (f"Read inbound SMS (PAID, {self.price_sats} sats). "
                             "Owner reads free. The result is a NIP-44 v2 payload "
                             "encrypted to the caller's npub."),
             "inputSchema": {"type": "object",
                             "properties": {"phone_number": {"type": "string"},
                                            "limit": {"type": "integer"},
                                            "cashu_token": {"type": "string"},
                                            "settlement_receipt": {"type": "string"}}}},
            {"name": TOOL_DOCS,
             "description": "The llms.txt contract, verbatim (free). Alias: llms.",
             "inputSchema": {"type": "object",
                             "properties": {"name": {"type": "string"}}}},
        ]

    def capability_tags(self) -> list[list[str]]:
        return [
            ["cap", f"tool:{TOOL_MESSAGES_LIST}", str(self.price_sats), "sats"],
            ["pmi", "bitcoin-cashu", "explicit_gating"],
        ]

    def server_announcement(self) -> dict:
        return {"name": SERVER_NAME, "about": SERVER_ABOUT,
                "version": SERVER_VERSION,
                "class": "phone-inbox",
                "tools": [t["name"] for t in self.tool_definitions()],
                "docs": {"url": self.contract.contract_url, "tool": TOOL_DOCS,
                         "alias": "llms"}}

    def call(self, tool: str, args: dict | None = None, caller: str = "") -> dict:
        """Dispatch one MCP tools/call and ALWAYS return a reply."""
        args = args or {}
        try:
            if tool == TOOL_NUMBERS_LIST:
                return mcp_tool_result(self.phone_numbers_list())
            if tool == TOOL_MESSAGES_LIST:
                return mcp_tool_result(self.phone_messages_list(
                    caller=caller, cashu_token=args.get("cashu_token"),
                    settlement_receipt=args.get("settlement_receipt"),
                    phone_number=args.get("phone_number"), limit=args.get("limit")))
            if tool in DOCS_ALIASES or tool in DOCS_FULL_ALIASES:
                default = "llms-full" if tool in DOCS_FULL_ALIASES else "llms"
                name = args.get("name") or default
                if "name" in args and name not in DOCS_ALIASES + DOCS_FULL_ALIASES:
                    raise ToolError("not_found", f"No contract document named {name!r}.")
                return {"content": [{"type": "text", "text": self.docs_tool(name)}]}
            raise ToolError("unsupported method", f"Unknown tool {tool!r}.")
        except ToolError as exc:
            return mcp_tool_error(exc.reason, exc.hint, **exc.extra)

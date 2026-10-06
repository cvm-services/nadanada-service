"""Run the nadanada-service ContextVM server over real Nostr relays.

Wire layer only: it owns the relay client, the gift-wrap envelope, the CEP-6
announcements, and dispatch into :mod:`app.cvm_rpc` / :mod:`app.nadanada_tools`.
Tool logic is pure and lives in the modules under test.

Usage
-----
    python3 scripts/run_cvm_server.py --announce     # publish catalog and exit
    python3 scripts/run_cvm_server.py                # announce, then serve

Environment
-----------
CVM_NSEC               server private key (nsec or hex); generated to --key-file
                       when absent, so a restart keeps the same npub.
CVM_OWNER_PUBKEYS      comma-separated hex pubkeys that read free (the operator).
NADANADA_DASHBOARD_URL the private dashboard URL (secret).
NADANADA_MINT_URL      mint postage tokens are escrowed against.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.cashu import MintClient                                    # noqa: E402
from app.config import Config                                       # noqa: E402
from app.cvm import (                                               # noqa: E402
    ANNOUNCE_RESOURCES,
    ANNOUNCE_SERVER,
    ANNOUNCE_TOOLS,
    CVM_MESSAGE_KIND,
    GIFT_WRAP_KINDS,
    ContractContext,
    WORKING_RELAYS,
    load_announcement_tags,
)
from app.cvm_rpc import handle_rpc                                  # noqa: E402
from app.main import load_docs                                      # noqa: E402
from app.nadanada_dashboard import reader_for                       # noqa: E402
from app.nadanada_tools import CvmTools                             # noqa: E402


def tag_values(tag) -> list[str]:
    return tag.as_vec()


def p_tag_of(event) -> str | None:
    for tag in event.tags().to_vec():
        values = tag_values(tag)
        if values and values[0] == "p":
            return values[1]
    return None


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--relays", nargs="+", default=list(WORKING_RELAYS))
    ap.add_argument("--key-file", default=str(REPO / ".cvm-server.nsec"))
    ap.add_argument("--announce", action="store_true",
                    help="publish the CEP-6 catalog and exit")
    args = ap.parse_args()

    cfg = Config.from_env()
    if not cfg.dashboard_url:
        print("[nadanada-cvm] WARNING: NADANADA_DASHBOARD_URL is unset; reads will fail",
              file=sys.stderr)

    from nostr_sdk import (ClientBuilder, EventBuilder, Filter, HandleNotification,
                           Keys, Kind, NostrSigner, RelayUrl, Tag)

    key_file = pathlib.Path(args.key_file)
    if os.environ.get("CVM_NSEC"):
        keys = Keys.parse(os.environ["CVM_NSEC"])
    elif key_file.exists():
        keys = Keys.parse(key_file.read_text().strip())
    else:
        keys = Keys.generate()
        key_file.write_text(keys.secret_key().to_bech32())
        key_file.chmod(0o600)
        print(f"[nadanada-cvm] generated a server key -> {key_file}")

    npub = keys.public_key().to_bech32()
    owners = {p.strip().lower() for p in
              os.environ.get("CVM_OWNER_PUBKEYS", "").split(",") if p.strip()}

    reader = reader_for(cfg)
    mint = MintClient(cfg.mint_url) if cfg.mint_url else None
    contract = ContractContext(npub=npub, relays=tuple(args.relays),
                               contract_url=cfg.contract_url)
    tools = CvmTools(reader, docs=load_docs(), owner_pubkeys=owners, mint=mint,
                     contract=contract, price_sats=cfg.price_sats,
                     server_secret_hex=keys.secret_key().to_hex(),
                     max_messages=cfg.max_messages)

    signer = NostrSigner.keys(keys)
    client = ClientBuilder().signer(signer).build()
    for url in args.relays:
        try:
            await client.add_relay(RelayUrl.parse(url))
        except Exception as exc:                                   # noqa: BLE001
            print(f"[nadanada-cvm] add_relay failed {url}: {exc}", file=sys.stderr)
    await client.connect()

    print(f"[nadanada-cvm] server npub {npub}")
    print(f"[nadanada-cvm] class       cvm:service:phone-inbox")
    print(f"[nadanada-cvm] price       {cfg.price_sats} sats / phone.messages.list")
    print(f"[nadanada-cvm] relays      {', '.join(args.relays)}")

    async def announce() -> None:
        server_info = tools.server_announcement()
        payloads = [
            (ANNOUNCE_SERVER, json.dumps(server_info)),
            (ANNOUNCE_TOOLS, json.dumps({"tools": tools.tool_definitions(), **server_info})),
            (ANNOUNCE_RESOURCES, json.dumps({"resources": tools.resource_list()})),
        ]
        # The conformant tags come from the kit-emitted golden fixture, not from
        # a hand-rolled builder here.
        tags = load_announcement_tags()
        for kind, content in payloads:
            builder = EventBuilder(Kind(kind), content).tags(
                [Tag.parse(t) for t in tags])
            try:
                out = await client.send_event_builder(builder)
                print(f"[nadanada-cvm] announcement kind {kind}: {out}")
            except Exception as exc:                               # noqa: BLE001
                print(f"[nadanada-cvm] announce kind {kind} failed: {exc}",
                      file=sys.stderr)

    await announce()
    if args.announce:
        await asyncio.sleep(2)
        await client.shutdown()
        return 0

    class Handler(HandleNotification):
        async def handle(self, relay_url, subscription_id, event):
            if event.kind().as_u16() not in GIFT_WRAP_KINDS:
                return
            if p_tag_of(event) != keys.public_key().to_hex():
                return
            try:
                unwrapped = await client.unwrap_gift_wrap(event)
            except Exception as exc:                               # noqa: BLE001
                print(f"[nadanada-cvm] unwrap failed: {exc}", file=sys.stderr)
                return
            rumor = unwrapped.rumor()
            if rumor.kind().as_u16() != CVM_MESSAGE_KIND:
                return
            try:
                rpc = json.loads(rumor.content())
            except Exception:                                      # noqa: BLE001
                return
            caller = unwrapped.sender().to_hex()
            print(f"[nadanada-cvm] {rpc.get('method')} id={rpc.get('id')} from={caller[:12]}")
            response = handle_rpc(rpc, tools, caller=caller)
            if response is None:
                return
            reply = EventBuilder(Kind(CVM_MESSAGE_KIND), json.dumps(response)).tags(
                [Tag.public_key(unwrapped.sender())]).build(keys.public_key())
            try:
                out = await client.gift_wrap(unwrapped.sender(), reply, [])
                err = " isError" if (response.get("result") or {}).get("isError") else ""
                print(f"[nadanada-cvm] replied -> {out}{err}")
            except Exception as exc:                               # noqa: BLE001
                print(f"[nadanada-cvm] reply failed: {exc}", file=sys.stderr)

        async def handle_msg(self, relay_url, msg):
            pass

    asyncio.get_running_loop().create_task(client.handle_notifications(Handler()))
    await client.subscribe(Filter().kinds([Kind(1059), Kind(21059)]))
    print("[nadanada-cvm] listening (broad kind 1059/21059, p-tag filtered client-side)")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await client.shutdown()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        pass

"""nadanada-service ASGI app: health + the machine contract.

The primary surface is the CVM (MCP over Nostr, see scripts/run_cvm_server.py).
This HTTP app exists so the contract is fetchable at the advertised URL and so a
human/agent can health-check the service. There is deliberately no HTTP tool
that reads messages: the paid, npub-addressed, NIP-44-encrypted surface is the
CVM.
"""
from __future__ import annotations

import pathlib

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from .config import Config

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACT_DIR = REPO / "docs" / "cvm"


def load_docs(contract_dir: pathlib.Path | None = None) -> dict[str, str]:
    d = contract_dir or CONTRACT_DIR
    docs: dict[str, str] = {}
    for key, name in (("llms", "llms.txt"), ("llms-full", "llms-full.txt")):
        p = d / name
        docs[key] = p.read_text() if p.exists() else ""
    return docs


def create_app(config: Config | None = None, *, tools=None) -> FastAPI:
    cfg = config or Config.from_env()
    app = FastAPI(title="nadanada-service", version=cfg.version)
    docs = load_docs()

    if tools is None:
        from .nadanada_dashboard import DashboardReader
        from .nadanada_tools import CvmTools
        tools = CvmTools(DashboardReader(cfg), docs=docs,
                         mint=None, price_sats=cfg.price_sats,
                         max_messages=cfg.max_messages)
    app.state.config = cfg
    app.state.tools = tools
    app.state.docs = docs

    @app.get("/api/health")
    def health() -> dict:
        return {"service": cfg.service, "version": cfg.version, "commit": cfg.commit,
                "ok": True, "surface": "cvm", "mint": cfg.mint_url}

    @app.get("/llms.txt", response_class=PlainTextResponse)
    def llms() -> str:
        return docs.get("llms", "")

    @app.get("/llms-full.txt", response_class=PlainTextResponse)
    def llms_full() -> str:
        return docs.get("llms-full", "")

    @app.get("/cvm/llms.txt", response_class=PlainTextResponse)
    def cvm_llms() -> str:
        return docs.get("llms", "")

    @app.get("/cvm/llms-full.txt", response_class=PlainTextResponse)
    def cvm_llms_full() -> str:
        return docs.get("llms-full", "")

    @app.get("/api/announcement")
    def announcement(request: Request) -> dict:
        t = request.app.state.tools
        return {"tags": t.server_announcement()}

    return app

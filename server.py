"""nadanada-service ASGI entrypoint.

Local:   python server.py
Prod:    uvicorn server:app --host 127.0.0.1 --port 8089   (behind Caddy on vps2)
"""
from __future__ import annotations

import os

from app.main import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app",
                host=os.environ.get("NADANADA_HOST", "127.0.0.1"),
                port=int(os.environ.get("NADANADA_PORT", "8089")),
                log_level=os.environ.get("NADANADA_LOG_LEVEL", "info"))

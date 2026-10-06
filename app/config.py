"""Runtime configuration for the nadanada-service CVM.

Env-driven; no secrets in code. The dashboard URL is a bearer secret (whoever
holds it can read the number's messages), so it is read from the environment
(OpenBao-injected in production) and never logged.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, replace

#: relays verified for the sibling nosms CVM (2026-10-05).
DEFAULT_RELAYS = (
    "wss://relay.contextvm.org",
    "wss://relay2.contextvm.org",
    "wss://relay.primal.net",
)


def _bool_env(raw, default: bool) -> bool:
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _int_env(raw, default: int) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _git_sha() -> str | None:
    for var in ("NADANADA_COMMIT", "NADANADA_BUILD_SHA", "GIT_COMMIT"):
        val = os.environ.get(var)
        if val:
            return val.strip()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:                                          # noqa: BLE001
        pass
    return None


@dataclass(frozen=True)
class Config:
    service: str = "nadanada"
    version: str = "0.1.0"
    commit: str | None = None

    #: full private dashboard URL, e.g.
    #: https://nadanada.me/phone-numbers/user/<token>  (SECRET).
    dashboard_url: str = ""
    #: where the CVM contract is served, advertised in the CEP-6 catalog.
    contract_url: str = "https://nadanada.orangesync.tech/cvm/llms.txt"

    #: mint every postage token is escrowed against (testnut in dev).
    mint_url: str = "https://testnut.cashu.space"
    #: flat price in sats for one phone.messages.list; MUST equal the cap in the
    #: golden announcement fixture (pinned by tests/test_announcement.py).
    price_sats: int = 1000

    relays: tuple[str, ...] = DEFAULT_RELAYS

    #: where the persistent Chromium profile + caches live.
    state_dir: str = "/var/lib/nadanada-service"
    browser_headless: bool = True
    #: "chromium" (Playwright's build) or "chrome" (system Google Chrome).
    browser_channel: str = "chromium"
    page_timeout_ms: int = 45_000
    #: max messages returned by one read (the dashboard shows a finite list).
    max_messages: int = 50
    #: DB path for the escrow ledger.
    escrow_db: str = ":memory:"

    @classmethod
    def from_env(cls, env: dict | None = None, **overrides) -> "Config":
        e = os.environ if env is None else env
        cfg = cls(
            service=e.get("NADANADA_SERVICE", "nadanada"),
            version=e.get("NADANADA_VERSION", "0.1.0"),
            commit=e.get("NADANADA_COMMIT") or _git_sha(),
            dashboard_url=(e.get("NADANADA_DASHBOARD_URL") or "").strip(),
            contract_url=e.get("NADANADA_CVM_CONTRACT_URL",
                               "https://nadanada.orangesync.tech/cvm/llms.txt"),
            mint_url=e.get("NADANADA_MINT_URL", "https://testnut.cashu.space"),
            price_sats=_int_env(e.get("NADANADA_PRICE_SATS"), 1000),
            relays=tuple(
                r.strip() for r in
                (e.get("NADANADA_RELAYS") or ",".join(DEFAULT_RELAYS)).split(",")
                if r.strip()),
            state_dir=e.get("NADANADA_STATE_DIR", "/var/lib/nadanada-service"),
            browser_headless=_bool_env(e.get("NADANADA_BROWSER_HEADLESS"), True),
            browser_channel=e.get("NADANADA_BROWSER_CHANNEL", "chromium"),
            page_timeout_ms=_int_env(e.get("NADANADA_PAGE_TIMEOUT_MS"), 45_000),
            max_messages=_int_env(e.get("NADANADA_MAX_MESSAGES"), 50),
            escrow_db=e.get("NADANADA_DB_PATH", ":memory:"),
        )
        if overrides:
            cfg = replace(cfg, **{k: v for k, v in overrides.items()
                                  if v is not None})
        return cfg

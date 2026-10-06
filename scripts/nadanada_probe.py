"""Live evidence: read the dashboard through the service reader and record it.

Usage: NADANADA_DASHBOARD_URL=... python3 scripts/nadanada_probe.py
Writes evidence/nadanada-live-<ts>.json (may contain message content).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.config import Config                                        # noqa: E402
from app.nadanada_dashboard import DashboardReader                   # noqa: E402


def main() -> int:
    cfg = Config.from_env()
    if not cfg.dashboard_url:
        print("NADANADA_DASHBOARD_URL is not set", file=sys.stderr)
        return 2
    snap = DashboardReader(cfg).read()
    out = REPO / "evidence"
    out.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = out / f"nadanada-live-{stamp}.json"
    path.write_text(json.dumps(snap.as_dict(), indent=2))
    print(json.dumps(snap.as_dict(), indent=2))
    print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

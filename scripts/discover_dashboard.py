"""Step 0 discovery: learn the dashboard's shape with a real browser.

Loads the private dashboard, captures every JSON XHR/fetch response, the rendered
text/HTML, and a screenshot, then runs the pure parser over it. The output tells
us (a) whether a stable internal JSON endpoint exists (so the reader can call it
directly), and (b) what selectors/shape to rely on if not.

Writes to evidence/discovery/ (git-visibility decision left to the operator;
this output can contain message content, so treat it as sensitive).

Usage: NADANADA_DASHBOARD_URL=... python3 scripts/discover_dashboard.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.config import Config                                        # noqa: E402
from app.nadanada_dashboard import (parse_snapshot, wait_for_challenge_clear,
                                    launch_options, _WEBDRIVER_JS)                    # noqa: E402


def main() -> int:
    cfg = Config.from_env()
    if not cfg.dashboard_url:
        print("NADANADA_DASHBOARD_URL is not set", file=sys.stderr)
        return 2
    out = REPO / "evidence" / "discovery"
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    from playwright.sync_api import sync_playwright
    profile = f"{cfg.state_dir.rstrip('/')}/chromium-profile"
    pathlib.Path(profile).mkdir(parents=True, exist_ok=True)

    captured: list[dict] = []
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(profile, **launch_options(cfg))
        ctx.add_init_script(_WEBDRIVER_JS)
        page = ctx.new_page()

        def on_response(r):
            try:
                ctype = (r.headers or {}).get("content-type", "")
                if "json" not in ctype.lower():
                    return
                if r.request.resource_type not in ("xhr", "fetch"):
                    return
                captured.append({"url": r.url, "body": r.text()})
            except Exception:                                        # noqa: BLE001
                return

        page.on("response", on_response)
        page.goto(cfg.dashboard_url, wait_until="domcontentloaded",
                  timeout=cfg.page_timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=cfg.page_timeout_ms)
        except Exception:                                            # noqa: BLE001
            pass
        print("challenge cleared:", wait_for_challenge_clear(page, cfg.page_timeout_ms))
        html = page.content()
        try:
            text = page.inner_text("body")
        except Exception:                                            # noqa: BLE001
            text = ""
        shot = out / f"dashboard-{stamp}.png"
        page.screenshot(path=str(shot), full_page=True)
        ctx.close()

    (out / f"responses-{stamp}.json").write_text(
        json.dumps([{"url": c["url"]} for c in captured], indent=2))
    (out / f"raw-{stamp}.json").write_text(
        json.dumps({"json": captured, "text": text, "html": html}, indent=2))
    snap = parse_snapshot({"json": captured, "text": text, "html": html})
    (out / f"snapshot-{stamp}.json").write_text(json.dumps(snap.as_dict(), indent=2))

    print(f"captured {len(captured)} JSON responses")
    for c in captured:
        print("  -", c["url"])
    print(json.dumps(snap.as_dict(), indent=2)[:4000])
    print("screenshot:", shot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

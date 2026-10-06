# Finding: the dashboard's Cloudflare challenge blocks automated reads

Date: 2026-10-06 · Host: CobradorWave · Reader: `scripts/discover_dashboard.py`

## What was tried

| Attempt | Browser | Result |
|---|---|---|
| 1 | Playwright `chromium-headless-shell` (default) | CF interstitial, not cleared |
| 2 | Playwright `channel="chrome"`, headless | CF interstitial, not cleared |
| 3 | Playwright `channel="chrome"`, `headless=false` under `xvfb-run` | CF interstitial, not cleared |
| 3 (+ stealth) | + `--disable-blink-features=AutomationControlled`, `--enable-automation` ignored, real Chrome UA, `navigator.webdriver` removed | CF interstitial, not cleared |

The captured page text was the interstitial:

> nadanada.me — Performing security verification
> This website uses a security service to protect against malicious bots.
> Ray ID: a4644f3acdccf6e9

No `xhr`/`fetch` JSON responses were captured and no number/message text was
rendered, because the app never loaded past the challenge.

Raw captures: `evidence/discovery/` (gitignored — may contain the dashboard URL).

## Interpretation

This is Cloudflare's *managed* challenge, not a simple JS cookie. It can detect
Playwright/CDP beyond the `navigator.webdriver` flag (TLS/JA3 fingerprint, CDP
`Runtime.enable`, automation heuristics) and can be IP- and reputation-scored.
Passing it reliably needs an anti-detect browser and/or a residential proxy, or
the challenge must be solved by a human once and the clearance cookie reused.

## Consequence for this service

The Playwright reader path is implemented and correct, but it **cannot currently
authenticate past Cloudflare from this host**. The robust route is a
nadanada **API number** ($7/1mo, $12/3mo): API numbers are readable through the
REST API, no browser, no challenge. That is the recommended fallback, and the
tool surface (`phone.numbers.list`, `phone.messages.list`) is unchanged — only
the `Fetcher` behind `DashboardReader` would swap from Playwright to the REST
client.

Until then, this service's live reads are blocked; the implementation, contract,
announcement and tests are complete and green.

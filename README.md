# nadanada-service

Inbound SMS as a [ContextVM](https://www.contextvm.org/) service. Reads the
operator's rented nadanada number(s) over MCP-on-Nostr, pay-per-read in Cashu
(CEP-8), owner-free for the operator, message bodies returned only as a NIP-44 v2
payload addressed to the caller.

- Class: `cvm:service:phone-inbox`
- Tools: `phone.numbers.list` (free) · `phone.messages.list` (paid)
- Contract: `docs/cvm/llms.txt` (served at **https://nadanada.orangesync.tech/cvm/llms.txt**)

See `PLAN.md` for the design and `CHECKLIST.md` for status.

## Why a browser

nadanada separates *website* numbers from *API* numbers: a website number is not
readable via the REST API, and its private dashboard is behind a Cloudflare
challenge. So the reader drives a persistent Chromium (Playwright) against the
dashboard and labels every result `source: "dashboard-scrape"`. The $7/1mo API
number remains the robust fallback.

## Quickstart

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# reader (needs a browser):
python -m playwright install chromium

export NADANADA_DASHBOARD_URL='https://nadanada.me/phone-numbers/user/<token>'
export CVM_OWNER_PUBKEYS='<operator hex pubkey>'
export NADANADA_MINT_URL='https://testnut.cashu.space'

python scripts/run_cvm_server.py --announce    # publish the CEP-6 catalog
python scripts/run_cvm_server.py               # announce + serve
```

## Test

```bash
pytest                 # offline: no browser, no network, no live mint
deno task test         # announcement conformance + fixture parity
deno task announce:check
```

## Layout

```
app/                 service core (pure, testable)
  cvm.py             protocol constants + kit-fixture announcement loader
  cvm_rpc.py         MCP JSON-RPC dispatch
  nip44.py           NIP-44 v2 (vectors-proved)
  cashu.py           Cashu decode/verify/swap + MintClient
  nadanada_dashboard.py  Playwright reader + pure parser
  nadanada_tools.py  MCP tools + CEP-8 gating
  main.py / server.py
scripts/             run_cvm_server.py, discover_dashboard.py, nadanada_probe.py
tools/               nadanada_announcement.ts (kit emitter) + test
vendor/cvm-service-kit  vendored tag-contract library
docs/cvm/            llms.txt, llms-full.txt
deploy/              systemd unit, Caddyfile, README
```

## Scope

Read-only inbound SMS. No send, no purchase/renew, and no provisioning of
accounts anywhere (including OpenAI). See `PLAN.md` §10.

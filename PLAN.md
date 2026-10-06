# PLAN — nadanada-service: pooled rental-number inbox as a ContextVM service

Status: **implementation in progress** (`cvm-services/nadanada-service`, private).
Owner/operator: c03rad0r · Started: 2026-10-06.

## 1. Goal

Wrap the operator's nadanada rented number(s) as a ContextVM (CVM) service that
**reads inbound SMS** — a machine-readable inbox addressed by a Nostr npub,
payable with Cashu (CEP-8), with the phone account secret held server-side.

Explicitly in scope: reading messages on a number the operator rents.
Explicitly out of scope: provisioning OpenAI (or any third-party) accounts, and
any automated account signup / verification flow. This service is a generic
inbound-SMS reader; it does not create accounts anywhere.

## 2. Why not the nadanada REST API

- nadanada's OpenAPI (`https://nadanada.me/api/v2/openapi.json`, verified
  2026-10-06) separates **frontend numbers** from **API numbers**: a number
  bought on the website is *not* readable through the API, and `userSecret` is
  only issued once at an API purchase.
- The operator's number `+447366934621` was bought on the website. Its dashboard
  is `https://nadanada.me/phone-numbers/user/<redacted-token>`.
- That dashboard sits behind a **Cloudflare non-interactive challenge**
  (`Just a moment...`; a plain HTTP GET returns a 5.6 KB challenge page), so the
  reader must drive a real browser.

Decision: **Playwright** (persistent Chromium context) against the private
dashboard URL. The API-number route ($7/1mo, $12/3mo) remains the robust
fallback if the dashboard path proves too brittle.

## 3. Identity

| Role | npub | Key |
|---|---|---|
| Owner / ACL (free caller) | `npub1tv65zfac5jhcu8v3dhy63eze4jw0slc7ekfj3lnf56agnem5p7zqmqp60e` | `~/.hermes/keys/hermes-ops/cobrador.nsec` (hex `5b354127…40f84`) |
| Provider / announce (for now) | generated `.cvm-server.nsec` on first run | repo-local, 0600 |

The vanity npub `npub1c03rad0r…` is the desired long-term provider identity but
is only reachable through an nsec bunker; switching to it is deferred.

## 4. Architecture

```
app/
  config.py             env-driven runtime config (no secrets in code)
  cvm.py                protocol constants, CEP-6 service identity, contract tags
  cvm_rpc.py            MCP JSON-RPC dispatch (reused from nosms, verbatim)
  nip44.py              NIP-44 v2 (reused, vectors-proved)
  errors.py             X-Reason / X-Hint error contract (reused)
  cashu.py              Cashu token decode/verify/swap, MintClient (reused)
  nadanada_dashboard.py Playwright reader + injectable fetcher (unit-testable)
  nadanada_tools.py     CvmTools: phone.numbers.list (free), phone.messages.list (PAID)
  main.py               FastAPI app: /api/health, /llms.txt, local debug surface
scripts/
  discover_dashboard.py one-off Playwright trace -> selectors / internal JSON endpoint
  run_cvm_server.py      announce + serve kind-25910 over relays (adapted from nosms)
  nadanada_probe.py      live evidence: list numbers, dump messages, screenshot
tools/
  nadanada_announcement.ts  Deno emitter via vendored cvm-service-kit (single source of tags)
docs/cvm/
  llms.txt, llms-full.txt   the machine contract, served by the `docs` tool
deploy/
  nadanada.service, Caddyfile.nadanada, README.md
```

## 5. Tools

- `phone.numbers.list` — **free**, read-only. Returns the numbers on the
  dashboard with expiry.
- `phone.messages.list` — **PAID** (CEP-8 `bitcoin-cashu` `explicit_gating`).
  Owner npub is free (via `CVM_OWNER_PUBKEYS`). Returns a **NIP-44 v2 payload
  encrypted to the caller's npub** — message bodies are OTPs, so they never
  travel as plaintext in an announcement-addressable context.

No `purchase` / `renew` tools (scope: paid inbox only). Renewal stays manual.

## 6. Reader design (Playwright)

- Persistent context (`--user-data-dir` under the service state dir, mode 0700)
  so the Cloudflare clearance cookie survives between calls.
- The reader is a class around an **injectable fetcher** so tests run offline
  against recorded fixtures; the Playwright fetcher is one implementation.
- On load it (a) records JSON responses and (b) extracts the rendered messages,
  so an internal JSON endpoint (if stable) can replace DOM scraping later.
- Every result is labelled honestly: `source: "dashboard-scrape"`, `as_of`,
  `freshness`. It never claims a rail API.
- Browser runs in a subprocess behind a lock (single-operator pool, v1).

## 7. Announcement (CEP-6 / CEP-8)

`tools/nadanada_announcement.ts` emits the tag set through the vendored
`cvm-service-kit` (single source of truth, parity-tested against a golden
fixture):

- kind `11316`; `d = nadanada`; `t = cvm:service:phone-inbox`
- `cvm:req:payment.amount` (the flow takes money) → `cvm:tier:financial`
- `pmi bitcoin-cashu explicit_gating`; `cap tool:phone.messages.list <n> sats`
- `r` → the contract URL; payload `name/about/website`
- relays: `wss://relay.contextvm.org wss://relay2.contextvm.org wss://relay.primal.net`

Registry: the generated provider npub is allow-listed in
`cvm-registry/curators.json`.

## 8. Deployment (vps2 `23.182.128.51`)

`/opt/nadanada-service` + `.venv` (needs Playwright + Chromium), config at
`/etc/nadanada.env`, systemd unit, Caddy vhost `nadanada.orangesync.tech` →
`127.0.0.1:8089`. Secrets (dashboard token, CVM nsec) via **OpenBao** /
`fleet_secret.py`.

## 9. Risks (accepted, flagged)

- Cloudflare may re-challenge headless Chromium; persistent profile + real
  Chrome channel + `xvfb` are the mitigations.
- The dashboard DOM/JSON is undocumented and may change; the reader fails
  loudly with a captured screenshot rather than returning fabricated data.
- Scraping a bot-protected dashboard is a ToS-gray, brittle path (noted, chosen
  over buying an API number for now).
- The dashboard currently shows **0 messages**; the empty state is provable now,
  the populated state is proven when a message arrives.

## 10. Out of scope (explicit)

Account provisioning/teardown for any third party, including OpenAI; automated
signup or payment flows. The nadanada reader is generic and standalone.

## 11. Companion work (separate)

The existing-account OpenAI Codex lane: `hermes auth add openai-codex --type
oauth` (official device flow) → `hermes auth list/status` → run the
`codex/models` + `wham/usage` probes from
`hermes-orchestration/docs/designs/openai-codex-subscription-lane.md`.

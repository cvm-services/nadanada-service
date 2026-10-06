# RUNBOOK — nadanada-service

Operator steps to take this from a green repo to a served, discoverable CVM.
Each step states its exit criterion. Nothing here is "done" without the stated
evidence.

## 0. Pick the read path (decision)

- **A. API number (recommended, working path).** Buy an API number
  (`POST /api/v2/phone/purchase` + `/complete`, $7/1mo or $12/3mo) — this returns
  a `userId` + `userSecret` **once**. Website numbers are NOT API-visible.
- **B. Browser scrape (blocked).** Only if Cloudflare can be passed (anti-detect
  browser + residential proxy, or a human-solved clearance cookie). See
  `evidence/CF-FINDING.md`.

Exit: a `userId` + `userSecret` (A), or a browser that loads the dashboard (B).

## 1. Configure (vps2, OpenBao-rendered `/etc/nadanada.env`, 0600)

Path A:
```
NADANADA_READER=api
NADANADA_API_BASE=https://nadanada.me
NADANADA_API_USER_ID=<uuid>
NADANADA_API_USER_SECRET=<uuid>
```
Path B:
```
NADANADA_READER=playwright
NADANADA_DASHBOARD_URL=https://nadanada.me/phone-numbers/user/<token>
```
Common:
```
CVM_OWNER_PUBKEYS=<operator hex pubkey>
NADANADA_MINT_URL=https://testnut.cashu.space
NADANADA_PRICE_SATS=1000
NADANADA_STATE_DIR=/var/lib/nadanada-service
NADANADA_RELAYS=wss://relay.contextvm.org,wss://relay2.contextvm.org,wss://relay.primal.net
```

Exit: `python -c` with the env set can construct `Config.from_env()` with the
expected values.

## 2. Prove the read locally (before deploy)

```
export NADANADA_READER=api NADANADA_API_USER_ID=... NADANADA_API_USER_SECRET=...
python scripts/nadanada_probe.py        # prints numbers + messages as JSON
```
Exit: the real number(s) appear; a message (or the honest 0-message state) is
recorded under `evidence/`.

## 3. Deploy on vps2

Follow `deploy/README.md`: user `nadanada`, `/opt/nadanada-service`, venv,
`playwright install chromium` (Path B only), `/etc/nadanada.env`, both units,
Caddy vhost.

```
sudo systemctl enable --now nadanada-http.service nadanada-cvm.service
curl -sS https://nadanada.orangesync.tech/api/health
curl -sS https://nadanada.orangesync.tech/cvm/llms.txt | head
```
Exit: health returns `ok:true`; the contract is fetchable; `journalctl -u
nadanada-cvm` shows the server npub and the published announcement kinds.

## 4. Allow-list the provider npub (dashboard visibility)

The server npub is printed on first run and stored in the `CVM_NSEC`. Add it to
`cvm-registry/curators.json` (`curators[]`, role `curator`/`provider`) and
redeploy the registry, so the announcement renders on `cvm.orangesync.tech`.

Exit: `nak req -k 11316 -t cvm:service:phone-inbox <relay>` returns the event,
and the dashboard renders it.

## 5. Verify the paid tool from a second key

From a distinct Nostr key (not the owner):
```
# free
cvmi call <npub> phone.numbers.list
# unpaid -> payment_required with the cap
cvmi call <npub> phone.messages.list
# paid -> attach a testnut Cashu token covering the cap
```
Exit: owner reads free; a stranger is refused with `payment_required`; a paid
call returns a NIP-44 payload the caller decrypts to the messages JSON.

## 6. Companion: OpenAI Codex lane (existing account only)

```
hermes auth add openai-codex --type oauth   # approve the device code in a browser
hermes auth list | grep openai-codex
hermes auth status openai-codex
```
Then run the `codex/models` + `wham/usage` probes from
`hermes-orchestration/docs/designs/openai-codex-subscription-lane.md`.

Exit: `openai-codex (1 credentials) oauth` and a 200 on `/wham/usage`.

## 7. Out of scope

Account provisioning/teardown for any third party. This repo is a read-only
inbound-SMS service.

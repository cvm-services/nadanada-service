# CHECKLIST — nadanada-service

Maintained in-repo; updated as work lands. `[ ]` todo · `[~]` in progress ·
`[x]` done · `[!]` blocked.

Repo: https://github.com/cvm-services/nadanada-service (private)

## 0. Scaffolding
- [x] Create repo skeleton at `~/repos/nadanada-service`
- [x] Reuse pure modules from nosms (`cvm_rpc.py`, `nip44.py`, `errors.py`, `cashu.py`)
- [x] `PLAN.md`, `CHECKLIST.md`, `README.md`, `requirements.txt`, `pytest.ini`, `.coveragerc`
- [x] Vendored `cvm-service-kit`

## 1. Core
- [x] `app/config.py` — env-driven config
- [x] `app/cvm.py` — protocol constants + kit-fixture announcement loader
- [x] `app/nadanada_dashboard.py` — Playwright + REST reader backends, pure parser, CF-aware wait
- [x] `app/nadanada_tools.py` — `phone.numbers.list` (free), `phone.messages.list` (paid)
- [x] `app/main.py` + `server.py` — health + contract surface
- [x] `scripts/discover_dashboard.py`, `scripts/nadanada_probe.py`
- [x] `scripts/run_cvm_server.py` — announce + serve kind-25910

## 2. Announcement
- [x] `tools/nadanada_announcement.ts` via vendored kit
- [x] `fixtures/nadanada-11316.tags.json` golden fixture
- [x] `tools/nadanada_announcement_test.ts` (4 tests) + `deno task announce:check`

## 3. Contract + docs
- [x] `docs/cvm/llms.txt`, `docs/cvm/llms-full.txt`, `README.md`

## 4. Tests
- [x] 22 `pytest` tests green; coverage 79% (gate 70%)
- [x] 4 Deno announcement tests green
- [x] CVM JSON-RPC surface test (initialize/tools/resources/notification)

## 5. Registry + publish
- [x] Create `cvm-services/nadanada-service` on GitHub (private) + push
- [ ] Allow-list provider npub in `cvm-registry/curators.json` (needs the npub
      generated on first `run_cvm_server.py` run)

## 6. Live evidence
- [x] Ran `scripts/discover_dashboard.py` (3 variants, incl. headed+stealth)
- [!] **BLOCKED by Cloudflare**: the managed challenge does not clear for an
      automated browser from this host. See `evidence/CF-FINDING.md`.
- [x] REST backend implemented (`ApiFetcher`, `NADANADA_READER=api`) + offline tests
- [ ] Buy an API number and set `NADANADA_API_USER_ID`/`SECRET` for a live read

## 7. Deploy (vps2)
- [x] `deploy/nadanada-http.service`, `nadanada-cvm.service`, `Caddyfile.nadanada`, `deploy/README.md`
- [ ] Apply on vps2 (venv, `playwright install chromium`, OpenBao `/etc/nadanada.env`, units, Caddy)

## 8. Companion (separate, existing account only)
- [~] `hermes auth add openai-codex --type oauth` started (device code issued); awaiting operator approval
- [ ] `hermes auth list/status` clean
- [ ] Run `codex/models` + `wham/usage` probes per the lane spec

## Blockers / decisions
- [!] Cloudflare blocks the Playwright dashboard read from this host. Decide:
      anti-detect browser + residential proxy, a human-solved clearance cookie,
      or switch to an API number (recommended).
- [ ] Switch provider identity to vanity npub via nsec bunker (deferred).

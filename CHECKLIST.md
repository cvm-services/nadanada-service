# CHECKLIST — nadanada-service

Maintained in-repo; updated as work lands. `[ ]` todo · `[~]` in progress ·
`[x]` done · `[!]` blocked.

Repo: https://github.com/cvm-services/nadanada-service (private)

## 0. Scaffolding
- [x] Create repo skeleton at `~/repos/nadanada-service`
- [x] Reuse pure modules from nosms (`cvm_rpc.py`, `nip44.py`, `errors.py`, `cashu.py`)
- [x] Write `PLAN.md`
- [x] Write `CHECKLIST.md`
- [x] `requirements.txt`, `pytest.ini`, `.coveragerc`, `.gitignore`, `README.md`

## 1. Core
- [x] `app/config.py` — env-driven config
- [x] `app/cvm.py` — protocol constants + kit-fixture announcement loader
- [x] `app/nadanada_dashboard.py` — Playwright reader + pure parser
- [x] `app/nadanada_tools.py` — `phone.numbers.list` (free), `phone.messages.list` (paid)
- [x] `app/main.py` + `server.py` — health + contract surface
- [x] `scripts/discover_dashboard.py` — trace selectors / internal endpoint
- [x] `scripts/run_cvm_server.py` — announce + serve kind-25910
- [x] `scripts/nadanada_probe.py` — live evidence run

## 2. Announcement
- [x] `tools/nadanada_announcement.ts` via vendored cvm-service-kit
- [x] `fixtures/nadanada-11316.tags.json` golden fixture
- [x] `tools/nadanada_announcement_test.ts` (4 tests) + `deno task announce:check`

## 3. Contract + docs
- [x] `docs/cvm/llms.txt`
- [x] `docs/cvm/llms-full.txt`
- [x] `README.md`

## 4. Tests
- [x] 22 `pytest` tests green; coverage 79% (gate 70%)
- [x] reader parser tests incl. empty state + multi-number
- [x] tools tests: owner-free, payment-required, capture, NIP-44 round-trip
- [x] 4 Deno announcement tests green

## 5. Registry + publish
- [x] Create `cvm-services/nadanada-service` on GitHub (private) + push
- [ ] Allow-list provider npub in `cvm-registry/curators.json` (needs the npub
      generated on first `run_cvm_server.py` run)
- [~] `phone-inbox` class: no vocab edit required (class is a free kebab token in
      the kit); revisit if `contextvm-services` keeps a class register

## 6. Live evidence
- [ ] Run `scripts/discover_dashboard.py` against the operator dashboard
      (requires `NADANADA_DASHBOARD_URL` + Playwright chromium on the host)
- [ ] Record numbers list + message read (0-message state now) to `evidence/`

## 7. Deploy (vps2)
- [x] `deploy/nadanada-http.service`, `deploy/nadanada-cvm.service`, `Caddyfile.nadanada`, `deploy/README.md`
- [ ] Apply on vps2: venv, `playwright install chromium`, OpenBao-rendered
      `/etc/nadanada.env`, units enabled, Caddy reloaded
- [ ] Announce live; `nadanada.orangesync.tech` up

## 8. Companion (separate, existing account only)
- [ ] `hermes auth add openai-codex --type oauth` → approve device code
- [ ] `hermes auth list/status` clean
- [ ] Run `codex/models` + `wham/usage` probes per the lane spec

## Open decisions / follow-ups
- [ ] Switch provider identity to vanity npub via nsec bunker (deferred)
- [ ] Optional: replace DOM scraping with a stable internal JSON endpoint if
      `discover_dashboard.py` finds one

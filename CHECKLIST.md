# CHECKLIST — nadanada-service

Maintained in-repo; updated as work lands. `[ ]` todo · `[~]` in progress ·
`[x]` done · `[!]` blocked.

## 0. Scaffolding
- [x] Create repo skeleton at `~/repos/nadanada-service`
- [x] Reuse pure modules from nosms (`cvm_rpc.py`, `nip44.py`, `errors.py`, `cashu.py`)
- [x] Write `PLAN.md`
- [x] Write `CHECKLIST.md`
- [ ] `requirements.txt`, `pytest.ini`, `.gitignore`, `README.md`

## 1. Core
- [ ] `app/config.py` — env-driven config
- [ ] `app/cvm.py` — protocol constants + CEP-6 identity for `phone-inbox`
- [ ] `app/nadanada_dashboard.py` — Playwright reader + injectable fetcher
- [ ] `app/nadanada_tools.py` — `phone.numbers.list` (free), `phone.messages.list` (paid)
- [ ] `app/main.py` + `server.py` — health + contract surface
- [ ] `scripts/discover_dashboard.py` — trace selectors / internal endpoint
- [ ] `scripts/run_cvm_server.py` — announce + serve kind-25910
- [ ] `scripts/nadanada_probe.py` — live evidence run

## 2. Announcement
- [ ] `tools/nadanada_announcement.ts` via vendored cvm-service-kit
- [ ] `fixtures/nadanada-11316.tags.json` golden fixture
- [ ] parity test (`tools/nadanada_announcement_test.ts` / deno task)

## 3. Contract + docs
- [ ] `docs/cvm/llms.txt`
- [ ] `docs/cvm/llms-full.txt`
- [ ] `README.md`

## 4. Tests
- [ ] reader unit tests against recorded fixtures (incl. empty state)
- [ ] tools tests (owner-free, payment-required, NIP-44 to caller)
- [ ] `pytest` green, coverage gate

## 5. Registry + publish
- [ ] Create `cvm-services/nadanada-service` on GitHub (private)
- [ ] Push initial implementation
- [ ] Allow-list provider npub in `cvm-registry/curators.json`
- [ ] Add `phone-inbox` class to `contextvm-services/vocab` if required

## 6. Live evidence
- [ ] Run `discover_dashboard.py` against the operator dashboard
- [ ] Record numbers list + message read (0-message state now) to `evidence/`

## 7. Deploy (vps2)
- [ ] `deploy/nadanada.service`, `Caddyfile.nadanada`, `README.md`
- [ ] Playwright + Chromium provisioned on vps2
- [ ] OpenBao secrets wired; announce live; `nadanada.orangesync.tech` up

## 8. Companion (separate, existing account only)
- [ ] `hermes auth add openai-codex --type oauth` → approve device code
- [ ] `hermes auth list/status` clean
- [ ] Run `codex/models` + `wham/usage` probes per the lane spec

## Open decisions / follow-ups
- [ ] Switch provider identity to vanity npub via nsec bunker (deferred)
- [ ] Decide whether to keep both free `numbers.list` and paid `messages.list` (yes, per operator)
- [ ] Optional: replace DOM scraping with a stable internal JSON endpoint if discovery finds one

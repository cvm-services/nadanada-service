# Deploy nadanada-service on vps2 (23.182.128.51)

Two systemd units (model: `~/nosms/deploy/`), one Caddy vhost, secrets via
OpenBao rendered into `/etc/nadanada.env`.

## 1. Code + venv

```bash
sudo useradd --system --home /opt/nadanada-service --shell /usr/sbin/nologin nadanada
sudo mkdir -p /opt/nadanada-service /var/lib/nadanada-service
sudo chown -R nadanada:nadanada /opt/nadanada-service /var/lib/nadanada-service
sudo -u nadanada git clone <repo> /opt/nadanada-service
cd /opt/nadanada-service
sudo -u nadanada python3 -m venv .venv
sudo -u nadanada .venv/bin/pip install -r requirements.txt
# browser for the dashboard reader
sudo -u nadanada .venv/bin/python -m playwright install --with-deps chromium
```

## 2. Secrets

Render `/etc/nadanada.env` (mode 0600, owner nadanada) from OpenBao via
`fleet_secret.py`; never commit it. Keys:

```
NADANADA_DASHBOARD_URL=https://nadanada.me/phone-numbers/user/<token>
CVM_OWNER_PUBKEYS=<operator hex pubkey>
NADANADA_MINT_URL=https://testnut.cashu.space
NADANADA_PRICE_SATS=1000
NADANADA_STATE_DIR=/var/lib/nadanada-service
```

## 3. Units + Caddy

```bash
sudo cp deploy/nadanada-http.service deploy/nadanada-cvm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nadanada-http.service nadanada-cvm.service
# append deploy/Caddyfile.nadanada to the existing Caddyfile, then:
sudo systemctl reload caddy
curl -sS https://nadanada.orangesync.tech/api/health
curl -sS https://nadanada.orangesync.tech/cvm/llms.txt | head
```

## 4. Evidence the units work

- `nadanada-cvm.service` logs the server npub + the published announcements.
- `journalctl -u nadanada-cvm -f` shows `tools/call` lines with caller short-hex.

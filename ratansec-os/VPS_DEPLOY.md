# 🖥️ RatanSec OS — VM / Cloud par chalao (24x7, ek command)

**Koi bhi VM chalega** — Oracle Cloud (free), Google Cloud (free), Vultr, Hetzner, DigitalOcean, Contabo, AWS, Azure, ya apne computer par VirtualBox/VMware/Proxmox VM. Sab par **wahi ek script** chalti hai, kyunki VM bas ek Ubuntu/Debian machine honi chahiye.

> Kaam ka rule: **VM = Ubuntu 22.04/24.04 ya Debian 12 ya Kali** hona chahiye, aur tumhare paas **root/sudo** ho.

---

## ⚡ 3 commands (poora setup) — VM ke SSH me ye chalao

```bash
# 1) code laao
sudo apt update && sudo apt install -y git
git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io

# 2) installer chalao (apni key + apna domain daalo)
sudo bash ratansec-os/deploy/vps-install.sh \
     --key sk-or-v1-TUMHARI-KEY \
     --scope "tera-domain.com" \
     --port 8000
```

**3) Bas!** Script khud ye sab karti hai:
- ✅ security tools install (nmap, nikto, whatweb, sqlmap, gobuster, ffuf, nuclei, hydra, whois, dig…)
- ✅ Python env + dependencies
- ✅ `.env` (random strong password generate karke)
- ✅ **systemd service** → VM restart/crash hone par bhi khud chalu (24x7)
- ✅ firewall (ufw) me port kholna (agar ufw active hai)
- ✅ health check + ant me URL + password print

Ant me aisa dikhega:

```
╔══════════════════════════════════════════════════════════════╗
║   ✅ RatanSec OS INSTALL HO GAYA                             ║
╚══════════════════════════════════════════════════════════════╝
   Dashboard:  http://203.0.113.45:8000
   Password:   wVmvZVsmxATf
   AI:         ON (openai/gpt-4o-mini)
   Scope:      tera-domain.com
```

Browser me wo URL kholo → password → **dashboard chalu** 🎉

---

## 🔓 Zaroori: cloud console me port kholna (ye 90% log bhool jaate hain)

VM ke andar firewall theek ho, par **cloud provider ka apna firewall** bhi port allow karna padta hai. Provider ke hisaab se:

| Provider | Kahan port 8000 kholna hai |
|---|---|
| **Oracle Cloud** | Networking → VCN → **Security Lists** → Default → **Add Ingress Rule**: Source `0.0.0.0/0`, IP Protocol `TCP`, Destination Port Range `8000` |
| **Google Cloud** | VPC network → **Firewall** → Create rule → Direction `Ingress`, Targets `All instances`, Source `0.0.0.0/0`, Protocols/ports: `tcp:8000` |
| **AWS EC2** | EC2 → **Security Groups** → instance ka SG → **Edit inbound rules** → Add rule: Type `Custom TCP`, Port `8000`, Source `0.0.0.0/0` |
| **Azure** | VM → **Networking** → **Add inbound port rule** → Destination port `8000`, Protocol `TCP`, Source `Any` |
| **Vultr / DigitalOcean / Hetzner / Contabo** | **Firewall / Cloud Firewall** (agar banaya hai) → inbound TCP 8000 allow. Vultr/DO me by default sab khula hota hai (firewall banaya na ho to) |
| **VirtualBox / VMware (local VM)** | VM Settings → **Network** → Adapter Attached to **Bridged** (best), ya NAT me **Port Forwarding**: Host 8000 → Guest 8000 |
| **Proxmox / KVM** | VM ko bridged network do; host firewall me 8000 allow |

Check karne ka aasan tarika: laptop ke browser me `http://<VM-PUBLIC-IP>:8000` kholo. Na khule to port band hai (upar wala rule add karo).

---

## 💰 Free VM kaun deta hai (2026 me realistic)

| Provider | Free me kya | Dhyan |
|---|---|---|
| **Oracle Cloud — Always Free** ⭐ | **4 ARM CPUs + 24 GB RAM** (Ampere A1) ya 2× AMD micro — **hamesha free** | Signup par card verification chahiye (charge nahi hota). Best free option — isme full tools + AI aaram se chalte hain |
| **Google Cloud Free Tier** | `e2-micro` (1 GB RAM) 1 free per month (US regions) | 1 GB RAM kam hai → `--lite` flag use karo |
| **AWS Free Tier** | `t2.micro`/`t4g.small` 12 mahine free | 12 mahine ke baad paisa |
| **Azure Free** | B1s 12 mahine + ₹15k credits | 12 mahine baad paisa |
| **Hetzner (paid, sasta)** | CX22 — ~€3.79/mo (~₹360) | Free nahi, par sabse sasta + best network |
| **Vultr / DigitalOcean (paid)** | $5–6/mo (~₹500) | Duniya bhar me region, sadha setup |

> **Mera suggestion:** **Oracle Cloud Always Free (ARM)** lo — free hai, 24 GB RAM hai, aur ye app + saare tools + AI usme aaram se chalenge.
> 1 GB RAM wali free VM (GCP) par: `sudo bash ratansec-os/deploy/vps-install.sh --lite --key ...`

---

## 🔁 Rozana ke commands (install ke baad)

Script ek `ratansec` helper bhi install karti hai:

```bash
ratansec status       # chal raha hai ya nahi + health JSON
ratansec logs -f      # live logs (Ctrl+C se bahar)
ratansec restart      # restart
ratansec stop         # band
ratansec start        # chalu
ratansec password     # dashboard password dikhao
ratansec url          # public URL
ratansec update       # naya code (git pull) + restart
```

Manual systemd (agar helper pasand na aaye):
```bash
sudo systemctl status ratansecos      # status
sudo systemctl restart ratansecos     # restart
sudo journalctl -u ratansecos -f      # logs
sudo nano /opt/ratansec-os/.env       # config badalna → phir: ratansec restart
```

**VM reboot karo to kya hoga?** Service `enable` hai — **khud chalu ho jayegi**, tumhe kuch nahi karna.

---

## 🔐 HTTPS / domain (optional, par recommended)

### Option 1 — Free HTTPS URL bina domain (Cloudflare Quick Tunnel)
```bash
bash ratansec-os/deploy/cloudflared-tunnel.sh 8000
```
Ye ek `https://xxxx.trycloudflare.com` URL de deta hai — port kholne ki bhi zarurat nahi. ⚠️ URL har restart par badalta hai.

### Option 2 — Apna domain + free SSL (Caddy)
Agar tumhara domain hai (jaise `lab.terasite.com`) aur uska DNS **A record** VM ke IP par point karta hai:
```bash
sudo apt install -y caddy
sudo tee /etc/caddy/Caddyfile >/dev/null <<'EOF'
lab.terasite.com {
    reverse_proxy 127.0.0.1:8000
}
EOF
sudo systemctl restart caddy
```
Caddy khud **free Let's Encrypt certificate** le lega → dashboard `https://lab.terasite.com` par. (Cloud firewall me port 80/443 allow karo, 8000 band kar do.)

---

## 🛠️ Troubleshooting (VM-specific)

| Problem | Kya karo |
|---|---|
| Browser me `http://IP:8000` nahi khulta | **Cloud firewall** me inbound TCP 8000 allow karo (upar table). Andar `curl localhost:8000/api/health` chalao — ye chal raha ho to 100% port/firewall ka issue hai |
| `Permission denied` script chalate waqt | `sudo bash ratansec-os/deploy/vps-install.sh …` (sudo ke saath) |
| `python3-venv` nahi mila / venv fail | `sudo apt install -y python3-venv python3-pip` phir script dobara |
| Health check timeout | `ratansec logs` (ya `sudo journalctl -u ratansecos -n 50`) → asli error wahan dikhega |
| `Address already in use` | Dusra port: `--port 8080` (aur cloud firewall me wahi port kholo) |
| 1 GB RAM VM par OOM / slow | `--lite` flag ke saath install karo, aur `.env` me `MAX_CONCURRENT_SCANS=1` |
| ARM VM (Oracle Ampere) par kuch tools missing | nmap/nikto/sqlmap/whatweb sab ARM par chalte hain. `gobuster`/`ffuf`/`nuclei` apt me na mile to dashboard → Tools tab me manual install command dikhega; un steps ke bina bhi scans chalte hain |
| `apt` tools install skip hue | `sudo bash ratansec-os/scripts/install-tools.sh` (best-effort), ya Docker image use karo |
| AI: off | `sudo nano /opt/ratansec-os/.env` → `OPENROUTER_API_KEY=…` → `ratansec restart` |
| Password bhool gaya | `ratansec password` |
| Naya code chahiye | `ratansec update` (git pull + restart) |
| YOLO debug | `tail -50 /tmp/ratansec.log` (Codespaces/local) · `sudo journalctl -u ratansecos -n 100` (VM) |

---

## 🧪 Verify (install ke baad check list)

```bash
ratansec status                                        # service active + health {"ok":true}
curl -s localhost:8000/api/tools | head -c 300          # tools list
curl -s -X POST localhost:8000/api/scan \
  -H "Authorization: Bearer $(ratansec password)" \
  -H 'Content-Type: application/json' \
  -d '{"target":"tera-domain.com","profile":"quick"}'   # scan start (scope me ho to seedha chalega)
```
Ya code base me: `python3 tests/smoke_test.py --url http://localhost:8000 --token "$(ratansec password)"`

---

## ⚙️ Flags (installer ke saare options)

```bash
sudo bash ratansec-os/deploy/vps-install.sh --help

--key KEY          OpenRouter API key (AI chat)
--password PASS    Dashboard password (na do to random)
--scope LIST       ALLOWED_TARGETS: "site.com,*.lab.in,10.0.0.0/24"
--port N           default 8000
--model M          default openai/gpt-4o-mini
--lite             1 GB RAM VMs ke liye (kam tools, 1 scan worker)
--no-service       systemd skip (Docker/Codespaces)
--skip-tools       apt se tools install mat karo
--no-apt           apt bilkul na chalao (sirf app setup)
--url-only         install karo, start mat karo
--dir PATH         install location (default /opt/ratansec-os)
```

---

## 🐳 Docker wala rasta (agar Docker already ho VM par)

```bash
cd Ratan-patel.github.io/ratansec-os
cp .env.example .env && nano .env          # APP_PASSWORD + OPENROUTER_API_KEY
docker compose up -d --build               # full Kali image (baari, par sab tools)
docker compose logs -f                     # logs
docker compose down                        # band
```
Slim image (kam RAM): `docker build -f Dockerfile.slim -t ratansec-os:slim . && docker run -d --name ratansec --env-file .env -p 8000:8000 --restart unless-stopped ratansec-os:slim`

---

## ⚠️ Security (VM public internet par hai — ye zaroor karo)

1. **Strong `.env` password** rakho (script random de deti hai — wahi rakho).
2. **`--scope` do** — bina scope ke har scan par manual approval lagega (safe, par slow).
3. **Port sirf 8000** kholna; SSH (22) ko sirf apne IP se allow karo.
4. **Public URL kisi ko share mat karo** (password kisi ko na do).
5. Sirf **authorized targets** scan karo — VM se kiya gaya scan tumhari IP/account se juda hota hai.

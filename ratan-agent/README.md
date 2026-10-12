# RATAN agent — phone ke terminal ke liye AI agent (Hugging Face powered)

`ratan` ek **terminal AI agent** hai jo aapke phone par chalta hai: Termux ke andar
**Ubuntu 26.04 LTS (Resolute Raccoon)** userspace, aur model **Hugging Face Inference
Providers** se aata hai (ek free HF token chahiye).

Yeh purane `agent-starter` (Cloudflare web agent) wale features ko replace karta hai.
Naye features terminal-first hain: shell chalana, file padhna/likhna, grep, sysinfo,
Hugging Face Hub search, streaming replies, session save/load — sab terminal mein.

---

## 1. Phone par install (3 command)

Termux kholiye (F-Droid wala Termux best hai), phir:

```bash
curl -fsSL https://ratan-patel.github.io/ratan-agent/install-termux.sh | bash
```

> Agar yeh branch abhi `main` par merge nahi hua, to branch wali URL use kijiye:
> ```bash
> curl -fsSL https://raw.githubusercontent.com/Ratan-patel/Ratan-patel.github.io/arena/45640110-ratan-patel-github-io/ratan-agent/install-termux.sh | bash
> ```

Installer yeh karta hai:

1. `pkg install python curl git proot-distro`
2. `proot-distro install ubuntu:26.04` (na mile to `ubuntu:latest` par fallback)
3. Ubuntu ke andar venv + `huggingface_hub` + `ratan` binary
4. HF token poochhta hai (skip bhi kar sakte hain)

Uske baad:

```bash
proot-distro login ubuntu
ratan login            # free token: https://huggingface.co/settings/tokens
ratan doctor           # token + network check
ratan                  # agent shuru
```

Termux se bina Ubuntu mein ghus ek-sawaal:

```bash
proot-distro login ubuntu -- ratan ask "disk kitna free hai?"
```

## 2. Hugging Face token

- https://huggingface.co/settings/tokens → **New token** → *Read* + **"Make calls to Inference Providers"** permission.
- `ratan login` se save hota hai `~/.ratan/config.json` mein (chmod 600), ya `export HF_TOKEN=hf_...`.
- Free tier rate-limited hai. `429` aaye to thoda rukiye ya model badliye.

## 3. Roz ka use

```bash
ratan                                   # interactive chat
ratan ask "termux mein python3.13 kaise install karun?"
ratan ask --yes "is folder ka size nikal aur top 5 bade files batao"
cat error.log | ratan ask "is crash ka reason kya hai?"
ratan models qwen                       # router par available models
ratan --model openai/gpt-oss-120b:fastest
ratan doctor                            # environment + token + connectivity
```

Chat ke andar:

| Command | Kaam |
|---|---|
| `/help` | poori help |
| `/model [id]` | model dekho / badlo |
| `/models [query]` | router ke models list |
| `/tools` | tools on/off |
| `/yes` | auto-approve on/off (destructive commands phir bhi poochte hain) |
| `/sysinfo` | Termux/proot, distro, kernel string, CPU, RAM |
| `/doctor` | poora health check |
| `/cwd <dir>` | kaam karne ki directory badlo |
| `/save [name]`, `/load <name>`, `/sessions` | conversation save/resume |
| `/clear` | context reset |
| `!<command>` | seedha shell command, jaise `!ls -la` |

## 4. Tools (model inhe khud call karta hai)

`shell`, `read_file`, `write_file`, `list_dir`, `search_files` (regex grep),
`sysinfo`, `hf_search_models`.

Har tool call se pehle terminal mein dikhta hai aur approval maangi jaati hai.
`rm -rf /`, `dd of=/dev/...`, `mkfs`, `chmod -R 777 /`, `curl ... | bash` jaise
destructive patterns **`--yes` ke saath bhi block** rehte hain.

## 5. Kernel ki sachchai (zaroor padhiye)

Aapne "latest kernel" maanga tha — iska honest jawab:

| Cheez | Phone (Termux + proot-distro) | VM (QEMU / qcow2) |
|---|---|---|
| Ubuntu userspace | ✅ 26.04 LTS Resolute Raccoon | ✅ 26.04 LTS |
| Kernel | ❌ phone ka **Android kernel** hi chalta hai | ✅ Ubuntu ka **Linux 7.0** |
| `uname -r` kya dikhata hai | `6.17.0-PRoot-Distro` (proot ki fixed string, `--kernel` se badal sakti hai) | `7.0.0-xx-generic` |

proot-distro ek *userspace* container hai — woh Android ke kernel ke upar chalta hai,
isliye Ubuntu 26.04 ka Linux 7.0 kernel phone ke andar boot nahi ho sakta. Yeh limitation
kisi bhi Termux/proot setup ki hai, is build ki nahi.

- Ubuntu 26.04 LTS release: 23 April 2026, kernel **Linux 7.0**, support April 2031 tak.
- Real 7.0 kernel chahiye to phone par VM app + qcow2 image use kijiye (aapke paas
  `ratan-os-release.html` par QCOW2 already hai).
- Cosmetic chahiye to: `proot-distro login ubuntu --kernel 7.0.0-38-generic`
  (sirf `uname -r` ki string badalti hai, kernel nahi).

## 6. Files

| File | Kaam |
|---|---|
| `ratan.py` | agent khud (single file, Python 3.9+; tests Python 3.11 par chalaye gaye) |
| `install-termux.sh` | phone/Termux side installer |
| `install-ubuntu.sh` | Ubuntu side installer (proot ke andar chalta hai) |
| `tests/test_ratan.py` | offline test-suite (mock HF router ke saath) |

## 7. Bina installer ke manual setup

Ubuntu/Debian par:

```bash
sudo apt-get install -y python3 python3-venv ca-certificates curl
python3 -m venv ~/.ratan/venv
~/.ratan/venv/bin/pip install -U huggingface_hub
cp ratan.py ~/.ratan/ratan.py
echo 'alias ratan="$HOME/.ratan/venv/bin/python $HOME/.ratan/ratan.py"' >> ~/.bashrc
source ~/.bashrc && ratan doctor
```

`huggingface_hub` na ho to bhi chalega — agent stdlib (`urllib`) backend par
automatic chala jaata hai. `ratan doctor` batata hai kaunsa backend use ho raha hai
aur SDK kyun nahi mila.

## 8. Local / private model (offline PC se)

Koi bhi OpenAI-compatible server chalta hai — jaise laptop par llama.cpp:

```bash
ratan config base_url=http://192.168.1.10:8080/v1
ratan --model qwen3-4b
```

## 9. Config

`~/.ratan/config.json` (ya `ratan config key=value`):
`model`, `token`, `provider`, `base_url`, `max_tokens`, `temperature`,
`auto_approve`, `tools`, `language`, `session`.

Environment variables: `HF_TOKEN`, `RATAN_MODEL`, `RATAN_BASE_URL`,
`RATAN_PROVIDER`, `RATAN_BACKEND` (`auto`/`sdk`/`raw`), `RATAN_HOME`.

## 10. Tests chalana

```bash
cd ratan-agent
python3 -m unittest discover -s tests -v      # 28 tests, network ki zaroorat nahi
```

Test-suite ek local mock Hugging Face router khada karta hai, isliye dono backend
(SDK + stdlib), SSE streaming, tool-calling loop, safety blocks aur sessions
actually execute hote hain.

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `HTTP 401/403` | token missing/wrong → `ratan login`, permission "Make calls to Inference Providers" honi chahiye |
| `HTTP 429` | free-tier limit → thoda rukiye, ya `ratan --model <doosra model>` |
| `router: unreachable` | mobile data/Wi-Fi check; `ratan doctor` |
| `proot-distro: command not found` | `pkg install proot-distro` |
| Ubuntu tag na mile | `proot-distro list` dekhiye; `UBUNTU_TAG=24.04 bash install-termux.sh` |
| Slow answers | `ratan config set max_tokens=512`, ya chhota model |

## 12. Safety / authorized use

`ratan` aapke hi terminal mein chalta hai aur sirf wahi karta hai jiski aap approval
dete hain. Security testing sirf un systems par kijiye jinki **written authorization**
aapke paas hai. DDoS, credential attacks, phishing, malware, persistence, exfiltration
aur destructive activity is project ke scope se bahar hain.

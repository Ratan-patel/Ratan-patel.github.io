# RatanSec Super Agent — full image (Kali rolling + tools)
# Build:  docker build -f superagent/Dockerfile -t ratansec-superagent .
# Run:    docker run --rm -p 8000:8000 --env-file .env ratansec-superagent
FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SUPERAGENT_DATA_DIR=/data \
    HOST=0.0.0.0 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv ca-certificates curl wget git procps \
      whois dnsutils traceroute iputils-ping netcat-openbsd nmap masscan \
      nikto whatweb gobuster ffuf sqlmap hydra medusa ncrack netexec \
      smbclient smbmap enum4linux-ng snmp snmpcheck nbtscan ldap-utils nfs-common \
      aircrack-ng reaver wifite responder bettercap proxychains4 socat jq openssl \
      exploitdb seclists wordlists hashcat john cewl crunch \
      nuclei testssl.sh openssh-client && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# optional extras — fail hone par build nahi rukta
RUN apt-get update && ( \
      apt-get install -y --no-install-recommends subfinder amass theharvester dnsrecon fierce dmitry \
        wafw00f sslscan zaproxy wapiti commix xsstrike feroxbuster dirsearch wpscan joomscan \
        websocat patator 2>/dev/null || true ) && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir fastapi 'uvicorn[standard]' pydantic httpx \
      arjun hashid ldapdomaindump impacket jwt-tool 2>/dev/null || \
    pip3 install --no-cache-dir fastapi 'uvicorn[standard]' pydantic httpx

# apt se na milne wale tools (best-effort)
RUN pip3 install --break-system-packages --no-cache-dir pipx >/dev/null 2>&1 || true; \
    (pipx install crackmapexec || pipx install netexec) >/dev/null 2>&1 || true; \
    (pipx install theHarvester) >/dev/null 2>&1 || true; \
    (pipx install mitmproxy) >/dev/null 2>&1 || true

RUN (nuclei -update-templates -silent || true) 2>/dev/null; \
    mkdir -p /data && useradd -m -u 1001 agent && chown -R agent:agent /data

WORKDIR /app
COPY superagent /app/superagent
COPY scripts /app/scripts
COPY docs /app/docs || true

USER agent
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["python3", "-m", "uvicorn", "superagent.webui:app", "--host", "0.0.0.0", "--port", "8000"]

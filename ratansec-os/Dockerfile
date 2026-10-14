# RatanSec OS — Kali Linux based AI pentest environment
# Build:  docker build -t ratansec-os .
# Run:    docker run --rm -p 8000:8000 --env-file .env --cap-add=NET_RAW --cap-add=NET_ADMIN ratansec-os
#
# Note: image ~2.5-3.5 GB hoti hai (Kali + tools). 25 MB me OS + tools possible nahi hain —
# isliye yeh cloud/VPS ke liye bana hai, local low-size ke liye CLI core (app/) use karo.

FROM kalilinux/kali-rolling

LABEL org.opencontainers.image.title="RatanSec OS" \
      org.opencontainers.image.description="AI-powered pentest environment (Kali tools + OpenRouter AI copilot)" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/Ratan-patel/Ratan-patel.github.io"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATA_DIR=/app/data \
    PATH="/opt/venv/bin:$PATH"

# ---------- 1) Base + Python ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip \
      ca-certificates curl dnsutils whois netcat-openbsd git \
 && rm -rf /var/lib/apt/lists/*

# ---------- 2) Security tooling (Kali repos) ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
      nmap \
      nikto \
      whatweb \
      gobuster \
      ffuf \
      nuclei \
      sqlmap \
      hydra \
      dirb \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Wordlists: dirb common.txt sabse practical (chhota + kaam ka).
# Pura SecLists chahiye to: apt-get install -y seclists (image bada ho jayega)

# ---------- 3) Python app ----------
RUN python3 -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# ---------- 4) Nuclei templates (optional, build-time) ----------
# Default off rakha hai (build fast + slim rehne ke liye).
# Enable: docker build --build-arg INSTALL_NUCLEI_TEMPLATES=1 -t ratansec-os .
ARG INSTALL_NUCLEI_TEMPLATES=0
RUN if [ "$INSTALL_NUCLEI_TEMPLATES" = "1" ]; then \
      nuclei -update-templates -duc -no-color -silent || true; \
    fi

WORKDIR /app
COPY app ./app
COPY cli.py ./cli.py
COPY scripts ./scripts
RUN chmod +x /app/scripts/*.sh && mkdir -p /app/data/reports

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["python", "-m", "app.webui"]

import urllib.request
import ssl
import json
import socket
from urllib.parse import urlparse

class VAPTSecurityAuditor:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.parsed = urlparse(target_url)
        self.report = {"target": target_url, "findings": [], "score": 100}

    def audit_security_headers(self):
        req = urllib.request.Request(self.target_url, headers={'User-Agent': 'Ratan-VAPT-Scanner/2.0'})
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                headers = {k.lower(): v for k, v in response.getheaders()}
                
                # Check critical OWASP security headers
                checks = {
                    "strict-transport-security": "Missing HSTS Header (High)",
                    "x-frame-options": "Missing Clickjacking Protection (Medium)",
                    "x-content-type-options": "Missing MIME-Sniffing Protection (Low)",
                    "content-security-policy": "Missing Content Security Policy (High)",
                    "referrer-policy": "Missing Referrer-Policy Header (Low)"
                }
                
                for header, issue in checks.items():
                    if header not in headers:
                        self.report["findings"].append({"type": "HEADER_MISSING", "detail": issue})
                        self.report["score"] -= 10
        except Exception as e:
            self.report["findings"].append({"type": "CONNECTION_ERROR", "detail": str(e)})

    def audit_ssl_tls(self):
        hostname = self.parsed.hostname or self.target_url
        ctx = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    tls_ver = ssock.version()
                    self.report["tls_version"] = tls_ver
                    if tls_ver in ["TLSv1", "TLSv1.1"]:
                        self.report["findings"].append({"type": "DEPRECATED_TLS", "detail": f"Insecure Protocol: {tls_ver}"})
                        self.report["score"] -= 25
        except Exception as e:
            self.report["findings"].append({"type": "TLS_AUDIT_SKIPPED", "detail": str(e)})

    def run_full_audit(self) -> dict:
        self.audit_security_headers()
        self.audit_ssl_tls()
        self.report["security_grade"] = "A" if self.report["score"] >= 80 else ("B" if self.report["score"] >= 60 else "C")
        return self.report

if __name__ == "__main__":
    scanner = VAPTSecurityAuditor("https://ratan-patel.github.io")
    print(json.dumps(scanner.run_full_audit(), indent=2))

package com.ratansec.superagent

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.URL
import java.security.cert.X509Certificate
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLSocket
import javax.net.ssl.SSLSocketFactory

/**
 * Phone par chalne wale bounded, non-destructive checks.
 *
 * Rules (server wale v2 jaise hi):
 *  - target scope me authorized hona chahiye
 *  - redirects follow nahi hote, credentials/cookies nahi bheje jate
 *  - response body read nahi hota (sirf 2 well-known public text files, 16 KiB cap)
 *  - private/loopback/metadata addresses default roop se blocked
 *  - har call bounded timeout ke andar
 */
class Probes(private val store: Store) {

    class ProbeError(message: String) : Exception(message)

    private val timeoutMs = 12_000
    private val maxTextBytes = 16_384

    // --- Safety ------------------------------------------------------------
    private fun requireAuthorized(host: String) {
        if (store.authorized(host) == null) {
            throw ProbeError("'$host' scope me nahi hai. Pehle Scope tab me target add karo (likhit permission ke saath).")
        }
    }

    private fun checkAddress(address: InetAddress, host: String) {
        val ip = address.hostAddress ?: ""
        if (address.isLoopbackAddress || address.isAnyLocalAddress || address.isLinkLocalAddress ||
            address.isMulticastAddress || ip.startsWith("169.254.")
        ) {
            throw ProbeError("Address $ip safety policy se blocked hai (loopback/link-local/metadata).")
        }
        if ((address.isSiteLocalAddress || ip.startsWith("100.")) && !store.allowPrivate) {
            throw ProbeError("Address $ip private hai. Private testing ke liye Settings me 'Allow private targets' on karo.")
        }
        if (host.isNotEmpty() && store.authorized(host) == null) {
            throw ProbeError("Host scope me nahi hai.")
        }
    }

    private fun resolve(host: String): List<InetAddress> {
        val addresses = try {
            InetAddress.getAllByName(host).toList()
        } catch (exc: Exception) {
            throw ProbeError("DNS resolve fail: ${exc.message ?: exc.javaClass.simpleName}")
        }
        if (addresses.isEmpty()) throw ProbeError("DNS ne koi address nahi diya.")
        addresses.forEach { checkAddress(it, host) }
        return addresses
    }

    // --- Probes ------------------------------------------------------------
    fun dns(host: String): JSONObject {
        requireAuthorized(host)
        val started = System.currentTimeMillis()
        val addresses = resolve(host)
        val data = JSONObject()
            .put("host", host)
            .put("addresses", JSONArray(addresses.map { it.hostAddress ?: "" }))
        return result("dns", data, JSONArray(), started)
    }

    fun httpHeaders(target: String): JSONObject {
        val url = parseTarget(target)
        val host = url.host
        requireAuthorized(host)
        resolve(host)
        val started = System.currentTimeMillis()
        val connection = open(url)
        val findings = JSONArray()
        try {
            connection.requestMethod = "GET"
            connection.connect()
            val headers = JSONObject()
            connection.headerFields.forEach { (name, values) ->
                if (name != null && name.lowercase() !in SENSITIVE_HEADERS) {
                    headers.put(name, values.joinToString("; "))
                }
            }
            val code = connection.responseCode
            fun header(name: String): String = connection.getHeaderField(name) ?: ""

            if (url.protocol == "https" && header("Strict-Transport-Security").isEmpty()) {
                findings.put(finding("WEB-HSTS-001", "medium", "HSTS header missing",
                    "Strict-Transport-Security response me nahi mila.",
                    "Strict-Transport-Security: max-age=31536000; includeSubDomains add karo."))
            }
            if (header("Content-Security-Policy").isEmpty()) {
                findings.put(finding("WEB-CSP-001", "medium", "Content Security Policy missing",
                    "Content-Security-Policy header nahi mila.",
                    "Ek restrictive CSP define karo (default-src 'self' se shuru)."))
            }
            if (!header("X-Content-Type-Options").equals("nosniff", true)) {
                findings.put(finding("WEB-NOSNIFF-001", "low", "MIME sniffing protection missing",
                    "X-Content-Type-Options: nosniff nahi mila.",
                    "X-Content-Type-Options: nosniff set karo."))
            }
            if (header("Referrer-Policy").isEmpty()) {
                findings.put(finding("WEB-REFERRER-001", "low", "Referrer Policy missing",
                    "Referrer-Policy header nahi mila.",
                    "Referrer-Policy: strict-origin-when-cross-origin set karo."))
            }
            val server = header("Server")
            if (server.isNotEmpty() && server.any { it.isDigit() }) {
                findings.put(finding("WEB-BANNER-001", "info", "Server version disclosed",
                    "Server: $server", "Version banner hata do (generic naam rakho)."))
            }
            if (code in 300..399) {
                findings.put(finding("WEB-REDIRECT-001", "info", "Redirect observed (not followed)",
                    "HTTP $code → ${header("Location")}",
                    "Redirect chain review karo; open redirect na ho."))
            }
            val data = JSONObject()
                .put("url", "${url.protocol}://$host${url.path.ifEmpty { "/" }}")
                .put("status", code)
                .put("headers", headers)
            return result("http_headers", data, findings, started)
        } catch (exc: ProbeError) {
            throw exc
        } catch (exc: Exception) {
            throw ProbeError("HTTP request fail: ${exc.message ?: exc.javaClass.simpleName}")
        } finally {
            connection.disconnect()
        }
    }

    fun tls(host: String, port: Int = 443): JSONObject {
        requireAuthorized(host)
        resolve(host)
        val started = System.currentTimeMillis()
        val findings = JSONArray()
        var socket: SSLSocket? = null
        try {
            val factory = SSLSocketFactory.getDefault() as SSLSocketFactory
            socket = factory.createSocket() as SSLSocket
            socket.connect(InetSocketAddress(host, port), timeoutMs)
            socket.soTimeout = timeoutMs
            socket.startHandshake()
            val protocol = socket.session.protocol
            val chain = socket.session.peerCertificates
            val certificate = chain.firstOrNull() as? X509Certificate
                ?: throw ProbeError("Certificate parse nahi hua.")
            val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
                timeZone = TimeZone.getTimeZone("UTC")
            }
            val daysLeft = ((certificate.notAfter.time - System.currentTimeMillis()) / 86_400_000L).toInt()
            if (daysLeft < 0) {
                findings.put(finding("TLS-EXPIRED-001", "high", "TLS certificate expired",
                    "notAfter=${format.format(certificate.notAfter)}", "Certificate turant renew karo."))
            } else if (daysLeft < 21) {
                findings.put(finding("TLS-EXPIRING-001", "medium", "TLS certificate expires soon",
                    "$daysLeft din bache hain.", "Renewal automate karo (ACME)."))
            }
            if (protocol in setOf("TLSv1", "TLSv1.1", "SSLv3")) {
                findings.put(finding("TLS-OLD-001", "high", "Legacy TLS protocol negotiated",
                    "protocol=$protocol", "TLS 1.2+ rakho, purane protocols band karo."))
            }
            val names = JSONArray()
            runCatching {
                certificate.subjectAlternativeNames?.forEach { entry ->
                    if (entry.size >= 2) names.put(entry[1].toString())
                }
            }
            val data = JSONObject()
                .put("host", host)
                .put("protocol", protocol)
                .put("cipher", socket.session.cipherSuite)
                .put("subject", certificate.subjectX500Principal.name)
                .put("issuer", certificate.issuerX500Principal.name)
                .put("not_before", format.format(certificate.notBefore))
                .put("not_after", format.format(certificate.notAfter))
                .put("days_left", daysLeft)
                .put("san", names)
            return result("tls", data, findings, started)
        } catch (exc: ProbeError) {
            throw exc
        } catch (exc: Exception) {
            throw ProbeError("TLS handshake fail: ${exc.message ?: exc.javaClass.simpleName}")
        } finally {
            runCatching { socket?.close() }
        }
    }

    fun textFile(target: String, kind: String): JSONObject {
        val base = parseTarget(target)
        val host = base.host
        requireAuthorized(host)
        resolve(host)
        val path = if (kind == "security_txt") "/.well-known/security.txt" else "/robots.txt"
        val url = URL("${base.protocol}://$host${if (base.port > 0) ":${base.port}" else ""}$path")
        val started = System.currentTimeMillis()
        val connection = open(url)
        try {
            connection.requestMethod = "GET"
            connection.connect()
            val code = connection.responseCode
            val findings = JSONArray()
            var body = ""
            if (code == 200) {
                connection.inputStream.use { stream ->
                    val buffer = ByteArray(maxTextBytes)
                    val read = stream.read(buffer)
                    if (read > 0) body = String(buffer, 0, read, Charsets.UTF_8)
                }
            } else if (kind == "security_txt") {
                findings.put(finding("WEB-SECTXT-001", "info", "security.txt not found",
                    "HTTP $code at $path",
                    "/.well-known/security.txt publish karo taaki researchers contact kar saken."))
            }
            val data = JSONObject().put("url", url.toString()).put("status", code).put("text", body)
            return result(kind, data, findings, started)
        } catch (exc: Exception) {
            throw ProbeError("$path fetch fail: ${exc.message ?: exc.javaClass.simpleName}")
        } finally {
            connection.disconnect()
        }
    }

    // --- helpers -----------------------------------------------------------
    private fun parseTarget(target: String): URL {
        var raw = target.trim()
        if (raw.isEmpty()) throw ProbeError("Target khali hai.")
        if (!raw.startsWith("http://") && !raw.startsWith("https://")) raw = "https://$raw"
        val url = runCatching { URL(raw) }.getOrNull() ?: throw ProbeError("Target URL invalid hai.")
        if (url.protocol !in setOf("http", "https")) throw ProbeError("Sirf http/https allowed hai.")
        if (!url.userInfo.isNullOrEmpty()) throw ProbeError("URL me credentials allowed nahi hain.")
        if (Store.normalizeHost(url.host).isEmpty()) throw ProbeError("Host invalid hai.")
        return url
    }

    private fun open(url: URL): HttpURLConnection {
        val connection = url.openConnection() as HttpURLConnection
        connection.instanceFollowRedirects = false
        connection.connectTimeout = timeoutMs
        connection.readTimeout = timeoutMs
        connection.useCaches = false
        connection.setRequestProperty("User-Agent", "RatanSecAgent/${Store.VERSION} (authorized-assessment)")
        connection.setRequestProperty("Accept", "*/*")
        if (connection is HttpsURLConnection) {
            connection.hostnameVerifier = HttpsURLConnection.getDefaultHostnameVerifier()
        }
        return connection
    }

    private fun result(id: String, data: JSONObject, findings: JSONArray, started: Long): JSONObject =
        JSONObject()
            .put("id", id)
            .put("status", "ok")
            .put("data", data)
            .put("findings", findings)
            .put("duration_ms", System.currentTimeMillis() - started)
            .put("ts", System.currentTimeMillis())

    private fun finding(code: String, severity: String, title: String, evidence: String, remediation: String) =
        JSONObject()
            .put("code", code)
            .put("severity", severity)
            .put("title", title)
            .put("evidence", evidence)
            .put("remediation", remediation)
            .put("confidence", "high")
            .put("status", "observed")

    companion object {
        private val SENSITIVE_HEADERS = setOf("set-cookie", "authorization", "proxy-authorization")
    }
}

package io.github.ratanpatel.ratanagent;

import java.util.Locale;

/**
 * Host classification used by the native HTTP engine.
 *
 * The shell can talk to: (a) the public internet over HTTPS, (b) anything on the local
 * network — where every pentest lab lives — and (c) plain HTTP only when the operator has
 * explicitly allowed it for that class of host. Redirects are re-checked hop by hop, so a
 * public HTTPS endpoint cannot bounce the app into a blocked destination.
 */
public final class NetPolicy {

    private NetPolicy() {
    }

    /** Loopback, RFC1918, CGNAT, link-local, ULA and mDNS-style lab names. */
    public static boolean isPrivateHost(String host) {
        if (host == null) {
            return false;
        }
        String h = host.trim().toLowerCase(Locale.US);
        if (h.isEmpty()) {
            return false;
        }
        if (h.startsWith("[") && h.endsWith("]")) {
            h = h.substring(1, h.length() - 1);
        }
        if (h.equals("localhost") || h.endsWith(".localhost") || h.equals("::1") || h.equals("0:0:0:0:0:0:0:1")) {
            return true;
        }
        if (h.endsWith(".local") || h.endsWith(".internal") || h.endsWith(".lan")
                || h.endsWith(".home.arpa") || h.endsWith(".lab") || h.endsWith(".test")) {
            return true;
        }
        if (h.contains(":")) {
            // IPv6: unique-local (fc00::/7) and link-local (fe80::/10)
            if (h.startsWith("fc") || h.startsWith("fd")) {
                return true;
            }
            return h.startsWith("fe8") || h.startsWith("fe9") || h.startsWith("fea") || h.startsWith("feb");
        }
        int[] octets = ipv4(h);
        if (octets == null) {
            return false;
        }
        int a = octets[0];
        int b = octets[1];
        if (a == 10 || a == 127 || a == 0) {
            return true;
        }
        if (a == 192 && b == 168) {
            return true;
        }
        if (a == 172 && b >= 16 && b <= 31) {
            return true;
        }
        if (a == 169 && b == 254) {
            return true;
        }
        // CGNAT / tailnet-style ranges are local enough to count as lab space
        return a == 100 && b >= 64 && b <= 127;
    }

    private static int[] ipv4(String host) {
        String[] parts = host.split("\\.");
        if (parts.length != 4) {
            return null;
        }
        int[] values = new int[4];
        for (int i = 0; i < 4; i++) {
            if (parts[i].isEmpty() || parts[i].length() > 3) {
                return null;
            }
            for (int j = 0; j < parts[i].length(); j++) {
                if (!Character.isDigit(parts[i].charAt(j))) {
                    return null;
                }
            }
            values[i] = Integer.parseInt(parts[i]);
            if (values[i] > 255) {
                return null;
            }
        }
        return values;
    }
}

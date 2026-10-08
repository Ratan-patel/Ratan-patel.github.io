package io.github.ratanpatel.ratanagent;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import android.util.Log;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Secret storage for provider credentials, backed by the hardware-protected Android Keystore.
 *
 * Why not SharedPreferences directly? An API key is a bearer credential: anyone who can read the
 * app's data directory (root, a backup, an ADB pull on a debuggable build, a rented device) owns
 * every request the key can make. Here the key material is generated inside the Keystore and can
 * never be exported, only used to wrap/unwrap values, and the ciphertext lives in its own
 * preference file.
 *
 * AES-256-GCM, a fresh random IV per write, tag length 128 bits. Values are stored as
 * {@code base64(IV || ciphertext||tag)}. Everything is best-effort: if a device's Keystore is
 * unavailable the callers degrade to "no key configured" and tell the operator, rather than
 * silently writing plaintext.
 */
public final class SecureStore {

    private static final String TAG = "RatanSecureStore";
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String ALIAS = "ratan_agent_secret_v1";
    private static final String FILE = "ratan_agent_secrets";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int TAG_BITS = 128;

    private final SharedPreferences prefs;

    public SecureStore(Context context) {
        this.prefs = context.getApplicationContext().getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    /** True when a usable Keystore key exists (or could be created). */
    public boolean isAvailable() {
        return secretKey() != null;
    }

    public boolean has(String name) {
        return name != null && prefs.contains(name);
    }

    /** Stores a secret. Throws when the Keystore cannot be used — callers must not fall back to plaintext. */
    public void put(String name, String value) throws Exception {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("name is required");
        }
        if (value == null || value.isEmpty()) {
            remove(name);
            return;
        }
        SecretKey key = secretKey();
        if (key == null) {
            throw new IllegalStateException("Android Keystore is unavailable on this device");
        }
        Cipher cipher = Cipher.getInstance(TRANSFORMATION);
        cipher.init(Cipher.ENCRYPT_MODE, key);          // Keystore supplies the random IV
        byte[] ciphertext = cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
        byte[] iv = cipher.getIV();
        byte[] payload = new byte[iv.length + ciphertext.length];
        System.arraycopy(iv, 0, payload, 0, iv.length);
        System.arraycopy(ciphertext, 0, payload, iv.length, ciphertext.length);
        prefs.edit().putString(name, Base64.encodeToString(payload, Base64.NO_WRAP)).apply();
    }

    /** Returns the secret, or null when absent/undecryptable. Never throws. */
    public String get(String name) {
        if (name == null) {
            return null;
        }
        String stored = prefs.getString(name, null);
        if (stored == null || stored.isEmpty()) {
            return null;
        }
        try {
            SecretKey key = secretKey();
            if (key == null) {
                return null;
            }
            byte[] payload = Base64.decode(stored, Base64.NO_WRAP);
            if (payload.length <= 12) {
                return null;
            }
            byte[] iv = new byte[12];
            byte[] ciphertext = new byte[payload.length - 12];
            System.arraycopy(payload, 0, iv, 0, 12);
            System.arraycopy(payload, 12, ciphertext, 0, ciphertext.length);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        } catch (Exception exc) {
            Log.w(TAG, "could not decrypt " + name + ": " + exc.getClass().getSimpleName());
            return null;
        }
    }

    public void remove(String name) {
        if (name != null) {
            prefs.edit().remove(name).apply();
        }
    }

    /**
     * A display-only fingerprint of a stored secret: the last few characters. The full value is
     * never handed back to the web layer, so a compromised page cannot read the key it just set.
     */
    public String hint(String name, int keepTail) {
        String value = get(name);
        if (value == null || value.isEmpty()) {
            return "";
        }
        int tail = Math.max(2, Math.min(keepTail, value.length()));
        return "…" + value.substring(value.length() - tail);
    }

    private SecretKey secretKey() {
        try {
            KeyStore keyStore = KeyStore.getInstance(KEYSTORE);
            keyStore.load(null);
            if (keyStore.containsAlias(ALIAS)) {
                java.security.Key existing = keyStore.getKey(ALIAS, null);
                if (existing instanceof SecretKey) {
                    return (SecretKey) existing;
                }
            }
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
            generator.init(new KeyGenParameterSpec.Builder(ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .setRandomizedEncryptionRequired(true)   // no IV reuse, ever
                    .build());
            return generator.generateKey();
        } catch (Exception exc) {
            Log.w(TAG, "keystore unavailable: " + exc.getClass().getSimpleName());
            return null;
        }
    }
}

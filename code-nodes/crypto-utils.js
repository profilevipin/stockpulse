/**
 * StockPulse v3.2 — Encryption Module
 * AES-256-GCM with random IV and authentication tag.
 * Used for encrypting Kite API tokens at rest in PostgreSQL.
 *
 * Usage in n8n Code node:
 *   const encrypted = encrypt(plaintext, process.env.ENCRYPTION_KEY);
 *   const decrypted = decrypt(encrypted, process.env.ENCRYPTION_KEY);
 */

const crypto = require('crypto');

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16;
const AUTH_TAG_LENGTH = 16;

function encrypt(plaintext, keyHex) {
    const key = Buffer.from(keyHex, 'hex');
    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv(ALGORITHM, key, iv);

    let encrypted = cipher.update(plaintext, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    const authTag = cipher.getAuthTag().toString('hex');

    // Format: iv:authTag:ciphertext
    return `${iv.toString('hex')}:${authTag}:${encrypted}`;
}

function decrypt(encryptedStr, keyHex) {
    const key = Buffer.from(keyHex, 'hex');
    const [ivHex, authTagHex, ciphertext] = encryptedStr.split(':');

    const iv = Buffer.from(ivHex, 'hex');
    const authTag = Buffer.from(authTagHex, 'hex');
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(authTag);

    let decrypted = decipher.update(ciphertext, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
}

module.exports = { encrypt, decrypt };

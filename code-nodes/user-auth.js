/**
 * StockPulse v3.2 — User Authentication Module
 * Checks telegram_user_id against whitelist in users table.
 * Enforces per-user rate limiting (30 messages/hour).
 */

// Rate limit tracking (in-memory, resets on n8n restart)
const rateLimits = new Map();

function checkRateLimit(userId, maxPerHour = 30) {
    const now = Date.now();
    const windowMs = 60 * 60 * 1000; // 1 hour

    if (!rateLimits.has(userId)) {
        rateLimits.set(userId, []);
    }

    const timestamps = rateLimits.get(userId).filter(t => now - t < windowMs);
    timestamps.push(now);
    rateLimits.set(userId, timestamps);

    return {
        allowed: timestamps.length <= maxPerHour,
        count: timestamps.length,
        limit: maxPerHour,
        remaining: Math.max(0, maxPerHour - timestamps.length)
    };
}

function isAuthorized(userRow) {
    return userRow && userRow.is_active === true;
}

function isAdmin(userRow) {
    return userRow && userRow.is_admin === true;
}

function isKiteProvider(userRow) {
    return userRow && userRow.is_kite_provider === true;
}

module.exports = { checkRateLimit, isAuthorized, isAdmin, isKiteProvider };

/**
 * StockPulse v3.2 — Input Validation Module
 * Use in n8n Code nodes for sanitizing all user-derived input.
 */

function validateSymbol(input) {
    if (!input || typeof input !== 'string') return null;
    const clean = input.toUpperCase().replace(/[^A-Z0-9&-]/g, '');
    if (clean.length < 1 || clean.length > 20) return null;
    return clean;
}

function validatePrice(input) {
    const price = parseFloat(input);
    if (isNaN(price) || price <= 0 || price >= 10000000) return null;
    return Math.round(price * 100) / 100; // 2 decimal places
}

function validateQuantity(input) {
    const qty = parseInt(input);
    if (isNaN(qty) || qty <= 0 || qty >= 1000000) return null;
    return qty;
}

function validateMessage(input) {
    if (!input || typeof input !== 'string') return '';
    return input.substring(0, 2000).trim();
}

function validateNotes(input) {
    if (!input || typeof input !== 'string') return '';
    return input.substring(0, 500).trim();
}

function validateDate(input) {
    if (!input) return new Date().toISOString().split('T')[0];
    const date = new Date(input);
    if (isNaN(date.getTime())) return new Date().toISOString().split('T')[0];
    return date.toISOString().split('T')[0];
}

function validateTradeType(input) {
    if (!input || typeof input !== 'string') return null;
    const upper = input.toUpperCase().trim();
    if (['BUY', 'SELL'].includes(upper)) return upper;
    if (['BOUGHT', 'PURCHASED'].includes(upper)) return 'BUY';
    if (['SOLD'].includes(upper)) return 'SELL';
    return null;
}

module.exports = {
    validateSymbol,
    validatePrice,
    validateQuantity,
    validateMessage,
    validateNotes,
    validateDate,
    validateTradeType
};

/**
 * StockPulse v3.2 — Market Hours Checker
 * Determines if Indian stock market (NSE) is currently open.
 * Accounts for weekends, market holidays, and pre/post market windows.
 */

function isMarketOpen(holidays = []) {
    const now = new Date();
    // Convert to IST (UTC+5:30)
    const istOffset = 5.5 * 60 * 60 * 1000;
    const ist = new Date(now.getTime() + istOffset + now.getTimezoneOffset() * 60 * 1000);

    const day = ist.getDay(); // 0=Sun, 6=Sat
    if (day === 0 || day === 6) return { open: false, reason: 'weekend' };

    const dateStr = ist.toISOString().split('T')[0];
    if (holidays.includes(dateStr)) return { open: false, reason: 'holiday' };

    const hours = ist.getHours();
    const minutes = ist.getMinutes();
    const timeMinutes = hours * 60 + minutes;

    const MARKET_OPEN = 9 * 60 + 15;   // 9:15 AM
    const MARKET_CLOSE = 15 * 60 + 30;  // 3:30 PM

    if (timeMinutes < MARKET_OPEN) return { open: false, reason: 'pre_market', opensIn: MARKET_OPEN - timeMinutes };
    if (timeMinutes > MARKET_CLOSE) return { open: false, reason: 'post_market' };

    return { open: true, reason: 'trading_hours', ist: ist.toISOString() };
}

function isPreMarketWindow() {
    const now = new Date();
    const istOffset = 5.5 * 60 * 60 * 1000;
    const ist = new Date(now.getTime() + istOffset + now.getTimezoneOffset() * 60 * 1000);
    const timeMinutes = ist.getHours() * 60 + ist.getMinutes();
    return timeMinutes >= 7 * 60 && timeMinutes < 9 * 60 + 15; // 7:00 - 9:15 AM
}

module.exports = { isMarketOpen, isPreMarketWindow };

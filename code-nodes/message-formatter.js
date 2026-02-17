/**
 * StockPulse v3.2 — Message Formatter
 * Formats bot responses for Telegram markdown.
 * Handles: portfolio display, alert notifications, inline buttons, truncation.
 */

const TELEGRAM_MAX_LENGTH = 4096;

function formatPortfolio(holdings, quotes) {
    if (!holdings || holdings.length === 0) {
        return '📭 *No holdings found*\n\nStart by logging a trade:\n`buy RELIANCE 10 at 2850`';
    }

    let msg = '📊 *Your Portfolio*\n\n';
    let totalInvested = 0, totalCurrent = 0;

    for (const h of holdings) {
        const key = `NSE:${h.symbol}`;
        const ltp = quotes?.[key]?.last_price || null;
        const invested = h.net_quantity * h.avg_buy_price;
        totalInvested += invested;

        if (ltp) {
            const current = h.net_quantity * ltp;
            totalCurrent += current;
            const pnl = current - invested;
            const pnlPct = ((pnl / invested) * 100).toFixed(1);
            const emoji = pnl >= 0 ? '🟢' : '🔴';
            msg += `${emoji} *${h.symbol}*\n`;
            msg += `   ${h.net_quantity} × ₹${h.avg_buy_price} → ₹${ltp}\n`;
            msg += `   P&L: ₹${Math.round(pnl).toLocaleString()} (${pnlPct}%)\n\n`;
        } else {
            totalCurrent += invested;
            msg += `⚪ *${h.symbol}*\n`;
            msg += `   ${h.net_quantity} × ₹${h.avg_buy_price}\n\n`;
        }
    }

    const totalPnl = totalCurrent - totalInvested;
    const totalPnlPct = totalInvested > 0 ? ((totalPnl / totalInvested) * 100).toFixed(1) : '0.0';
    msg += `━━━━━━━━━━━━━━━━━━\n`;
    msg += `${totalPnl >= 0 ? '📈' : '📉'} *Total P&L: ₹${Math.round(totalPnl).toLocaleString()} (${totalPnlPct}%)*\n`;
    msg += `💰 Invested: ₹${Math.round(totalInvested).toLocaleString()}`;

    return truncate(msg);
}

function formatAlertsList(alerts) {
    if (!alerts || alerts.length === 0) {
        return '🔔 *No active alerts*\n\nSet one:\n`alert RELIANCE 2800-2950`';
    }

    let msg = '🔔 *Active Alerts*\n\n';
    for (const a of alerts) {
        const bounds = [];
        if (a.lower_bound) bounds.push(`⬇️ ₹${a.lower_bound}`);
        if (a.upper_bound) bounds.push(`⬆️ ₹${a.upper_bound}`);
        msg += `*${a.symbol}*: ${bounds.join(' | ')}\n`;
        if (a.cooldown_until && new Date(a.cooldown_until) > new Date()) {
            msg += `   ⏳ Cooldown until ${new Date(a.cooldown_until).toLocaleTimeString('en-IN')}\n`;
        }
    }
    return truncate(msg);
}

function formatTradeConfirmation(trade, type) {
    const emoji = type === 'BUY' ? '📈' : '📉';
    const total = trade.quantity * trade.price;
    return `✅ *${type} Logged*\n\n` +
        `${emoji} *${trade.symbol}*\n` +
        `   Qty: ${trade.quantity} shares\n` +
        `   Price: ₹${trade.price}\n` +
        `   Total: ₹${total.toLocaleString()}`;
}

function buildInlineButtons(symbol, context) {
    const buttons = [];
    if (context === 'alert_triggered') {
        buttons.push([
            { text: '💰 Sell', callback_data: `sell_${symbol}_market` },
            { text: '📊 Analysis', callback_data: `predict_${symbol}` }
        ]);
        buttons.push([
            { text: '🔔 Adjust Alert', callback_data: `alert_prompt_${symbol}` },
            { text: '❌ Cancel Alert', callback_data: `cancel_alert_${symbol}` }
        ]);
    } else if (context === 'trade_logged') {
        buttons.push([
            { text: '🔔 Set Alert', callback_data: `alert_prompt_${symbol}` },
            { text: '❌ Skip', callback_data: 'skip' }
        ]);
    } else if (context === 'csv_imported') {
        buttons.push([
            { text: '🔔 Set Alerts for All', callback_data: 'alert_all_holdings' },
            { text: '📊 View Portfolio', callback_data: 'portfolio' }
        ]);
    }
    return { inline_keyboard: buttons };
}

function truncate(msg) {
    if (msg.length <= TELEGRAM_MAX_LENGTH) return msg;
    return msg.substring(0, TELEGRAM_MAX_LENGTH - 20) + '\n\n_(truncated)_';
}

function splitMessage(msg) {
    if (msg.length <= TELEGRAM_MAX_LENGTH) return [msg];
    const parts = [];
    let remaining = msg;
    while (remaining.length > 0) {
        if (remaining.length <= TELEGRAM_MAX_LENGTH) {
            parts.push(remaining);
            break;
        }
        let splitAt = remaining.lastIndexOf('\n', TELEGRAM_MAX_LENGTH - 50);
        if (splitAt < TELEGRAM_MAX_LENGTH / 2) splitAt = TELEGRAM_MAX_LENGTH - 50;
        parts.push(remaining.substring(0, splitAt));
        remaining = remaining.substring(splitAt);
    }
    return parts;
}

module.exports = { formatPortfolio, formatAlertsList, formatTradeConfirmation, buildInlineButtons, truncate, splitMessage };

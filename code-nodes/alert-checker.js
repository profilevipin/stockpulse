/**
 * StockPulse v3.2 — Alert Checker Module
 * Compares live prices against alert bounds.
 * Features: hard triggers, proximity warnings, cooldown, explanation layer.
 */

function checkAlerts(alerts, quotes) {
    const now = new Date();
    const triggered = [];
    const approaching = [];
    const errors = [];

    for (const alert of alerts) {
        const key = `${alert.exchange || 'NSE'}:${alert.symbol}`;
        const quote = quotes[key];

        if (!quote || !quote.last_price) {
            errors.push({ alert_id: alert.id, symbol: alert.symbol, error: 'No quote data' });
            continue;
        }

        // Skip if in cooldown
        if (alert.cooldown_until && new Date(alert.cooldown_until) > now) continue;

        const price = quote.last_price;
        const dayChange = quote.net_change || 0;
        const dayChangePct = quote.day_change_pct || ((dayChange / (price - dayChange)) * 100);
        const volume = quote.volume || 0;
        const avgVol = quote.average_volume || volume;
        const volRatio = avgVol > 0 ? (volume / avgVol).toFixed(1) : '?';

        let result = null;

        // ===== HARD TRIGGERS =====
        if (alert.upper_bound && price >= parseFloat(alert.upper_bound)) {
            result = {
                trigger_type: 'HIT_UPPER',
                severity: 'high',
                new_status: 'triggered_upper',
                why: `Price ₹${price} crossed above upper bound ₹${alert.upper_bound}`,
                message: `📈 *${alert.symbol}* hit ₹${price}!\n` +
                    `Above your ₹${alert.upper_bound} upper bound\n` +
                    `Day: ${dayChange >= 0 ? '+' : ''}${dayChange.toFixed(1)} (${dayChangePct.toFixed(1)}%)\n` +
                    `Volume: ${volRatio}x avg`
            };
        } else if (alert.lower_bound && price <= parseFloat(alert.lower_bound)) {
            result = {
                trigger_type: 'HIT_LOWER',
                severity: 'high',
                new_status: 'triggered_lower',
                why: `Price ₹${price} dropped below lower bound ₹${alert.lower_bound}`,
                message: `📉 *${alert.symbol}* dropped to ₹${price}!\n` +
                    `Below your ₹${alert.lower_bound} lower bound\n` +
                    `Day: ${dayChange >= 0 ? '+' : ''}${dayChange.toFixed(1)} (${dayChangePct.toFixed(1)}%)\n` +
                    `Volume: ${volRatio}x avg`
            };
        }

        // ===== PROXIMITY ALERTS (within configured %) =====
        if (!result) {
            const proximityPct = parseFloat(alert.settings?.proximity_pct || 1.5);

            if (alert.upper_bound) {
                const distPct = ((parseFloat(alert.upper_bound) - price) / price) * 100;
                if (distPct > 0 && distPct <= proximityPct) {
                    result = {
                        trigger_type: 'APPROACHING_UPPER',
                        severity: 'medium',
                        new_status: 'active', // stays active
                        why: `Only ${distPct.toFixed(1)}% from upper target — momentum ${dayChangePct > 0 ? 'positive' : 'fading'}`,
                        message: `⚡ *${alert.symbol}* at ₹${price}\n` +
                            `${distPct.toFixed(1)}% from your ₹${alert.upper_bound} target\n` +
                            `Day: ${dayChange >= 0 ? '+' : ''}${dayChange.toFixed(1)} (${dayChangePct.toFixed(1)}%)`
                    };
                }
            }
            if (!result && alert.lower_bound) {
                const distPct = ((price - parseFloat(alert.lower_bound)) / price) * 100;
                if (distPct > 0 && distPct <= proximityPct) {
                    result = {
                        trigger_type: 'APPROACHING_LOWER',
                        severity: 'medium',
                        new_status: 'active',
                        why: `Only ${distPct.toFixed(1)}% from lower bound — watch for breakdown`,
                        message: `⚠️ *${alert.symbol}* at ₹${price}\n` +
                            `${distPct.toFixed(1)}% from your ₹${alert.lower_bound} floor\n` +
                            `Day: ${dayChange >= 0 ? '+' : ''}${dayChange.toFixed(1)} (${dayChangePct.toFixed(1)}%)`
                    };
                }
            }
        }

        if (result) {
            const cooldownMinutes = parseInt(alert.settings?.cooldown_minutes || 30);
            const cooldownUntil = new Date(now.getTime() + cooldownMinutes * 60 * 1000);

            const item = {
                alert_id: alert.id,
                user_id: alert.user_id,
                symbol: alert.symbol,
                current_price: price,
                ...result,
                cooldown_until: cooldownUntil.toISOString(),
                chat_id: alert.alerts_chat_id || alert.private_chat_id,
                display_name: alert.display_name,
                upper_bound: alert.upper_bound,
                lower_bound: alert.lower_bound,
                // Distance to both bounds for context
                upper_dist_pct: alert.upper_bound ? (((parseFloat(alert.upper_bound) - price) / price) * 100).toFixed(1) : null,
                lower_dist_pct: alert.lower_bound ? (((price - parseFloat(alert.lower_bound)) / price) * 100).toFixed(1) : null
            };

            if (result.severity === 'high') triggered.push(item);
            else approaching.push(item);
        }
    }

    return { triggered, approaching, errors };
}

module.exports = { checkAlerts };

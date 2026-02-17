/**
 * StockPulse v3.3 — Attention Score Calculator
 * Ranks stocks by "how much attention they need right now."
 * Used by: Morning Briefing (top 5), EOD (moved stocks), Portfolio (top 10).
 *
 * Score range: 0-100. Higher = needs more attention.
 */

function calculateAttentionScore(stock) {
    let score = 0;

    // 1. Alert proximity (highest weight)
    if (stock.alert_dist_pct !== null && stock.alert_dist_pct !== undefined) {
        if (stock.alert_dist_pct < 1) score += 40;       // <1% from target
        else if (stock.alert_dist_pct < 2) score += 30;   // <2%
        else if (stock.alert_dist_pct < 5) score += 15;   // <5%
    }

    // 2. Big daily move
    const absChange = Math.abs(stock.day_change_pct || 0);
    if (absChange > 4) score += 30;
    else if (absChange > 2) score += 20;
    else if (absChange > 1) score += 10;

    // 3. News sentiment impact
    const sentiment = Math.abs(stock.sentiment_score || 0);
    if (sentiment > 60) score += 15;
    else if (sentiment > 30) score += 8;

    // 4. Pattern detected today
    if (stock.pattern_detected) score += 15;

    // 5. Unusual volume
    const volRatio = stock.volume_ratio || 1;
    if (volRatio > 2.5) score += 15;
    else if (volRatio > 1.5) score += 8;

    // 6. RSI extreme
    const rsi = stock.rsi || 50;
    if (rsi > 75 || rsi < 25) score += 12;
    else if (rsi > 70 || rsi < 30) score += 5;

    // 7. Corporate action within 7 days
    if (stock.corporate_action_within_7d) score += 10;

    // 8. Bollinger squeeze (impending breakout)
    if (stock.bollinger_bandwidth && stock.bollinger_bandwidth < 3) score += 8;

    return Math.min(100, score);
}

function rankByAttention(stocks) {
    return stocks
        .map(s => ({ ...s, attention_score: calculateAttentionScore(s) }))
        .sort((a, b) => b.attention_score - a.attention_score);
}

function getTopN(stocks, n = 5) {
    const ranked = rankByAttention(stocks);
    return {
        top: ranked.slice(0, n),
        rest: ranked.slice(n),
        rest_summary: summarizeRest(ranked.slice(n))
    };
}

function summarizeRest(stocks) {
    if (stocks.length === 0) return null;
    const green = stocks.filter(s => (s.day_change_pct || 0) > 0.1).length;
    const red = stocks.filter(s => (s.day_change_pct || 0) < -0.1).length;
    const flat = stocks.length - green - red;
    
    const biggest = stocks.reduce((max, s) => 
        Math.abs(s.day_change_pct || 0) > Math.abs(max.day_change_pct || 0) ? s : max, stocks[0]);
    const worst = stocks.reduce((min, s) => 
        (s.day_change_pct || 0) < (min.day_change_pct || 0) ? s : min, stocks[0]);

    return {
        count: stocks.length,
        green, red, flat,
        biggest_mover: biggest ? `${biggest.symbol} ${biggest.day_change_pct > 0 ? '+' : ''}${biggest.day_change_pct?.toFixed(1)}%` : null,
        worst_mover: worst ? `${worst.symbol} ${worst.day_change_pct?.toFixed(1)}%` : null,
        text: `${stocks.length} others: ${green} 🟢 green, ${red} 🔴 red, ${flat} ⚪ flat`
    };
}

function getMovedStocks(stocks, thresholdPct = 1.0) {
    return stocks.filter(s => 
        Math.abs(s.day_change_pct || 0) > thresholdPct ||
        s.alert_triggered_today ||
        s.pattern_detected
    );
}

module.exports = { calculateAttentionScore, rankByAttention, getTopN, getMovedStocks, summarizeRest };

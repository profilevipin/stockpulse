/**
 * StockPulse v3.2 — Historical Pattern Matcher
 * Finds past instances with similar technical setup to current conditions.
 * Used in predictions: "Last 3 times RSI was 62 + volume 1.2x, price moved +3.2% in 5 sessions."
 *
 * NOTE: This is indicative analysis, not guaranteed. Similarity threshold is heuristic.
 */

function findSimilarPatterns(candles, currentTechnicals, targetPrice) {
    if (!candles || candles.length < 70) {
        return { matches: [], summary: { hit_rate: 0, avg_sessions: 0, sample_size: 0, reliability: 'insufficient_data' } };
    }

    const closes = candles.map(c => c[4]);
    const volumes = candles.map(c => c[5]);
    const currentPrice = closes[closes.length - 1];
    const targetPct = ((targetPrice - currentPrice) / currentPrice) * 100;
    const isUp = targetPct > 0;

    function sma(data, end, period) {
        if (end < period) return null;
        let sum = 0;
        for (let i = end - period; i < end; i++) sum += data[i];
        return sum / period;
    }

    function rsiAt(data, end, period = 14) {
        if (end < period + 1) return null;
        let gains = 0, losses = 0;
        for (let i = end - period; i < end; i++) {
            const diff = data[i] - data[i - 1];
            if (diff > 0) gains += diff; else losses += Math.abs(diff);
        }
        if (losses === 0) return 100;
        return 100 - (100 / (1 + gains / losses));
    }

    const currentRSI = currentTechnicals.rsi || 50;
    const currentVolRatio = currentTechnicals.volume?.ratio || 1;
    const SIMILARITY_THRESHOLD = 20;
    const LOOKFORWARD = 20;

    const matches = [];

    for (let i = 50; i < closes.length - LOOKFORWARD; i++) {
        const histRSI = rsiAt(closes, i);
        const histVolAvg = sma(volumes, i, 20);
        const histVol = volumes[i];
        const histVolRatio = histVolAvg ? histVol / histVolAvg : 1;

        if (!histRSI) continue;

        const rsiDiff = Math.abs(histRSI - currentRSI) * 0.5;
        const volDiff = Math.abs(histVolRatio - currentVolRatio) * 10;
        const similarity = rsiDiff + volDiff;

        if (similarity < SIMILARITY_THRESHOLD) {
            const priceAtMatch = closes[i];
            let maxUp = 0, maxDown = 0, targetHit = false, sessionsToHit = null;

            for (let j = 1; j <= LOOKFORWARD && (i + j) < closes.length; j++) {
                const futurePrice = closes[i + j];
                const movePct = ((futurePrice - priceAtMatch) / priceAtMatch) * 100;
                if (movePct > maxUp) maxUp = movePct;
                if (movePct < maxDown) maxDown = movePct;
                if (!targetHit) {
                    if (isUp && movePct >= Math.abs(targetPct)) { targetHit = true; sessionsToHit = j; }
                    else if (!isUp && movePct <= -Math.abs(targetPct)) { targetHit = true; sessionsToHit = j; }
                }
            }

            matches.push({
                date: candles[i][0], price_at_match: priceAtMatch,
                rsi: histRSI.toFixed(0), vol_ratio: histVolRatio.toFixed(1),
                similarity: similarity.toFixed(1),
                max_up_pct: maxUp.toFixed(1), max_down_pct: maxDown.toFixed(1),
                target_hit: targetHit, sessions_to_hit: sessionsToHit
            });
        }
    }

    matches.sort((a, b) => parseFloat(a.similarity) - parseFloat(b.similarity));
    const top = matches.slice(0, 5);
    const hitCount = top.filter(m => m.target_hit).length;
    const hitRate = top.length > 0 ? ((hitCount / top.length) * 100).toFixed(0) : 0;
    const avgSessions = top.filter(m => m.sessions_to_hit).reduce((s, m) => s + m.sessions_to_hit, 0) / (hitCount || 1);

    return {
        matches: top,
        summary: {
            total_found: matches.length, shown: top.length,
            hit_rate: parseFloat(hitRate), avg_sessions: Math.round(avgSessions),
            reliability: top.length >= 5 ? 'good' : top.length >= 3 ? 'moderate' : 'limited',
            interpretation: top.length >= 3
                ? `In ${top.length} similar setups, target hit ${hitRate}% of the time in ~${Math.round(avgSessions)} sessions.`
                : `Only ${top.length} similar setups found — interpret with caution.`
        }
    };
}

module.exports = { findSimilarPatterns };

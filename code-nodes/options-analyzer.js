/**
 * StockPulse v3.2 — Options Chain Analyzer
 * Analyzes NSE option chain data from nsefin service.
 * Calculates: PCR, Max Pain, Max OI strikes, expected range, avg IV.
 *
 * Expected input shape (from nsefin):
 * {
 *   records: {
 *     data: [
 *       { strikePrice: 22400, CE: { openInterest: 125000, impliedVolatility: 12.5 }, PE: { openInterest: 98000, impliedVolatility: 13.2 } }
 *     ],
 *     underlyingValue: 22450.5
 *   }
 * }
 */

function analyzeOptionChain(ocData, symbol) {
    if (!ocData || !ocData.records || !ocData.records.data) {
        return { symbol, error: 'No option chain data', available: false };
    }

    const data = ocData.records.data;
    const spotPrice = ocData.records.underlyingValue || 0;

    let totalCallOI = 0, totalPutOI = 0;
    let maxCallOI = 0, maxCallOIStrike = 0;
    let maxPutOI = 0, maxPutOIStrike = 0;
    let totalIV = 0, ivCount = 0;
    const strikes = [];

    for (const row of data) {
        const strike = row.strikePrice;
        const callOI = row.CE?.openInterest || 0;
        const putOI = row.PE?.openInterest || 0;
        const callIV = row.CE?.impliedVolatility || 0;
        const putIV = row.PE?.impliedVolatility || 0;
        const callChangeOI = row.CE?.changeinOpenInterest || 0;
        const putChangeOI = row.PE?.changeinOpenInterest || 0;

        totalCallOI += callOI;
        totalPutOI += putOI;

        if (callOI > maxCallOI) { maxCallOI = callOI; maxCallOIStrike = strike; }
        if (putOI > maxPutOI) { maxPutOI = putOI; maxPutOIStrike = strike; }

        if (callIV > 0) { totalIV += callIV; ivCount++; }
        if (putIV > 0) { totalIV += putIV; ivCount++; }

        strikes.push({ strike, callOI, putOI, callIV, putIV, callChangeOI, putChangeOI });
    }

    // PCR
    const pcr = totalCallOI > 0 ? parseFloat((totalPutOI / totalCallOI).toFixed(2)) : 0;
    let pcrSignal, pcrExplanation;
    if (pcr > 1.3) {
        pcrSignal = 'bullish';
        pcrExplanation = `PCR ${pcr} — Heavy put writing indicates strong support. Writers expect price to stay above current levels.`;
    } else if (pcr > 1.0) {
        pcrSignal = 'mildly_bullish';
        pcrExplanation = `PCR ${pcr} — Moderate put writing. Slight bullish bias.`;
    } else if (pcr > 0.8) {
        pcrSignal = 'neutral';
        pcrExplanation = `PCR ${pcr} — Balanced call and put writing. No clear directional bias.`;
    } else {
        pcrSignal = 'bearish';
        pcrExplanation = `PCR ${pcr} — Heavy call writing indicates resistance above. Bearish bias.`;
    }

    // Max Pain calculation
    let minPain = Infinity, maxPainStrike = 0;
    for (const s of strikes) {
        let pain = 0;
        for (const other of strikes) {
            if (other.strike < s.strike) pain += other.callOI * (s.strike - other.strike);
            if (other.strike > s.strike) pain += other.putOI * (other.strike - s.strike);
        }
        if (pain < minPain) { minPain = pain; maxPainStrike = s.strike; }
    }

    // Average IV
    const avgIV = ivCount > 0 ? parseFloat((totalIV / ivCount).toFixed(2)) : 0;

    // Top OI buildup (by change in OI)
    const topCallBuildup = strikes
        .filter(s => s.callChangeOI > 0)
        .sort((a, b) => b.callChangeOI - a.callChangeOI)
        .slice(0, 3);

    const topPutBuildup = strikes
        .filter(s => s.putChangeOI > 0)
        .sort((a, b) => b.putChangeOI - a.putChangeOI)
        .slice(0, 3);

    return {
        symbol,
        available: true,
        spot_price: spotPrice,
        pcr,
        pcr_signal: pcrSignal,
        pcr_explanation: pcrExplanation,
        max_pain: maxPainStrike,
        max_call_oi_strike: maxCallOIStrike,
        max_put_oi_strike: maxPutOIStrike,
        expected_range: { low: maxPutOIStrike, high: maxCallOIStrike },
        expected_range_text: `₹${maxPutOIStrike} — ₹${maxCallOIStrike}`,
        total_call_oi: totalCallOI,
        total_put_oi: totalPutOI,
        avg_iv: avgIV,
        top_call_buildup: topCallBuildup,
        top_put_buildup: topPutBuildup
    };
}

module.exports = { analyzeOptionChain };

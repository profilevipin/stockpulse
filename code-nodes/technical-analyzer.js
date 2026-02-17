/**
 * StockPulse v3.2 — Technical Analyzer
 * Complete TA engine: SMA, EMA, RSI, MACD, Bollinger, ATR, S/R, Volume, Momentum.
 * Input: array of candles [date, open, high, low, close, volume]
 * Output: full analysis object ready for Claude prompt.
 */

class TechnicalAnalyzer {
    constructor(candles) {
        this.dates = candles.map(c => c[0]);
        this.opens = candles.map(c => c[1]);
        this.highs = candles.map(c => c[2]);
        this.lows = candles.map(c => c[3]);
        this.closes = candles.map(c => c[4]);
        this.volumes = candles.map(c => c[5]);
        this.len = candles.length;
    }

    sma(data, period) {
        if (data.length < period) return null;
        return data.slice(-period).reduce((a, b) => a + b, 0) / period;
    }

    ema(data, period) {
        if (data.length < period) return null;
        const k = 2 / (period + 1);
        let e = data.slice(0, period).reduce((a, b) => a + b, 0) / period;
        for (let i = period; i < data.length; i++) e = data[i] * k + e * (1 - k);
        return e;
    }

    calcRSI(period = 14) {
        const data = this.closes;
        if (data.length < period + 1) return null;
        let avgGain = 0, avgLoss = 0;
        for (let i = 1; i <= period; i++) {
            const d = data[i] - data[i - 1];
            if (d > 0) avgGain += d; else avgLoss += Math.abs(d);
        }
        avgGain /= period; avgLoss /= period;
        for (let i = period + 1; i < data.length; i++) {
            const d = data[i] - data[i - 1];
            avgGain = (avgGain * (period - 1) + Math.max(d, 0)) / period;
            avgLoss = (avgLoss * (period - 1) + Math.max(-d, 0)) / period;
        }
        if (avgLoss === 0) return 100;
        return 100 - (100 / (1 + avgGain / avgLoss));
    }

    calcMACD() {
        const e12 = this.ema(this.closes, 12);
        const e26 = this.ema(this.closes, 26);
        if (!e12 || !e26) return { line: null, signal: null, histogram: null };
        const line = e12 - e26;
        // Build MACD values array for signal line
        const vals = [];
        const k12 = 2 / 13, k26 = 2 / 27;
        let em12 = this.closes.slice(0, 12).reduce((a, b) => a + b, 0) / 12;
        let em26 = this.closes.slice(0, 26).reduce((a, b) => a + b, 0) / 26;
        for (let i = 26; i < this.len; i++) {
            em12 = this.closes[i] * k12 + em12 * (1 - k12);
            em26 = this.closes[i] * k26 + em26 * (1 - k26);
            vals.push(em12 - em26);
        }
        const signal = vals.length >= 9 ? this.ema(vals, 9) : null;
        return { line, signal, histogram: signal ? line - signal : null };
    }

    calcBollinger(period = 20, mult = 2) {
        if (this.len < period) return null;
        const slice = this.closes.slice(-period);
        const mean = slice.reduce((a, b) => a + b, 0) / period;
        const std = Math.sqrt(slice.reduce((s, v) => s + Math.pow(v - mean, 2), 0) / period);
        const price = this.closes[this.len - 1];
        return {
            upper: mean + mult * std, middle: mean, lower: mean - mult * std,
            bandwidth: std > 0 ? (4 * mult * std / mean * 100) : 0,
            percentB: std > 0 ? (price - (mean - mult * std)) / (2 * mult * std) : 0.5
        };
    }

    calcATR(period = 14) {
        if (this.len < period + 1) return null;
        const trs = [];
        for (let i = 1; i < this.len; i++) {
            trs.push(Math.max(
                this.highs[i] - this.lows[i],
                Math.abs(this.highs[i] - this.closes[i - 1]),
                Math.abs(this.lows[i] - this.closes[i - 1])
            ));
        }
        let atr = trs.slice(0, period).reduce((a, b) => a + b, 0) / period;
        for (let i = period; i < trs.length; i++) atr = (atr * (period - 1) + trs[i]) / period;
        return atr;
    }

    calcSupportResistance() {
        const c = this.closes[this.len - 1], h = this.highs[this.len - 1], l = this.lows[this.len - 1];
        const pivot = (h + l + c) / 3;
        return {
            pivot, r1: 2 * pivot - l, r2: pivot + (h - l), r3: h + 2 * (pivot - l),
            s1: 2 * pivot - h, s2: pivot - (h - l), s3: l - 2 * (h - pivot),
            high20: Math.max(...this.highs.slice(-20)), low20: Math.min(...this.lows.slice(-20)),
            high52: this.len >= 252 ? Math.max(...this.highs.slice(-252)) : Math.max(...this.highs),
            low52: this.len >= 252 ? Math.min(...this.lows.slice(-252)) : Math.min(...this.lows)
        };
    }

    calcVolume() {
        const cur = this.volumes[this.len - 1];
        const avg5 = this.sma(this.volumes, 5);
        const avg20 = this.sma(this.volumes, 20);
        let obv = 0;
        for (let i = 1; i < this.len; i++) {
            if (this.closes[i] > this.closes[i - 1]) obv += this.volumes[i];
            else if (this.closes[i] < this.closes[i - 1]) obv -= this.volumes[i];
        }
        const obvPrev10 = (() => { let o = 0; for (let i = 1; i < Math.max(1, this.len - 10); i++) { if (this.closes[i] > this.closes[i-1]) o += this.volumes[i]; else if (this.closes[i] < this.closes[i-1]) o -= this.volumes[i]; } return o; })();
        return {
            current: cur, avg_5d: avg5, avg_20d: avg20,
            ratio: avg20 ? parseFloat((cur / avg20).toFixed(2)) : 1,
            obv_trend: obv > obvPrev10 ? 'rising' : 'falling',
            is_spike: avg20 ? cur > 2 * avg20 : false,
            is_dry: avg20 ? cur < 0.5 * avg20 : false
        };
    }

    calcTrend() {
        const price = this.closes[this.len - 1];
        const s20 = this.sma(this.closes, 20);
        const s50 = this.sma(this.closes, 50);
        const s200 = this.len >= 200 ? this.sma(this.closes, 200) : null;
        const rsi = this.calcRSI();
        if (price > (s50 || 0) && price > (s20 || 0) && (s20 || 0) > (s50 || 0))
            return rsi > 60 ? 'STRONG_BULLISH' : 'BULLISH';
        if (price < (s50 || Infinity) && price < (s20 || Infinity))
            return rsi < 40 ? 'STRONG_BEARISH' : 'BEARISH';
        return 'SIDEWAYS';
    }

    calcMomentum() {
        let score = 50;
        const rsi = this.calcRSI();
        const macd = this.calcMACD();
        const vol = this.calcVolume();
        const price = this.closes[this.len - 1];
        if (rsi) score += (rsi - 50) * 0.3;
        if (macd.histogram) score += macd.histogram > 0 ? 10 : -10;
        if (price > (this.sma(this.closes, 20) || 0)) score += 5;
        if (price > (this.sma(this.closes, 50) || 0)) score += 5;
        if (vol.obv_trend === 'rising') score += 5; else score -= 5;
        return Math.max(0, Math.min(100, Math.round(score)));
    }

    calcAvgDailyMove() {
        const moves = [];
        for (let i = Math.max(1, this.len - 20); i < this.len; i++) {
            moves.push(Math.abs(this.closes[i] - this.closes[i - 1]) / this.closes[i - 1] * 100);
        }
        return moves.length > 0 ? parseFloat((moves.reduce((a, b) => a + b, 0) / moves.length).toFixed(2)) : 0;
    }

    analyze() {
        return {
            last_close: this.closes[this.len - 1],
            last_date: this.dates[this.len - 1],
            candle_count: this.len,
            moving_averages: {
                sma5: this.sma(this.closes, 5), sma10: this.sma(this.closes, 10),
                sma20: this.sma(this.closes, 20), sma50: this.sma(this.closes, 50),
                sma200: this.len >= 200 ? this.sma(this.closes, 200) : null,
                ema9: this.ema(this.closes, 9), ema12: this.ema(this.closes, 12),
                ema21: this.ema(this.closes, 21), ema26: this.ema(this.closes, 26)
            },
            rsi: this.calcRSI(),
            macd: this.calcMACD(),
            bollinger: this.calcBollinger(),
            atr: this.calcATR(),
            support_resistance: this.calcSupportResistance(),
            volume: this.calcVolume(),
            trend: this.calcTrend(),
            momentum_score: this.calcMomentum(),
            avg_daily_move_pct: this.calcAvgDailyMove()
        };
    }
}

module.exports = { TechnicalAnalyzer };

"""
StockPulse NSE Data Service v3.2
Flask microservice for NSE market data via nsefin + yfinance
Runs on localhost:5000 inside Docker

Endpoints:
  GET  /health              → {"status": "ok"}
  GET  /fii-dii             → FII/DII activity data
  GET  /option-chain/<sym>  → Full option chain with PCR, max pain
  GET  /pre-market          → Pre-market F&O data
  GET  /corporate-actions   → Upcoming dividends, splits, bonuses
  GET  /most-active         → Top traded stocks by volume
  GET  /global-indices      → Via yfinance: NIFTY, DOW, S&P500, etc.
  GET  /stock-fundamentals/<sym> → PE, PB, market cap, sector
"""

from flask import Flask, jsonify
import logging
from datetime import datetime, timedelta

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# Initialize data sources
# ============================================
nse = None
try:
    from nsefin import NSE
    nse = NSE()
    logger.info("nsefin initialized successfully")
except Exception as e:
    logger.warning(f"nsefin not available: {e}. Some endpoints will use fallbacks.")

try:
    import yfinance as yf
    logger.info("yfinance initialized successfully")
except Exception as e:
    logger.warning(f"yfinance not available: {e}")
    yf = None


# ============================================
# Health Check
# ============================================
@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "nsefin_available": nse is not None,
        "yfinance_available": yf is not None,
        "timestamp": datetime.now().isoformat()
    })


# ============================================
# FII/DII Activity
# Response sample:
# {
#   "fii": {"buy": 12500.5, "sell": 11200.3, "net": 1300.2},
#   "dii": {"buy": 9800.1, "sell": 10500.7, "net": -700.6},
#   "date": "2026-02-16",
#   "signal": "FII net buyers, DII net sellers — mildly bullish"
# }
# ============================================
@app.route('/fii-dii')
def fii_dii():
    try:
        if nse:
            data = nse.get_fii_dii_activity()
            if data is not None:
                result = {
                    "raw": data.to_dict('records') if hasattr(data, 'to_dict') else data,
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "source": "nsefin"
                }
                return jsonify(result)

        return jsonify({
            "error": "NSE data unavailable",
            "fallback": "Use Claude web_search for FII/DII data",
            "date": datetime.now().strftime('%Y-%m-%d')
        }), 503
    except Exception as e:
        logger.error(f"FII/DII error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# Option Chain
# Response sample:
# {
#   "symbol": "NIFTY",
#   "spot_price": 22450.5,
#   "expiry_date": "2026-02-26",
#   "records": {
#     "data": [
#       {
#         "strikePrice": 22400,
#         "CE": {"openInterest": 125000, "changeinOpenInterest": 5000, "impliedVolatility": 12.5, "lastPrice": 120.5},
#         "PE": {"openInterest": 98000, "changeinOpenInterest": -3000, "impliedVolatility": 13.2, "lastPrice": 85.3}
#       }
#     ],
#     "underlyingValue": 22450.5
#   }
# }
# ============================================
@app.route('/option-chain/<symbol>')
def option_chain(symbol):
    try:
        symbol = symbol.upper().strip()
        if nse:
            data = nse.get_option_chain(symbol)
            if data is not None:
                return jsonify({
                    "symbol": symbol,
                    "records": data if isinstance(data, dict) else {"data": data},
                    "source": "nsefin",
                    "timestamp": datetime.now().isoformat()
                })

        return jsonify({"error": f"Option chain unavailable for {symbol}"}), 503
    except Exception as e:
        logger.error(f"Option chain error for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# Pre-Market Data
# Response sample:
# {
#   "data": [
#     {"symbol": "RELIANCE", "prevClose": 2850.0, "iep": 2870.0, "change": 20.0, "pChange": 0.7}
#   ]
# }
# ============================================
@app.route('/pre-market')
def pre_market():
    try:
        if nse:
            data = nse.get_premarket_data()
            if data is not None:
                return jsonify({
                    "data": data.to_dict('records') if hasattr(data, 'to_dict') else data,
                    "source": "nsefin",
                    "timestamp": datetime.now().isoformat()
                })

        return jsonify({"error": "Pre-market data unavailable"}), 503
    except Exception as e:
        logger.error(f"Pre-market error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# Corporate Actions
# Response sample:
# {
#   "data": [
#     {"symbol": "INFY", "series": "EQ", "subject": "Dividend - Rs 18 Per Share", "exDate": "2026-02-20"}
#   ]
# }
# ============================================
@app.route('/corporate-actions')
def corporate_actions():
    try:
        if nse:
            from_date = datetime.now()
            to_date = from_date + timedelta(days=14)
            data = nse.get_corporate_actions(
                from_date=from_date.strftime('%d-%m-%Y'),
                to_date=to_date.strftime('%d-%m-%Y')
            )
            if data is not None:
                return jsonify({
                    "data": data.to_dict('records') if hasattr(data, 'to_dict') else data,
                    "from": from_date.strftime('%Y-%m-%d'),
                    "to": to_date.strftime('%Y-%m-%d'),
                    "source": "nsefin"
                })

        return jsonify({"error": "Corporate actions unavailable"}), 503
    except Exception as e:
        logger.error(f"Corporate actions error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# Most Active Stocks
# Response sample:
# {
#   "data": [
#     {"symbol": "RELIANCE", "volume": 12500000, "value": 35600.5, "pChange": 1.2}
#   ]
# }
# ============================================
@app.route('/most-active')
def most_active():
    try:
        if nse:
            data = nse.get_most_active()
            if data is not None:
                return jsonify({
                    "data": data.to_dict('records') if hasattr(data, 'to_dict') else data,
                    "source": "nsefin",
                    "timestamp": datetime.now().isoformat()
                })

        return jsonify({"error": "Most active data unavailable"}), 503
    except Exception as e:
        logger.error(f"Most active error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# Global Indices (via yfinance)
# Response sample:
# {
#   "indices": {
#     "NIFTY_50": {"price": 22450.5, "change_pct": 0.8},
#     "SENSEX": {"price": 73800.2, "change_pct": 0.65},
#     "DOW_JONES": {"price": 42500.1, "change_pct": -0.3},
#     "SP500": {"price": 5850.3, "change_pct": -0.2},
#     "NASDAQ": {"price": 18900.7, "change_pct": -0.5},
#     "NIKKEI": {"price": 38500.0, "change_pct": 0.4},
#     "HANG_SENG": {"price": 20100.5, "change_pct": -0.8},
#     "CRUDE_BRENT": {"price": 78.5, "change_pct": 1.2},
#     "GOLD": {"price": 2350.0, "change_pct": 0.3}
#   }
# }
# ============================================
@app.route('/global-indices')
def global_indices():
    try:
        if yf is None:
            return jsonify({"error": "yfinance not available"}), 503

        tickers = {
            "NIFTY_50": "^NSEI",
            "SENSEX": "^BSESN",
            "DOW_JONES": "^DJI",
            "SP500": "^GSPC",
            "NASDAQ": "^IXIC",
            "NIKKEI": "^N225",
            "HANG_SENG": "^HSI",
            "CRUDE_BRENT": "BZ=F",
            "GOLD": "GC=F",
            "USD_INR": "INR=X"
        }

        indices = {}
        for name, symbol in tickers.items():
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                price = getattr(info, 'last_price', None) or getattr(info, 'previous_close', 0)
                prev_close = getattr(info, 'previous_close', price)
                change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
                indices[name] = {
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2)
                }
            except Exception as e:
                logger.warning(f"Failed to fetch {name}: {e}")
                indices[name] = {"price": None, "error": str(e)}

        return jsonify({
            "indices": indices,
            "source": "yfinance",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Global indices error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# Stock Fundamentals
# Response sample:
# {
#   "symbol": "RELIANCE",
#   "pe_ratio": 28.5,
#   "pb_ratio": 2.8,
#   "market_cap": 1850000000000,
#   "sector": "Energy",
#   "industry": "Oil & Gas Refining & Marketing",
#   "52w_high": 3025.0,
#   "52w_low": 2220.0,
#   "analyst_target": 2950.0
# }
# ============================================
@app.route('/stock-fundamentals/<symbol>')
def stock_fundamentals(symbol):
    try:
        symbol = symbol.upper().strip()
        if yf is None:
            return jsonify({"error": "yfinance not available"}), 503

        # yfinance uses .NS suffix for NSE stocks
        yf_symbol = f"{symbol}.NS"
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        return jsonify({
            "symbol": symbol,
            "company_name": info.get("longName", ""),
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "market_cap": info.get("marketCap"),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "analyst_target": info.get("targetMeanPrice"),
            "dividend_yield": info.get("dividendYield"),
            "source": "yfinance",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Fundamentals error for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

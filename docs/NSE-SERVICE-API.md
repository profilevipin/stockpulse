# NSE Data Service API Documentation

Base URL: `http://localhost:5000` (or `http://nse-data-service:5000` from Docker network)

## Endpoints

### GET /health
```json
{"status": "ok", "nsefin_available": true, "yfinance_available": true, "timestamp": "2026-02-17T07:00:00"}
```

### GET /fii-dii
FII/DII cash market activity from previous trading day.
```json
{
  "raw": [
    {"category": "FII/FPI", "buy_value": 12500.5, "sell_value": 11200.3, "net_value": 1300.2},
    {"category": "DII", "buy_value": 9800.1, "sell_value": 10500.7, "net_value": -700.6}
  ],
  "date": "2026-02-16",
  "source": "nsefin"
}
```

### GET /option-chain/{symbol}
Full option chain with OI, IV, Greeks. Symbol: NIFTY, BANKNIFTY, or any F&O stock.
```json
{
  "symbol": "NIFTY",
  "records": {
    "data": [
      {
        "strikePrice": 22400,
        "CE": {"openInterest": 125000, "changeinOpenInterest": 5000, "impliedVolatility": 12.5, "lastPrice": 120.5},
        "PE": {"openInterest": 98000, "changeinOpenInterest": -3000, "impliedVolatility": 13.2, "lastPrice": 85.3}
      }
    ],
    "underlyingValue": 22450.5
  },
  "source": "nsefin"
}
```

### GET /pre-market
Pre-market data for F&O stocks.
```json
{
  "data": [
    {"symbol": "RELIANCE", "prevClose": 2850.0, "iep": 2870.0, "change": 20.0, "pChange": 0.7}
  ],
  "source": "nsefin"
}
```

### GET /corporate-actions
Upcoming 14 days of corporate actions.
```json
{
  "data": [
    {"symbol": "INFY", "series": "EQ", "subject": "Dividend - Rs 18 Per Share", "exDate": "2026-02-20"}
  ],
  "from": "2026-02-17",
  "to": "2026-03-03"
}
```

### GET /most-active
Most traded stocks by volume.
```json
{
  "data": [
    {"symbol": "RELIANCE", "volume": 12500000, "value": 35600.5, "pChange": 1.2}
  ]
}
```

### GET /global-indices
Global market indices via yfinance.
```json
{
  "indices": {
    "NIFTY_50": {"price": 22450.5, "change_pct": 0.8},
    "SENSEX": {"price": 73800.2, "change_pct": 0.65},
    "DOW_JONES": {"price": 42500.1, "change_pct": -0.3},
    "SP500": {"price": 5850.3, "change_pct": -0.2},
    "NASDAQ": {"price": 18900.7, "change_pct": -0.5},
    "CRUDE_BRENT": {"price": 78.5, "change_pct": 1.2},
    "GOLD": {"price": 2350.0, "change_pct": 0.3},
    "USD_INR": {"price": 83.2, "change_pct": -0.1}
  }
}
```

### GET /stock-fundamentals/{symbol}
Stock fundamentals via yfinance.
```json
{
  "symbol": "RELIANCE",
  "company_name": "Reliance Industries Limited",
  "pe_ratio": 28.5,
  "pb_ratio": 2.8,
  "market_cap": 1850000000000,
  "sector": "Energy",
  "52w_high": 3025.0,
  "52w_low": 2220.0,
  "analyst_target": 2950.0
}
```

## Error Responses

All endpoints return `503` if data source is unavailable:
```json
{"error": "NSE data unavailable", "fallback": "Use Claude web_search for FII/DII data"}
```

And `500` for server errors:
```json
{"error": "Connection timeout to NSE"}
```

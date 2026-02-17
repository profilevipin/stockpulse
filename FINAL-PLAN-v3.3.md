# StockPulse v3.3 — COMPLETE BUILD PLAN
## Single Kite Account · Smart UX · Portfolio Intelligence · Production-Ready
## Last Updated: February 2026

---

# TABLE OF CONTENTS

1. [App Overview & Features](#part-1)
2. [Architecture](#part-2)
3. [What Are n8n Workflow JSONs?](#part-3)
4. [The 13 Workflows Explained](#part-4)
5. [Smart Display System (20-30 Stocks)](#part-5)
6. [Smart Alert Suggestions](#part-6)
7. [Portfolio Intelligence & Risk](#part-7)
8. [Conversation Memory](#part-8)
9. [AI Features & Intelligence](#part-9)
10. [Single Kite Account + CSV Upload](#part-10)
11. [User Onboarding Flow](#part-11)
12. [Database Schema (v3.3)](#part-12)
13. [Security Architecture](#part-13)
14. [API Stack & Kite Costs](#part-14)
15. [Graceful Degradation](#part-15)
16. [Backup & Export](#part-16)
17. [Multi-Agent Cursor Build](#part-17)
18. [File Manifest](#part-18)
19. [Costs & Timeline](#part-19)
20. [Changelog v3.2 → v3.3](#part-20)

---

# PART 1: APP OVERVIEW & FEATURES

## What Is StockPulse?

A personal AI stock assistant in Telegram for Indian markets (NSE/BSE). Monitors 20-30 stocks in real-time, sends AI briefings, detects patterns, predicts targets, tracks accuracy — all through natural conversation.

## Who Is It For?

Two users (you and a friend) who trade/invest in Indian stocks via Zerodha. One has Kite Connect; the other enters trades manually or via CSV.

## Complete Feature List

### Trading & Portfolio
- 📝 Natural language trading: "buy 10 reliance at 2850"
- 📊 Real-time portfolio with live P&L (tiered display for 20-30 stocks)
- 🔔 Smart price alerts with AI-suggested levels based on technicals
- 📎 CSV/XLS bulk import for trades
- 🔄 Kite auto-sync for User 1
- 📤 Data export (CSV of trades, predictions, snapshots)

### AI Intelligence
- 🌅 Morning Briefing (7 sources, top 5 by "attention score", expandable)
- ⏸️ Midday Pulse (12:30 PM — 3-line portfolio + market check)
- 📉 EOD Summary (only stocks that moved, not all 30)
- 📆 Weekly Review with portfolio intelligence
- 📊 Monthly Scorecard (prediction accuracy, portfolio performance, bot usefulness)
- 🔮 3-Scenario Predictions with historical pattern matching
- 📰 News Sentiment scoring per stock
- 📈 7 Pattern types detected with "why" explanation
- 🧠 Conversation Memory (last 10 messages for context)
- ❓ Natural Q&A ("why did Reliance drop?")
- ⚠️ Risk Snapshot (concentration, sector tilt, loss flags)
- 💡 Portfolio Intelligence (underperformers, FII flow alignment, rebalancing observations)
- 🎯 Prediction Calibration (accuracy fed back into prompts)

### UX & Reliability
- 👋 Guided onboarding for new users (inline buttons walk through setup)
- 📱 Inline buttons everywhere (no typing needed for actions)
- 📏 Dynamic briefing length (short when boring, long when eventful)
- 🔄 Graceful Kite-down messaging (fallback to last known prices)
- 💾 Daily PostgreSQL backups
- 🚫 Idempotent trades (no duplicates from double-taps)
- 🧹 Auto-cleanup (staging 7d, context 30d, audit 90d)

### Technical Indicators
RSI, MACD, Bollinger Bands, SMA (5/10/20/50/200), EMA (9/12/21/26), ATR, Pivot Points, Volume Analysis (OBV, ratio, spikes), Momentum Score (0-100), Options Chain (PCR, Max Pain, OI), Support/Resistance levels

---

# PART 2: ARCHITECTURE

```
┌─────────────────────────────────────────────────────┐
│                   TELEGRAM BOT                       │
│  Users ←→ Messages, Buttons, Files, Alerts           │
└─────────────────────┬───────────────────────────────┘
                      │ Webhook (HTTPS + secret token)
                      ▼
┌─────────────────────────────────────────────────────┐
│                     n8n                              │
│  13 Workflows · 95+ Nodes · Cron + Webhooks          │
│  Orchestrates all data flow and AI calls             │
└───┬──────────┬──────────┬──────────┬────────────────┘
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐
│Postgres│ │Kite API│ │Claude  │ │NSE Data Svc  │
│        │ │(free   │ │        │ │(Python/Flask) │
│Users   │ │within  │ │NLP     │ │              │
│Trades  │ │₹2000/mo│ │Briefing│ │FII/DII       │
│Alerts  │ │plan)   │ │Predict │ │Options       │
│Context │ │        │ │Q&A     │ │Pre-Market    │
│Predict │ │Quotes  │ │Sentimnt│ │Corp Actions  │
│Snapshot│ │OHLC    │ │        │ │Fundamentals  │
└────────┘ └────────┘ └────────┘ └──────────────┘
```

---

# PART 3: WHAT ARE N8N WORKFLOW JSONS?

n8n stores each workflow as a JSON file. Instead of creating 95 nodes by hand, you import the JSON:

```
n8n UI → Settings (⚙️) → Import from File → Select JSON → Done
```

**Before importing:** Create credentials in n8n first (Telegram, Postgres, Claude, Kite, Finnhub), then find-replace the placeholder IDs in each JSON:
```
Replace "POSTGRES_CREDENTIAL_ID" → your actual credential ID from n8n
Replace "TELEGRAM_CREDENTIAL_ID" → your actual credential ID  
Replace "CLAUDE_CREDENTIAL_ID"   → your actual credential ID
Replace "KITE_CREDENTIAL_ID"     → your actual credential ID
Replace "FINNHUB_CREDENTIAL_ID"  → your actual credential ID
```

n8n shows credential IDs in Settings → Credentials → click credential → ID is in the URL.

---

# PART 4: THE 13 WORKFLOWS

| # | File | What It Does | Schedule |
|---|------|-------------|----------|
| WF1 | `wf1-message-handler.json` | **The Brain.** Parses intent (with conversation memory), routes commands, handles CSV uploads, inline buttons, Q&A, onboarding flow. Smart alert suggestions after BUY. | Every message |
| WF2 | `wf2-alert-checker.json` | **The Watchdog.** Batch quotes ALL symbols, checks alerts with cooldown, sends notifications with "why" + inline buttons. | Every 30s (market hours) |
| WF3 | `wf3-pattern-detector.json` | **The Scout.** 7 pattern types with explanation layer. Deduplicates (1 alert per pattern per day). | Every 5min (market hours) |
| WF4a | `wf4a-global-data.json` | Global cues via Claude web_search + Finnhub. | 7:00 AM |
| WF4b | `wf4b-flow-data.json` | FII/DII + most active + pre-market from nsefin. | 7:30 AM |
| WF4c | `wf4c-technical-data.json` | 90-day OHLC → full TA for all held stocks. Computes attention_score. | 8:00 AM |
| WF4d | `wf4d-options-news.json` | Options chains + NewsAPI + Claude sentiment. | 8:15 AM |
| WF4 | `wf4-morning-briefing.json` | **The Analyst.** Data completeness check → top 5 by attention score → Claude briefing (dynamic length) → per-user send with [Full Briefing] button. | 8:30 AM |
| WF4e | `wf4e-midday-pulse.json` | **NEW.** 3-line midday update: NIFTY + portfolio P&L + alert proximity. No Claude needed — pure template. | 12:30 PM |
| WF5 | `wf5-eod-summary.json` | Only stocks that moved >1% or triggered alerts. Snapshot + cleanup jobs. | 3:45 PM |
| WF6 | `wf6-token-manager.json` | Tests Kite token, sends login URL if expired. | 8:45 AM |
| WF7 | `wf7-weekly-review.json` | Weekly P&L + portfolio intelligence (concentration, sector, underperformers, FII alignment). | Sunday 10 AM |
| WF8 | `wf8-prediction-tracker.json` | Checks predictions vs actual, updates accuracy, calibration feedback. | 3:46 PM |

**Monthly:** WF7 includes a monthly scorecard on the 1st of each month (conditional check).

---

# PART 5: SMART DISPLAY SYSTEM (20-30 STOCKS)

## The Problem
30 stocks × 5 lines = 150 lines. Nobody reads that on a phone.

## The Solution: Attention Score + Tiered Display

### Attention Score (computed in WF4c)
```javascript
function attentionScore(stock) {
    let score = 0;
    
    // Alert proximity (highest priority)
    if (stock.alert_dist_pct < 2) score += 40;
    else if (stock.alert_dist_pct < 5) score += 20;
    
    // Big daily move
    if (Math.abs(stock.day_change_pct) > 3) score += 25;
    else if (Math.abs(stock.day_change_pct) > 1.5) score += 15;
    
    // News impact
    if (stock.sentiment_score > 40 || stock.sentiment_score < -40) score += 15;
    
    // Technical signal today
    if (stock.pattern_detected) score += 15;
    
    // Unusual volume
    if (stock.volume_ratio > 2) score += 15;
    else if (stock.volume_ratio > 1.5) score += 10;
    
    // Upcoming corporate action
    if (stock.corporate_action_within_7d) score += 10;
    
    // RSI extreme
    if (stock.rsi > 75 || stock.rsi < 25) score += 10;
    
    return score;
}
```

### How Each Feature Uses It

**Morning Briefing:**
```
🌅 Morning Briefing — Feb 17, 2026

🌍 NIFTY at 22,480 | FII: +₹1,200Cr | PCR: 1.15 (mildly bullish)

📊 TOP 5 STOCKS TO WATCH:

1. 🔴 RELIANCE (Attention: 75)
   ₹2,948 — 0.1% from your ₹2,950 target!
   RSI 72 (overbought) + Volume 1.4x
   Action: Consider partial profit booking at resistance

2. ⚡ TATAMOTORS (Attention: 55)
   Gap down -2.8% on weak auto sales data
   Approaching SMA200 support at ₹780
   Action: Watch ₹780 — bounce or break

[...3 more detailed stocks...]

📋 25 others: 14 🟢 green, 8 🔴 red, 3 ⚪ flat
Biggest: HDFCBANK +1.8% | Worst: WIPRO -1.2%

[📊 Full Briefing (all 30)] [🔮 Predict Top Stock]
```

**Portfolio Command:**
```
📊 Your Portfolio (30 stocks)

TOP 10 by value:
🟢 RELIANCE    10 × ₹2,850 → ₹2,948  +₹980 (+3.4%)
🔴 INFY        25 × ₹1,420 → ₹1,385  -₹875 (-2.5%)
🟢 HDFCBANK    20 × ₹1,650 → ₹1,698  +₹960 (+2.9%)
[...7 more...]

+20 more: invested ₹3.2L, current ₹3.4L (+6.2%)

━━━━━━━━━━━━━━━━━━
📈 Total P&L: +₹42,300 (+5.8%)
💰 Invested: ₹7.3L | Current: ₹7.72L

[Show All 30] [📈 Top Gainers] [📉 Top Losers]
```

**Midday Pulse (NEW — WF4e):**
```
⏸️ Midday Pulse — 12:30 PM
NIFTY: 22,510 (+0.4%) | Your portfolio: +₹3,200 (+0.44%)
🔔 RELIANCE 0.3% from target | TATAMOTORS at support ₹782
```

No Claude needed. Just Kite quotes + template. Costs zero AI tokens.

**EOD Summary (stocks that moved only):**
```
🔔 End of Day — Feb 17

📊 Stocks that moved today (6 of 30):
🟢 RELIANCE  +2.1%  ₹2,910 → ₹2,972  (Alert: 0.7% from target!)
🔴 TATAMOTORS -3.2% ₹808 → ₹782     (Hit SMA200 support)
🟢 SBIN      +1.8%  ₹620 → ₹631     (FII buying in banks)
🔴 WIPRO     -1.5%  ₹445 → ₹438     (IT sector outflows)
🟢 ITC       +1.2%  ₹472 → ₹478     (Volume spike 2.1x)
📈 BAJFINANCE +0.9% ₹7,250 → ₹7,315 (MACD bullish cross)

24 others: no significant movement

📈 Day P&L: +₹4,200 (+0.58%)
Alerts triggered: 0 | Approaching: 2 | Patterns: 3
```

---

# PART 6: SMART ALERT SUGGESTIONS

## After Every Trade

When a user logs a BUY, the bot suggests alert levels based on computed technicals:

```
User: "bought 15 HDFCBANK at 1650"

Bot: ✅ BUY Logged: 15 HDFCBANK @ ₹1,650 (Total: ₹24,750)

  📊 Current: ₹1,662 (+0.7%) | RSI: 54 | Trend: Bullish

  Suggested alerts based on technicals:

  🎯 Profit target: ₹1,720 (R1 pivot resistance, +4.2%)
  🛡️ Stop loss: ₹1,600 (S1 pivot support, -3.0%)

  [✅ Set Both] [🎯 Profit Only] [🛡️ Stop Only] [⚙️ Custom] [Skip]
```

### How Suggestions Are Computed

```javascript
function suggestAlertLevels(symbol, buyPrice, technicals) {
    const suggestions = {};
    
    // Profit target: nearest resistance above buy price
    const resistanceLevels = [
        technicals.support_resistance.r1,
        technicals.support_resistance.r2,
        technicals.support_resistance.high20,
        technicals.bollinger?.upper
    ].filter(r => r && r > buyPrice).sort((a, b) => a - b);
    
    suggestions.profit_target = resistanceLevels[0] || buyPrice * 1.05; // fallback +5%
    suggestions.profit_target_reason = resistanceLevels[0] 
        ? 'Next resistance level' : 'Default +5% target';
    
    // Stop loss: nearest support below buy price
    const supportLevels = [
        technicals.support_resistance.s1,
        technicals.support_resistance.s2,
        technicals.support_resistance.low20,
        technicals.bollinger?.lower,
        technicals.moving_averages.sma50
    ].filter(s => s && s < buyPrice).sort((a, b) => b - a);
    
    suggestions.stop_loss = supportLevels[0] || buyPrice * 0.95; // fallback -5%
    suggestions.stop_loss_reason = supportLevels[0]
        ? 'Nearest support level' : 'Default -5% stop';
    
    // Risk/reward ratio
    const reward = suggestions.profit_target - buyPrice;
    const risk = buyPrice - suggestions.stop_loss;
    suggestions.risk_reward = (reward / risk).toFixed(1);
    
    return suggestions;
}
```

### Alert After Trigger

When an alert triggers, the response guides the next action:

```
📈 HDFCBANK hit ₹1,722!
Above your ₹1,720 profit target
P&L: +₹1,080 (+4.4%) on 15 shares

Why: Broke R1 pivot resistance on 1.3x volume. RSI 64 — still has room.
Next resistance: ₹1,780 (R2 pivot, +3.4% from here)

[💰 Log Sale (all 15)] [💰 Sell Half (7)] [🔔 Raise to ₹1,780] [📊 Full Analysis]
```

---

# PART 7: PORTFOLIO INTELLIGENCE & RISK

## In Weekly Review (WF7)

```
🧠 Portfolio Intelligence — Week of Feb 10-14

⚠️ CONCENTRATION RISK
• RELIANCE is 38% of your ₹7.7L portfolio
• Top 3 stocks = 65% of portfolio
→ A 5% drop in RELIANCE = ₹1,470 loss (2% portfolio hit)

📊 SECTOR EXPOSURE
  Energy:     38% (RELIANCE, ONGC)
  Financials: 28% (HDFCBANK, SBIN, KOTAKBANK, BAJFINANCE)
  IT:         18% (INFY, TCS, WIPRO)
  Auto:        8% (TATAMOTORS, MARUTI)
  Others:      8%
→ Heavy energy tilt. Crude oil price is key risk factor.

📉 UNDERPERFORMERS (30-day)
  WIPRO: -8.2% (RSI 32, oversold)
  → Historically bounced from RSI <35 zone 4/5 times within 5 sessions
  TATAMOTORS: -5.1% (at SMA200 support ₹780)
  → Critical level. Break below = trend reversal signal.

📈 OUTPERFORMERS (30-day)
  RELIANCE: +12.3% (RSI 71 — approaching overbought)
  → Consider booking 25-50% profits near ₹2,950-3,000 resistance zone

💰 FII/DII ALIGNMENT
  FII: Net buyers in Financials (+₹2,400Cr this week) ✅ aligns with your holdings
  FII: Net sellers in IT (-₹800Cr) ⚠️ headwind for INFY, TCS, WIPRO
  DII: Buying IT on dips — provides some support

🔮 PREDICTION SCORECARD
  This week: 3 predictions made, 2 hit (67%)
  All time: 18 made, 11 hit (61%), stated avg confidence was 65%
  → Calibration: Slightly overconfident. Consider 55-60% for "likely" calls.
```

**Important:** This is observations and data, NOT financial advice. The prompt explicitly tells Claude:
```
"Present factual observations about portfolio composition, sector exposure, 
and technical levels. Never recommend specific buy/sell actions. 
Use phrases like 'consider', 'watch for', 'historically X happened'. 
End with: These are technical observations only. Not financial advice."
```

---

# PART 8: CONVERSATION MEMORY

Rolling window of **last 10 messages** per user. Before every Claude call in WF1, fetch recent context:

```sql
SELECT message, role, parsed_intent, bot_response_summary 
FROM conversation_context 
WHERE user_id = $1 
ORDER BY created_at DESC LIMIT 10
```

Enables:
- "What about INFY?" → inherits context (prediction, analysis, etc.)
- "Compare both" → references recent RELIANCE + INFY discussion
- "What did I ask about Reliance?" → direct recall
- "Same for TCS" → inherits command type from previous message

Bot responses stored as compressed summaries (max 500 chars) to avoid token bloat.

Cleanup: Messages older than 30 days deleted by WF5.

---

# PART 9: AI FEATURES & INTELLIGENCE

### 1. Intent Parser (with memory context)
Every message → Claude with last 10 messages → structured intent JSON.

### 2. Morning Briefing (7 sources, dynamic length)
Prompt includes: *"If the market setup is unremarkable, keep it under 150 words. If there are significant developments, expand to 500 words. Match length to significance."*

Data completeness check: If any source failed, Claude is told *"Global cues data was unavailable today"* instead of receiving null.

### 3. 3-Scenario Predictions
Single Claude call with rich pre-computed context (technicals + options + sentiment + historical matches). No 2-call chain needed — the analysis is done by JavaScript, Claude only synthesizes.

### 4. Explanation Layer
Every alert and pattern includes "why":
```
Why: RSI 74 (>70) + Price at upper Bollinger (₹2,948) + Volume 1.3x above average
→ Historically, this combination led to 2-3% pullback within 5 sessions (4/6 times)
```

### 5. Natural Q&A
Unknown intents → Claude with user's holdings + today's data + conversation memory.

### 6. Prediction Calibration
After 30+ predictions: "Your 70% UP predictions hit 55% of the time" fed into future prompts.

### 7. Smart Alert Suggestions
After every BUY: technical-level-based suggestions for profit target and stop loss.

### 8. Portfolio Intelligence
Weekly: concentration, sector tilt, underperformers, FII alignment. Observations only, not advice.

---

# PART 10: SINGLE KITE ACCOUNT + CSV UPLOAD

**User 1:** Kite Connect (₹2,000/mo). Auto-sync + live prices for everyone.
**User 2:** Manual entry + CSV upload. Same live prices from User 1's Kite.

All symbols across both users fetched in a single Kite batch call:
```
GET /quote?i=NSE:RELIANCE&i=NSE:INFY&i=NSE:TCS&... (up to 30+ symbols)
```

### Kite API Cost: ₹2,000/month FLAT (unlimited calls)
- 30-second polling = 750 calls/day = 0.3% of rate limit
- Zero per-call charges
- Batch quotes = 1 call for all symbols

CSV format:
```csv
Symbol,Type,Quantity,Price,Date
RELIANCE,BUY,10,2850,2026-02-15
```

---

# PART 11: USER ONBOARDING FLOW

When a new authorized user sends their first message:

```
👋 Welcome to StockPulse, [Name]!

I'm your personal stock market assistant. Let me help you set up.

How would you like to add your first trades?

[📝 Type a trade] [📎 Upload CSV] [⏭️ Just explore]
```

If they tap **Type a trade:**
```
Great! Just tell me naturally:
"bought 10 reliance at 2850"
"buy 25 INFY at 1420"

Try it now! 👇
```

After first trade:
```
✅ Got it! 10 RELIANCE @ ₹2,850

Want me to watch this stock for you?
🎯 Profit target: ₹2,950 (resistance) 
🛡️ Stop loss: ₹2,780 (support)

[✅ Set Both Alerts] [⏭️ Add More Trades First]
```

After 3+ trades:
```
📊 Nice! You have 3 stocks in your portfolio.

I'll start sending you:
• 🌅 Morning briefing at 8:30 AM
• ⏸️ Midday pulse at 12:30 PM  
• 🔔 EOD summary at 3:45 PM
• 🔔 Real-time alerts when prices hit your targets

Type "help" anytime to see all commands.
Ready to go! 🚀
```

Tracked via `users.settings.onboarding_complete = true`.

---

# PART 12: DATABASE SCHEMA (v3.3)

## Changes from v3.2
- Added `attention_score` concept (computed, not stored — calculated per query)
- Added `onboarding_complete` in settings JSONB
- Added `bot_response_summary` to conversation_context (already in v3.2)
- All other tables unchanged from v3.2

Schema is in `schema.sql` — see that file for full DDL.

Key constraints:
- `UNIQUE(user_id, telegram_message_id)` on trades — idempotency
- `UNIQUE(user_id, symbol, pattern_type, alert_date)` on pattern_alerts_log — dedup
- `CHECK` constraints on symbol length (≤20), price (0-10M), quantity (1-999999), message (≤2000), notes (≤500)
- Cleanup function: `SELECT cleanup_old_data();` — called by WF5

---

# PART 13: SECURITY

| Threat | Mitigation |
|--------|-----------|
| Unauthorized access | Whitelist telegram_user_ids; auth check on every message |
| API key theft | AES-256-GCM encryption at rest |
| Webhook impersonation | **Telegram secret_token validation** (NEW) |
| Bot token compromise | Token in .env only; .env in .gitignore |
| SQL injection | Parameterized queries ($1, $2 bindings) |
| Duplicate trades | UNIQUE constraint on (user_id, telegram_message_id) |
| Cross-user data leak | Every query includes user_id filter |
| Input abuse | Length limits on all text fields |
| Rate limit abuse | 30 msg/hour per user; 30-min alert cooldown |
| Cost runaway | **Claude API spend limit: $20/month on console.anthropic.com** (NEW) |
| Data loss | **Daily PostgreSQL backup at 4 AM** (NEW) |
| n8n infinite loops | Max 3 retries per workflow execution |

### Webhook Secret Token
```
# When setting Telegram webhook, include secret:
https://api.telegram.org/bot{TOKEN}/setWebhook?
  url=https://domain.com/webhook/stockpulse&
  secret_token=RANDOM_SECRET_STRING

# n8n Telegram Trigger validates X-Telegram-Bot-Api-Secret-Token header
```

### Secrets in Workflow JSONs
Workflow JSONs contain **credential IDs only**, never actual secrets. n8n stores credentials in its own encrypted database. No secrets are committed to files.

---

# PART 14: API STACK & KITE COSTS

### Kite Connect — ₹2,000/month FLAT
| Metric | Value |
|--------|-------|
| Plan | Connect (₹2,000/mo) |
| Pricing | Flat fee, unlimited API calls |
| Rate limit | 3 requests/second |
| Our usage | 1 request per 30 seconds (0.03 RPS) |
| Daily calls | ~750 (alert checker) + ~30 (OHLC) + ~20 (misc) = ~800 |
| Capacity used | <1% of rate limit |
| Upgrade path | WebSocket streaming for real-time ticks (later) |

### Free APIs
| API | Limits | Used For |
|-----|--------|----------|
| Claude API | ~₹600-1200/mo pay-per-use | NLP, briefings, predictions, Q&A |
| Telegram Bot | Unlimited, free | Messaging |
| nsefin | No limits | FII/DII, options, pre-market |
| Finnhub | 60/min | Global news |
| NewsAPI | 100/day | Stock news |
| yfinance | No limits | Global indices fallback |

### Data Source Priority
| Workflow | Primary | Fallback |
|----------|---------|----------|
| WF2 (Alerts) | Kite quotes | Graceful "prices unavailable" message |
| WF4a (Global) | Claude web_search + Finnhub | yfinance indices |
| WF4b (FII/DII) | nsefin | "Data unavailable" noted in briefing |
| WF4c (Technicals) | Kite OHLC | yfinance historical |
| WF4d (Options) | nsefin | Skipped, noted in briefing |

---

# PART 15: GRACEFUL DEGRADATION

Every external API call wrapped in try-catch with user-friendly fallback:

### Kite Down
```
⚠️ Live prices temporarily unavailable.

Your portfolio (based on last known prices):
🟢 RELIANCE: 10 shares @ avg ₹2,850
🟢 INFY: 25 shares @ avg ₹1,420
...

I'll notify you when prices are back online.
Alerts are paused until connection restores.
```

### Claude Down
```
⚠️ AI analysis temporarily unavailable.

Your active alerts are still running.
Try again in a few minutes, or type "portfolio" for basic holdings view.
```

### Morning Briefing with Missing Data
```
🌅 Morning Briefing (partial data)

⚠️ Note: Global cues unavailable today (Finnhub timeout)

📊 Using available data: FII/DII ✅ Technicals ✅ Options ✅ News ✅

[...briefing with available data...]
```

The WF4 synthesis prompt receives: `"Missing data sources: global_cues. Generate briefing with available data. Do not guess or hallucinate missing information."`

---

# PART 16: BACKUP & EXPORT

### Daily Backup (backup.sh)
```bash
#!/bin/bash
# Runs at 4 AM daily via cron
BACKUP_DIR=/opt/stockpulse/backups
mkdir -p $BACKUP_DIR
docker exec stockpulse-db pg_dump -U stockpulse stockpulse | gzip > $BACKUP_DIR/stockpulse-$(date +%Y%m%d).sql.gz
# Keep last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
echo "Backup complete: stockpulse-$(date +%Y%m%d).sql.gz"
```

Add to crontab: `0 4 * * * /opt/stockpulse/backup.sh`

### Data Export Command
User types "export" or "download my data":

```
📤 Your StockPulse Data Export

Generating CSV files...

📊 trades.csv — 145 trades since Jan 2026
🔮 predictions.csv — 28 predictions (17 hit, 11 missed)
📈 snapshots.csv — 45 daily portfolio snapshots

[📥 Download All (ZIP)]
```

Bot generates CSV files, zips them, sends via Telegram file upload (supports up to 2GB).

### Monthly Scorecard (1st of each month)
```
📊 StockPulse Monthly Report — January 2026

📱 Usage: 847 messages | 234 commands | 3 CSV uploads
🔔 Alerts: 42 triggered | 18 patterns detected
🔮 Predictions: 12 made → 7 hit (58%) | Avg 6.2 sessions
📈 Portfolio: ₹6.8L → ₹7.3L (+7.4%)

🏆 Best call: RELIANCE ₹2,950 target (hit in 4 sessions, predicted 5-8)
❌ Worst call: WIPRO ₹480 target (expired, price went opposite)
📊 Most watched: RELIANCE (checked 34 times)

💡 Insight: Your afternoon trades perform better than morning trades.
```

---

# PART 17: MULTI-AGENT CURSOR BUILD

## Phase Layout (13 days)

```
PHASE 1: INFRASTRUCTURE (1 Agent — Day 1-2)
  docker-compose up → schema.sql → NSE service → Caddy SSL → backup cron

PHASE 2: PARALLEL BUILD (3 Agents — Day 3-7)
  Agent 1: WF1 (handler + onboarding + smart alerts) + WF6 (token)
  Agent 2: WF2 (alerts) + WF3 (patterns) + WF4e (midday pulse)
  Agent 3: WF4a-d (data collectors) + WF4 (briefing with attention score)

PHASE 3: INTEGRATION (2 Agents — Day 8-10)
  Agent 1: WF5 (EOD + cleanup) + WF7 (weekly + portfolio intelligence) + WF8 (predictions)
  Agent 2: Multi-user + CSV + memory + export + monthly scorecard

PHASE 4: TESTING (1 Agent — Day 11-13)
  Full test with real market data + prompt tuning
```

---

# PART 18: FILE MANIFEST

```
stockpulse/
├── docker-compose.yml
├── .env.example
├── Caddyfile
├── setup.sh
├── backup.sh                          ← NEW
├── schema.sql
│
├── nse-data-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── nse_data_service.py
│
├── n8n-workflows/                      (13 JSONs)
│   ├── wf1-message-handler.json       (updated: onboarding + smart alerts)
│   ├── wf2-alert-checker.json
│   ├── wf3-pattern-detector.json
│   ├── wf4a-global-data.json
│   ├── wf4b-flow-data.json
│   ├── wf4c-technical-data.json       (updated: attention_score)
│   ├── wf4d-options-news.json
│   ├── wf4-morning-briefing.json      (updated: tiered display + data completeness)
│   ├── wf4e-midday-pulse.json         ← NEW
│   ├── wf5-eod-summary.json           (updated: only moved stocks + cleanup)
│   ├── wf6-token-manager.json
│   ├── wf7-weekly-review.json         (updated: portfolio intelligence + monthly)
│   └── wf8-prediction-tracker.json
│
├── code-nodes/                         (13 JS modules)
│   ├── technical-analyzer.js
│   ├── alert-checker.js
│   ├── pattern-detector.js
│   ├── historical-matcher.js
│   ├── options-analyzer.js
│   ├── market-hours.js
│   ├── news-sentiment.js
│   ├── crypto-utils.js
│   ├── validation.js
│   ├── message-formatter.js
│   ├── csv-import.js
│   ├── user-auth.js
│   └── attention-score.js             ← NEW
│
├── claude-prompts/                     (6 prompts)
│   ├── 01-parser.md
│   ├── 02-briefing-v2.md              (updated: dynamic length + data completeness)
│   ├── 03-prediction-v2.md
│   ├── 04-eod-summary.md              (updated: only moved stocks)
│   ├── 05-weekly-review.md            (updated: portfolio intelligence)
│   └── 06-sentiment-scorer.md
│
├── templates/
│   └── trade-import-template.csv
│
└── docs/
    ├── SETUP-GUIDE.md                  (updated: credential ID replacement)
    ├── CURSOR-AGENTS.md
    ├── ENV-VARIABLES.md
    ├── IMPORTING-WORKFLOWS.md          (updated: find-replace instructions)
    ├── ADDING-USERS.md
    ├── NSE-SERVICE-API.md
    ├── BACKUP-RESTORE.md              ← NEW
    └── TROUBLESHOOTING.md
```

---

# PART 19: COSTS & TIMELINE

## Monthly Costs
| Service | Cost (₹) | Notes |
|---------|----------|-------|
| Kite Connect (1 user, flat) | 2,000 | Unlimited API calls |
| VPS (DigitalOcean 2GB) | 800 | All services |
| Claude API (~70 calls/day) | 600-1,200 | Set $20/mo spend limit |
| Telegram / NewsAPI / Finnhub / nsefin | 0 | Free |
| Domain | 100 | Annual averaged |
| **TOTAL** | **3,500-4,100** | **₹1,750-2,050 per user** |

## Timeline (13 days with multi-agent)
| Days | What |
|------|------|
| 1-2 | Infrastructure + backup cron |
| 3 | Telegram bot + webhook + groups + onboarding flow |
| 4-5 | WF1 + WF2 + WF3 + WF4e (parallel agents) |
| 6-7 | WF4a-d + WF4 with attention score (parallel) |
| 8-9 | WF5-8 + portfolio intelligence + export |
| 10 | Multi-user + CSV + memory |
| 11 | Security: encryption, webhook secret, rate limits |
| 12-13 | Full testing + prompt tuning + monthly scorecard |

---

# PART 20: CHANGELOG (v3.2 → v3.3)

| Change | Category | Detail |
|--------|----------|--------|
| **Tiered display** | UX | Top 5 by attention score + summary for rest. Handles 20-30 stocks without spam. |
| **Attention score** | UX | Composite score (alert proximity + move + news + volume + RSI + patterns) for prioritization |
| **Smart alert suggestions** | UX | After BUY: technical-level-based profit target + stop loss with inline buttons |
| **Midday pulse (WF4e)** | UX | 3-line 12:30 PM update. No Claude cost. Bot feels alive between morning and EOD. |
| **Guided onboarding** | UX | New user → inline button walkthrough → first trade → first alert → ready |
| **Dynamic briefing length** | UX | Short when boring, long when eventful. Prompt-level change. |
| **Portfolio intelligence** | AI | Concentration, sector tilt, underperformers, FII alignment in weekly review |
| **Monthly scorecard** | Founder | 1st of month: usage, accuracy, P&L, best/worst calls |
| **Data export** | Founder | "export" command → CSV zip via Telegram |
| **Graceful Kite-down** | Reliability | Fallback messaging + alert pausing when Kite unavailable |
| **Data completeness check** | Dev | WF4 tells Claude which sources are missing; no hallucination |
| **Credential ID docs** | Dev | Find-replace instructions for workflow import |
| **Webhook secret** | Security | Telegram secret_token prevents webhook impersonation |
| **Daily backup** | Security | backup.sh + cron at 4 AM. 30-day retention. |
| **Claude spend limit** | Security | $20/month cap documented in setup guide |
| **backup.sh** | New file | PostgreSQL backup script |
| **WF4e** | New workflow | Midday pulse (13th workflow) |
| **attention-score.js** | New module | Attention score computation (13th code module) |

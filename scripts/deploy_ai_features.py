#!/usr/bin/env python3
"""
StockPulse — Deploy All 5 AI Feature Phases to WF1

Phase 1: Intent parser — add analyze + ask intents
Phase 2: Portfolio with live P&L (Kite prices)
Phase 3: Analyze command — deep AI analysis (replaces weak predict)
Phase 4: NLP Ask command — natural language Q&A
Phase 5: Polish — update help text + unknown handler

Usage:
    python3 scripts/deploy_ai_features.py
"""

import json, copy, time, sys, os
import urllib.request, urllib.error

# ── Credentials (hardcoded from WF1 inspection) ──────────────────────────────
CREDS_TELEGRAM = {"telegramApi": {"id": "oh2jj2bRbyNVQvgB", "name": "Telegram account"}}
CREDS_POSTGRES  = {"postgres":   {"id": "6dSdIQ2xAFPzyEwe", "name": "Postgres account"}}
CREDS_CLAUDE    = {"httpHeaderAuth": {"id": "Idkjo6pmv2QE4urQ", "name": "Anthropic Header Auth"}}
KITE_API_KEY    = "gifzm9kfars6kr8x"   # as it appears in Fetch Kite Quote
WF1_N8N_ID      = "kGn3KwIfHldiwuGW"
WF1_FILE        = os.path.join(os.path.dirname(__file__), "..", "n8n-workflows", "wf1-message-handler.json")

# ── Load .env ─────────────────────────────────────────────────────────────────
env = {}
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

DOMAIN      = env.get("DOMAIN", "stockpulse.co.in")
N8N_API_KEY = env.get("N8N_API_KEY", os.environ.get("N8N_API_KEY", ""))

# ── n8n API helper ────────────────────────────────────────────────────────────
def n8n(path, method="GET", data=None):
    url = f"https://{DOMAIN}/api/v1{path}"
    headers = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e.read().decode() if e.fp else ""
            print(f"  HTTP {e.code}: {err[:300]}")
            if attempt < 3 and e.code >= 500:
                wait = 2 ** (attempt + 1)
                print(f"  Retry in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))
            else:
                raise

# ── Load WF1 JSON ─────────────────────────────────────────────────────────────
print("Loading WF1 from disk...")
with open(WF1_FILE) as f:
    wf = json.load(f)

nodes     = wf["nodes"]
conns     = wf["connections"]
nodes_map = {n["name"]: n for n in nodes}

print(f"  WF1 loaded: {len(nodes)} nodes, {len(conns)} connection groups")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Intent Parser: add analyze + ask
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[Phase 1] Updating intent parser...")

NEW_SYSTEM = '\n'.join([
    'You are a stock trading message parser for Indian markets (NSE/BSE).',
    'Extract intent and data from user messages. Respond ONLY in valid JSON format with no other text:',
    '{',
    '  "intent": "buy|sell|alert_set|alert_cancel|portfolio|analyze|briefing|alerts_list|sync|login|settings|help|ask|clarify|unknown",',
    '  "symbol": "STOCK_SYMBOL or null",',
    '  "quantity": "number or null",',
    '  "price": "number or null",',
    '  "lower_bound": "number or null",',
    '  "upper_bound": "number or null",',
    '  "request_token": "string or null",',
    '  "raw_query": "original message if intent is analyze, ask, or unknown",',
    '  "query": "the specific question being asked if intent is ask"',
    '}',
    '',
    'Map common names: Reliance->RELIANCE, Infosys->INFY, TCS->TCS, HDFC Bank->HDFCBANK,',
    'Tata Motors->TATAMOTORS, Wipro->WIPRO, ITC->ITC, SBI->SBIN, Axis Bank->AXISBANK,',
    'Kotak->KOTAKBANK, Bajaj Finance->BAJFINANCE, HCL Tech->HCLTECH, Asian Paints->ASIANPAINT,',
    'Maruti->MARUTI, Sun Pharma->SUNPHARMA, Titan->TITAN, L&T->LT, Adani->ADANIENT, Bharti Airtel->BHARTIARTL.',
    'Default exchange: NSE. If date not mentioned, use today. If price not mentioned, set null.',
    'For "alert" or "set alert", extract symbol + bounds. "alert reliance 2800-2950" means lower=2800, upper=2950.',
    'For "portfolio"/"holdings"/"what do i own", intent=portfolio.',
    'For "analyze X", "analysis of X", "check X", "deep dive X", intent=analyze with symbol.',
    'For "predict X", "when will X hit Y", intent=analyze (map predict->analyze) with symbol and upper_bound.',
    'For "briefing"/"morning update"/"market update", intent=briefing.',
    'For natural language questions like "why did X fall?", "top 5 losses", "what should I sell?",',
    '"how is my portfolio doing?", intent=ask, query=the question text, symbol=X if mentioned.',
    'For callback data like "sell_RELIANCE_market", parse as intent=sell, symbol=RELIANCE.',
    'For "login ABC123", intent=login, request_token=ABC123. For bare "login", intent=login, request_token=null.',
])

# Update Claude: Parse Intent jsonBody
# The jsonBody is an n8n expression string like ={{ JSON.stringify({...system: 'OLD'...}) }}
# We rebuild it entirely with the new system prompt (single-line, JS-safe)
pi_node = nodes_map["Claude: Parse Intent"]
new_sys_js = NEW_SYSTEM.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
pi_node["parameters"]["jsonBody"] = (
    "={{ JSON.stringify({ model: 'claude-sonnet-4-20250514', max_tokens: 500,"
    " system: '" + new_sys_js + "',"
    " messages: [{ role: 'user', content: $json.message_text }] }) }}"
)
print("  ✓ Claude: Parse Intent — system prompt updated")

# Update Parse Claude Response to extract query field
nodes_map["Parse Claude Response"]["parameters"]["jsCode"] = r"""// Parse Claude's response into structured data
const response = $input.first().json;
let parsed;

try {
  const text = response.content[0].text;
  const clean = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
  parsed = JSON.parse(clean);
} catch (e) {
  parsed = {
    intent: 'unknown',
    raw_query: $('Prepare User Context').item.json.message_text,
    parse_error: e.message
  };
}

const ctx = $('Prepare User Context').item.json;

return [{
  json: {
    ...ctx,
    intent: parsed.intent,
    symbol: parsed.symbol ? parsed.symbol.toUpperCase().replace(/[^A-Z0-9&-]/g, '') : null,
    quantity: parsed.quantity ? parseInt(parsed.quantity) : null,
    price: parsed.price ? parseFloat(parsed.price) : null,
    lower_bound: parsed.lower_bound ? parseFloat(parsed.lower_bound) : null,
    upper_bound: parsed.upper_bound ? parseFloat(parsed.upper_bound) : null,
    request_token: parsed.request_token || null,
    raw_query: parsed.raw_query || parsed.query || null,
    query: parsed.query || parsed.raw_query || null
  }
}];"""
print("  ✓ Parse Claude Response — query field added")

# Update Route by Intent switch: predict → analyze, add ask rule
route = nodes_map["Route by Intent"]
rules = route["parameters"]["rules"]["values"]

for rule in rules:
    for cond in rule.get("conditions", {}).get("conditions", []):
        if cond.get("rightValue") == "predict":
            cond["rightValue"] = "analyze"
            print("  ✓ Switch rule: predict → analyze")

# Add ask rule (output index = len(rules), i.e. 11)
rules.append({
    "conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
        "conditions": [{
            "id": "rule-ask",
            "leftValue": "={{ $(\"Parse Claude Response\").item.json.intent }}",
            "rightValue": "ask",
            "operator": {"type": "string", "operation": "equals"}
        }],
        "combinator": "and"
    }
})
print(f"  ✓ Switch rule added for 'ask' (output {len(rules)-1})")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Portfolio with live P&L
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[Phase 2] Adding portfolio live P&L...")

# New node: Get Portfolio Token (postgres)
get_portfolio_token = {
    "id": "get-portfolio-token",
    "name": "Get Portfolio Token",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [2580, 250],
    "parameters": {
        "operation": "executeQuery",
        "query": (
            "SELECT access_token_encrypted, token_expiry > NOW() as is_valid "
            "FROM kite_sessions "
            "WHERE user_id = (SELECT id FROM users WHERE is_kite_provider = true LIMIT 1) "
            "LIMIT 1"
        ),
        "options": {}
    },
    "credentials": CREDS_POSTGRES
}

# New node: Fetch Portfolio Prices (HTTP → Kite)
fetch_portfolio_prices = {
    "id": "fetch-portfolio-prices",
    "name": "Fetch Portfolio Prices",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [2700, 250],
    "parameters": {
        "method": "GET",
        "url": (
            "={{ 'https://api.kite.trade/quote?' + "
            "$('Handle PORTFOLIO').all().map(function(i){ return 'i=NSE:' + i.json.symbol; }).join('&') }}"
        ),
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {
                    "name": "Authorization",
                    "value": f"={{ 'token {KITE_API_KEY}:' + $input.first().json.access_token_encrypted }}"
                },
                {"name": "X-Kite-Version", "value": "3"}
            ]
        },
        "options": {
            "response": {
                "response": {"neverError": True}
            }
        }
    }
}

# Updated Format Portfolio with live P&L
nodes_map["Format Portfolio"]["position"] = [2920, 250]
nodes_map["Format Portfolio"]["parameters"]["jsCode"] = r"""// Format portfolio with live Kite prices + P&L
const holdings = $('Handle PORTFOLIO').all().map(i => i.json);

// Parse live prices from Kite response
let prices = {};
try {
  const raw = $input.first().json;
  if (raw && raw.status === 'success' && raw.data) {
    for (const [key, val] of Object.entries(raw.data)) {
      const sym = key.split(':')[1];
      prices[sym] = val;
    }
  }
} catch(e) {}

if (holdings.length === 0 || !holdings[0].symbol) {
  return [{ json: { message: '📭 *No holdings found*\n\nStart by logging a trade:\n`buy RELIANCE 10 at 2850`' } }];
}

const hasLive = Object.keys(prices).length > 0;
let totalInvested = 0, totalCurrent = 0, totalTodayPL = 0;
let msg = '📊 *Your Portfolio*' + (hasLive ? ' 🔴 Live' : '') + '\n\n';

for (const h of holdings.slice(0, 15)) {
  const invested = h.net_quantity * h.avg_buy_price;
  totalInvested += invested;
  const q = prices[h.symbol];
  const ltp = q && q.last_price;

  if (ltp) {
    const current = h.net_quantity * ltp;
    totalCurrent += current;
    const pl = current - invested;
    const plPct = (pl / invested * 100).toFixed(1);
    const plSign = pl >= 0 ? '+' : '-';
    const plStr = plSign + '₹' + Math.round(Math.abs(pl)).toLocaleString('en-IN');
    const todayPL = h.net_quantity * (q.change || 0);
    totalTodayPL += todayPL;
    const arrow = pl >= 0 ? '📈' : '📉';
    msg += arrow + ' *' + h.symbol + '*  ' + h.net_quantity + ' @ ₹' + h.avg_buy_price + '\n';
    msg += '   ₹' + ltp.toLocaleString('en-IN') + '  ' + plStr + ' (' + plPct + '%)\n\n';
  } else {
    msg += '⚪ *' + h.symbol + '*  ' + h.net_quantity + ' @ ₹' + h.avg_buy_price + '\n';
    msg += '   Invested: ₹' + Math.round(invested).toLocaleString('en-IN') + '\n\n';
  }
}

if (holdings.length > 15) {
  msg += '_...and ' + (holdings.length - 15) + ' more positions_\n\n';
}

msg += '━━━━━━━━━━━━━━━━━━\n';
msg += '💰 *Invested: ₹' + Math.round(totalInvested).toLocaleString('en-IN') + '*\n';

if (totalCurrent > 0) {
  const totalPL = totalCurrent - totalInvested;
  const totalPLPct = (totalPL / totalInvested * 100).toFixed(1);
  const plSign = totalPL >= 0 ? '+' : '-';
  const plStr = plSign + '₹' + Math.round(Math.abs(totalPL)).toLocaleString('en-IN');
  msg += '📊 *Current: ₹' + Math.round(totalCurrent).toLocaleString('en-IN') + '*\n';
  msg += (totalPL >= 0 ? '📈' : '📉') + ' *P&L: ' + plStr + ' (' + totalPLPct + '%)*\n';
  if (totalTodayPL !== 0) {
    const tSign = totalTodayPL >= 0 ? '+' : '-';
    msg += '📅 *Today: ' + tSign + '₹' + Math.round(Math.abs(totalTodayPL)).toLocaleString('en-IN') + '*\n';
  }
} else if (!hasLive) {
  msg += '\n_Live prices unavailable — Kite session needed_';
}

const ctx = $('Parse Claude Response').item.json;
return [{ json: { chat_id: ctx.chat_id, message: msg } }];"""

# Move Send Portfolio right
nodes_map["Send Portfolio"]["position"] = [3140, 250]

# Add new nodes to wf
nodes.append(get_portfolio_token)
nodes.append(fetch_portfolio_prices)

# Reconnect: Handle PORTFOLIO → Get Portfolio Token → Fetch Portfolio Prices → Format Portfolio
conns["Handle PORTFOLIO"] = {"main": [[{"node": "Get Portfolio Token", "type": "main", "index": 0}]]}
conns["Get Portfolio Token"] = {"main": [[{"node": "Fetch Portfolio Prices", "type": "main", "index": 0}]]}
conns["Fetch Portfolio Prices"] = {"main": [[{"node": "Format Portfolio", "type": "main", "index": 0}]]}

print("  ✓ Get Portfolio Token node added")
print("  ✓ Fetch Portfolio Prices node added")
print("  ✓ Format Portfolio updated with live P&L")
print("  ✓ Portfolio connections rewired")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Analyze Command (replaces predict)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[Phase 3] Building analyze command...")

# Rename Get Quote Token → Get Analyze Token
nodes_map["Get Quote Token"]["name"] = "Get Analyze Token"
if "Get Quote Token" in conns:
    conns["Get Analyze Token"] = conns.pop("Get Quote Token")

# Fix Fetch Kite Quote auth reference (was Get Quote Token, now Get Analyze Token)
fkq = nodes_map["Fetch Kite Quote"]
fkq["parameters"]["headerParameters"]["parameters"][0]["value"] = (
    f"={{ 'token {KITE_API_KEY}:' + $('Get Analyze Token').first().json.access_token_encrypted }}"
)
fkq["position"] = [2720, 400]

# New: Fetch Analyze Data from staging_data
fetch_analyze_data = {
    "id": "fetch-analyze-data",
    "name": "Fetch Analyze Data",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [2960, 400],
    "parameters": {
        "operation": "executeQuery",
        "query": (
            "SELECT data_type, data FROM staging_data "
            "WHERE symbol = $1 AND data_date >= CURRENT_DATE - INTERVAL '1 day' "
            "ORDER BY data_date DESC LIMIT 10"
        ),
        "options": {
            "queryReplacement": "={{ [$('Parse Claude Response').item.json.symbol] }}"
        }
    },
    "credentials": CREDS_POSTGRES
}

# New: Claude: Analyze HTTP node
ANALYZE_BODY = (
    "={{ JSON.stringify({"
    " model: 'claude-sonnet-4-20250514',"
    " max_tokens: 1000,"
    " system: 'You are an expert Indian stock market analyst. Provide concise, actionable analysis. Use INR symbol for prices. Keep under 400 words. Format for Telegram with *bold* and emojis.',"
    " messages: [{"
    "  role: 'user',"
    "  content: 'Analyze ' + $('Parse Claude Response').item.json.symbol + ' for me.\\n\\n'"
    "   + 'Live Quote: ' + JSON.stringify($('Fetch Kite Quote').first().json.data || {}) + '\\n\\n'"
    "   + 'Staged Data: ' + JSON.stringify($('Fetch Analyze Data').all().map(function(i){ return i.json; })) + '\\n\\n'"
    "   + 'User target: ' + ($('Parse Claude Response').item.json.upper_bound || 'none') + '\\n\\n'"
    "   + 'Provide: 1) Current trend & momentum 2) Key support/resistance 3) Technical signals (RSI/MACD if available) 4) AI verdict (Bullish/Bearish/Neutral) with reasoning 5) Near-term price target range.'"
    " }]"
    "}) }}"
)

claude_analyze = {
    "id": "claude-analyze",
    "name": "Claude: Analyze",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [3200, 400],
    "parameters": {
        "method": "POST",
        "url": "https://api.anthropic.com/v1/messages",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "anthropic-version", "value": "2023-06-01"},
                {"name": "content-type", "value": "application/json"}
            ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": ANALYZE_BODY
    },
    "credentials": CREDS_CLAUDE
}

# Update Format Prediction → Format Analysis
fmt_pred = nodes_map["Format Prediction"]
fmt_pred["name"] = "Format Analysis"
fmt_pred["position"] = [3440, 400]
fmt_pred["parameters"]["jsCode"] = r"""// Format deep AI analysis response
const symbol = $('Parse Claude Response').item.json.symbol;
const ctx = $('Parse Claude Response').item.json;

// Get live quote
let quote = {};
try {
  const raw = $('Fetch Kite Quote').first().json;
  if (raw && raw.status === 'success' && raw.data) {
    const key = Object.keys(raw.data)[0];
    quote = raw.data[key] || {};
  }
} catch(e) {}

// Get Claude analysis text
let analysis = '';
try {
  analysis = $input.first().json.content[0].text;
} catch(e) {
  analysis = '⚠️ Analysis unavailable. Try again or check your Kite session.';
}

let msg = '';
const price = quote.last_price;
if (price) {
  const change = quote.change || 0;
  const prevClose = quote.ohlc && quote.ohlc.close;
  const changePct = prevClose ? ((price - prevClose) / prevClose * 100).toFixed(2) : '0.00';
  const arrow = change >= 0 ? '📈' : '📉';
  msg += arrow + ' *' + symbol + '*  ₹' + price.toLocaleString('en-IN') + '\n';
  msg += '   ' + (change >= 0 ? '+' : '') + change.toFixed(2) + ' (' + (change >= 0 ? '+' : '') + changePct + '%)\n\n';
}

msg += analysis;

return [{ json: { chat_id: ctx.chat_id, message: msg } }];"""

# Update Send Prediction → Send Analysis
snd_pred = nodes_map["Send Prediction"]
snd_pred["name"] = "Send Analysis"
snd_pred["position"] = [3680, 400]

# Add new nodes
nodes.append(fetch_analyze_data)
nodes.append(claude_analyze)

# Reconnect analyze flow:
# Get Analyze Token → Fetch Kite Quote → Fetch Analyze Data → Claude: Analyze → Format Analysis → Send Analysis
conns["Fetch Kite Quote"] = {"main": [[{"node": "Fetch Analyze Data", "type": "main", "index": 0}]]}
conns["Fetch Analyze Data"] = {"main": [[{"node": "Claude: Analyze", "type": "main", "index": 0}]]}
conns["Claude: Analyze"] = {"main": [[{"node": "Format Analysis", "type": "main", "index": 0}]]}
conns["Format Analysis"] = {"main": [[{"node": "Send Analysis", "type": "main", "index": 0}]]}
# Remove stale Format Prediction key (renamed)
conns.pop("Format Prediction", None)

# Fix Route by Intent output 4 to point to Get Analyze Token
route_main = conns["Route by Intent"]["main"]
route_main[4] = [{"node": "Get Analyze Token", "type": "main", "index": 0}]

print("  ✓ Get Quote Token renamed → Get Analyze Token")
print("  ✓ Fetch Analyze Data node added (staging_data lookup)")
print("  ✓ Claude: Analyze node added")
print("  ✓ Format Analysis updated with price header + AI text")
print("  ✓ Analyze flow connected")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — NLP Ask Command
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[Phase 4] Building Ask command...")

# New: Fetch Ask Context (postgres — portfolio + query context)
fetch_ask_ctx = {
    "id": "fetch-ask-context",
    "name": "Fetch Ask Context",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.5,
    "position": [2460, 580],
    "parameters": {
        "operation": "executeQuery",
        "query": (
            "SELECT h.symbol, h.net_quantity, h.avg_buy_price, h.total_invested, "
            "(SELECT data FROM staging_data WHERE symbol = h.symbol "
            " ORDER BY data_date DESC LIMIT 1) as latest_data "
            "FROM holdings h "
            "WHERE h.user_id = $1 "
            "ORDER BY h.total_invested DESC LIMIT 15"
        ),
        "options": {
            "queryReplacement": "={{ [$('Parse Claude Response').item.json.user_id] }}"
        }
    },
    "credentials": CREDS_POSTGRES
}

# New: Claude: Ask HTTP node
ASK_BODY = (
    "={{ JSON.stringify({"
    " model: 'claude-sonnet-4-20250514',"
    " max_tokens: 600,"
    " system: 'You are an expert Indian stock market assistant. The user has asked a question about their portfolio or the market. Answer concisely and helpfully. Use INR symbol for prices. Format for Telegram with *bold* and emojis. Keep under 300 words.',"
    " messages: [{"
    "  role: 'user',"
    "  content: 'Question: ' + $('Parse Claude Response').item.json.query + '\\n\\n'"
    "   + 'My portfolio: ' + JSON.stringify($input.all().map(function(i){ return { symbol: i.json.symbol, qty: i.json.net_quantity, avg: i.json.avg_buy_price, invested: i.json.total_invested }; })) + '\\n\\n'"
    "   + 'Please answer the question. If it is about a specific stock, use the portfolio data. If asking about losses/gains, calculate from avg price vs any available data.'"
    " }]"
    "}) }}"
)

claude_ask = {
    "id": "claude-ask",
    "name": "Claude: Ask",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [2700, 580],
    "parameters": {
        "method": "POST",
        "url": "https://api.anthropic.com/v1/messages",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "anthropic-version", "value": "2023-06-01"},
                {"name": "content-type", "value": "application/json"}
            ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": ASK_BODY
    },
    "credentials": CREDS_CLAUDE
}

# New: Format Ask Response (code)
format_ask = {
    "id": "format-ask",
    "name": "Format Ask Response",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [2940, 580],
    "parameters": {
        "jsCode": r"""const ctx = $('Parse Claude Response').item.json;
let answer = '';
try {
  answer = $input.first().json.content[0].text;
} catch(e) {
  answer = "Sorry, I couldn't process that question. Try rephrasing or use `help` for commands.";
}
return [{ json: { chat_id: ctx.chat_id, message: answer } }];"""
    }
}

# New: Send Ask Response (telegram)
send_ask = {
    "id": "send-ask",
    "name": "Send Ask Response",
    "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2,
    "position": [3180, 580],
    "parameters": {
        "chatId": "={{ $('Format Ask Response').item.json.chat_id }}",
        "text": "={{ $('Format Ask Response').item.json.message }}",
        "additionalFields": {"parse_mode": "Markdown"}
    },
    "credentials": CREDS_TELEGRAM
}

# Add new nodes
nodes.extend([fetch_ask_ctx, claude_ask, format_ask, send_ask])

# Connections for ask flow
conns["Fetch Ask Context"] = {"main": [[{"node": "Claude: Ask", "type": "main", "index": 0}]]}
conns["Claude: Ask"] = {"main": [[{"node": "Format Ask Response", "type": "main", "index": 0}]]}
conns["Format Ask Response"] = {"main": [[{"node": "Send Ask Response", "type": "main", "index": 0}]]}

# Add output 11 for ask in Route by Intent (index 11 = new rule we added)
# The "else/fallback" (Handle Unknown) is currently at the last index.
# Insert ask BEFORE it so: ask=output 11, Handle Unknown=output 12 (else)
route_main.insert(-1, [{"node": "Fetch Ask Context", "type": "main", "index": 0}])

print("  ✓ Fetch Ask Context node added")
print("  ✓ Claude: Ask node added")
print("  ✓ Format Ask Response node added")
print("  ✓ Send Ask Response node added")
print("  ✓ Ask flow connected at switch output 11")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Polish: Help + Unknown Handler
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[Phase 5] Polishing help text and unknown handler...")

nodes_map["Handle HELP"]["parameters"]["text"] = (
    "🤖 *StockPulse Commands*\n\n"
    "📈 *Trading*\n"
    "`buy RELIANCE 10 at 2850`\n"
    "`sell INFY 5 at 1500`\n\n"
    "🔔 *Alerts*\n"
    "`alert RELIANCE 2800-2950`\n"
    "`alerts` — view active alerts\n"
    "`cancel alert RELIANCE`\n\n"
    "📊 *Portfolio*\n"
    "`portfolio` — live holdings + P&L\n"
    "`sync` — sync from Kite (User 1)\n\n"
    "🔮 *AI Analysis*\n"
    "`analyze RELIANCE` — deep AI analysis\n"
    "`analyze TCS 4000` — analysis with target\n\n"
    "❓ *Ask Anything*\n"
    "`why did Reliance fall?`\n"
    "`top 5 losses in my portfolio`\n"
    "`what should I sell?`\n"
    "`how is my portfolio doing?`\n\n"
    "🌅 *Briefing*\n"
    "`briefing` — morning AI analysis\n\n"
    "📎 *File Upload*\n"
    "Send a CSV file to bulk import trades\n\n"
    "⚙️ *Settings*\n"
    "`login <token>` — connect Kite\n"
    "`settings` — view preferences"
)

nodes_map["Handle Unknown"]["parameters"]["text"] = (
    "={{ '🤔 I didn\\'t understand that.\\n\\n'"
    " + 'You said: \"' + $(\\'Prepare User Context\\').item.json.message_text + '\"\\n\\n'"
    " + 'Try:\\n'"
    " + '• `analyze RELIANCE` — deep AI stock analysis\\n'"
    " + '• `portfolio` — see holdings with live P&L\\n'"
    " + '• `why did X fall?` — ask me anything\\n'"
    " + '• `help` — all commands' }}"
)

print("  ✓ Handle HELP updated with analyze + ask commands")
print("  ✓ Handle Unknown updated with better suggestions")

# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOY TO N8N
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[Deploy] Fetching current WF1 from n8n (ID: {WF1_N8N_ID})...")
current = n8n(f"/workflows/{WF1_N8N_ID}")
print(f"  Current: {current['name']} ({len(current['nodes'])} nodes)")

payload = {
    "name": current["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": current.get("settings", {}),
    "staticData": current.get("staticData")
}

print(f"  Deploying {len(wf['nodes'])} nodes ({len(wf['nodes']) - len(current['nodes'])} new)...")

result = n8n(f"/workflows/{WF1_N8N_ID}", method="PUT", data=payload)
print(f"  ✅ Deployed! n8n reports {len(result.get('nodes', []))} nodes")

# Activate
try:
    n8n(f"/workflows/{WF1_N8N_ID}/activate", method="POST")
    print("  ✅ Workflow activated")
except Exception as e:
    print(f"  ⚠️  Activate failed (may already be active): {e}")

# Save updated JSON back to disk (use n8n's response as source of truth)
with open(WF1_FILE, "w") as f:
    json.dump(result, f, indent=2)
print(f"  ✅ Saved to {WF1_FILE}")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("✅  ALL 5 PHASES COMPLETE")
print("═"*60)
print("  Phase 1 ✓  Intent parser — analyze + ask intents added")
print("  Phase 2 ✓  Portfolio — live P&L via Kite prices")
print("  Phase 3 ✓  Analyze — deep AI analysis (replaces predict)")
print("  Phase 4 ✓  Ask — natural language Q&A")
print("  Phase 5 ✓  Polish — help + unknown handler updated")
print(f"\n  Total nodes: {len(result.get('nodes', []))}")
print("═"*60)

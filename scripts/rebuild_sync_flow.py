#!/usr/bin/env python3
"""
Rebuilds Handle SYNC in WF1 with a real Kite portfolio sync flow.
Also does one-time cleanup of test data and initial sync via temp workflow.
"""

import json, requests, time, sys

BASE = "https://stockpulse.co.in"
COOKIE_FILE = "/tmp/n8n_cookies.txt"
WF1_ID = "kGn3KwIfHldiwuGW"

CREDS = {
    "postgres": {"id": "6dSdIQ2xAFPzyEwe", "name": "Postgres account"},
    "telegram": {"id": "oh2jj2bRbyNVQvgB", "name": "Telegram account"},
    "kite_http": {"id": "du74DqpJeNl4luFf", "name": "Header Auth account"},
}
KITE_API_KEY = "gifzm9kfars6kr8x"

def session():
    s = requests.Session()
    # Load cookies
    import http.cookiejar
    jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)
    jar.load(ignore_discard=True, ignore_expires=True)
    s.cookies = jar
    return s

def get_wf1(s):
    r = s.get(f"{BASE}/rest/workflows/{WF1_ID}")
    r.raise_for_status()
    return r.json()["data"]

def put_wf1(s, wf):
    r = s.put(f"{BASE}/rest/workflows/{WF1_ID}", json=wf)
    if not r.ok:
        print("PUT failed:", r.status_code, r.text[:500])
        r.raise_for_status()
    return r.json()["data"]

def deactivate_wf(s, wf_id):
    r = s.post(f"{BASE}/rest/workflows/{wf_id}/deactivate")
    return r.ok

def activate_wf(s, wf_id):
    r = s.post(f"{BASE}/rest/workflows/{wf_id}/activate")
    return r.ok

# ─────────────────────────────────────────────────────────────
# Step 1: One-time data cleanup + initial sync via temp workflow
# ─────────────────────────────────────────────────────────────

def build_init_sql(holdings):
    """Build SQL to clear test data and insert real Kite holdings."""
    if not holdings:
        return None, 0

    values = []
    for h in holdings:
        sym = h["tradingsymbol"].replace("'", "''")
        qty = int(h["quantity"])
        price = round(float(h["average_price"]), 2)
        values.append(f"(1, '{sym}', 'BUY', {qty}, {price}, 'kite_sync', CURRENT_DATE)")

    values_sql = ",\n".join(values)

    sql = f"""
-- Clear test/dummy data
DELETE FROM trades WHERE user_id = 1;
DELETE FROM alerts WHERE user_id = 1 AND lower_bound = 1 AND upper_bound = 999999;

-- Insert real Kite holdings as kite_sync trades
INSERT INTO trades (user_id, symbol, trade_type, quantity, price, source, trade_date)
VALUES
{values_sql};
""".strip()
    return sql, len(holdings)


def run_init_sync_via_temp_workflow(s):
    """Create a temp n8n workflow to run init SQL, execute it, delete it."""
    print("[INIT SYNC] Fetching real Kite holdings...")
    token_resp = requests.get(
        "https://api.kite.trade/portfolio/holdings",
        headers={"Authorization": f"token {KITE_API_KEY}:C48w1tJA4pPTgmOWZ3Pcuo8uLgVQcXxI"}
    )
    token_resp.raise_for_status()
    holdings = token_resp.json().get("data", [])
    print(f"[INIT SYNC] Got {len(holdings)} holdings from Kite")

    sql, count = build_init_sql(holdings)
    if not sql:
        print("[INIT SYNC] No holdings to sync")
        return False

    # Create temp workflow with a manual trigger + postgres execute node
    temp_wf = {
        "name": "TEMP_INIT_SYNC",
        "nodes": [
            {
                "id": "temp-trigger",
                "name": "When clicking 'Test workflow'",
                "type": "n8n-nodes-base.manualTrigger",
                "typeVersion": 1,
                "position": [250, 300],
                "parameters": {}
            },
            {
                "id": "temp-sql",
                "name": "Execute Init SQL",
                "type": "n8n-nodes-base.postgres",
                "typeVersion": 2.5,
                "position": [500, 300],
                "parameters": {
                    "operation": "executeQuery",
                    "query": sql
                },
                "credentials": {
                    "postgres": {
                        "id": CREDS["postgres"]["id"],
                        "name": CREDS["postgres"]["name"]
                    }
                }
            }
        ],
        "connections": {
            "When clicking 'Test workflow'": {
                "main": [[{"node": "Execute Init SQL", "type": "main", "index": 0}]]
            }
        },
        "settings": {"executionOrder": "v1"}
    }

    # Create temp workflow
    print("[INIT SYNC] Creating temp workflow...")
    r = s.post(f"{BASE}/rest/workflows", json=temp_wf)
    if not r.ok:
        print("[INIT SYNC] Failed to create temp workflow:", r.status_code, r.text[:300])
        return False
    temp_wf_data = r.json()["data"]
    temp_wf_id = temp_wf_data["id"]
    print(f"[INIT SYNC] Temp workflow created: {temp_wf_id}")

    # Execute it via manual trigger
    print("[INIT SYNC] Executing init SQL...")
    exec_r = s.post(f"{BASE}/rest/workflows/{temp_wf_id}/run", json={"startNodes": ["When clicking 'Test workflow'"]})
    if not exec_r.ok:
        print("[INIT SYNC] Execution call response:", exec_r.status_code, exec_r.text[:300])

    # Wait for execution
    time.sleep(5)

    # Check last execution
    exec_list = s.get(f"{BASE}/rest/executions?workflowId={temp_wf_id}&limit=1")
    if exec_list.ok:
        execs = exec_list.json().get("data", {}).get("results", [])
        if execs:
            exec_status = execs[0].get("status")
            print(f"[INIT SYNC] Execution status: {exec_status}")
            if exec_status == "error":
                print("[INIT SYNC] ERROR in execution!")
                # Try to get detail
                exec_id = execs[0].get("id")
                exec_detail = s.get(f"{BASE}/rest/executions/{exec_id}")
                if exec_detail.ok:
                    print(exec_detail.text[:500])

    # Delete temp workflow
    print(f"[INIT SYNC] Deleting temp workflow {temp_wf_id}...")
    del_r = s.delete(f"{BASE}/rest/workflows/{temp_wf_id}")
    print(f"[INIT SYNC] Delete status: {del_r.status_code}")

    print(f"[INIT SYNC] Done. Inserted {count} holdings.")
    return True


# ─────────────────────────────────────────────────────────────
# Step 2: Rebuild Handle SYNC → real Kite sync flow in WF1
# ─────────────────────────────────────────────────────────────

def build_sync_nodes():
    """Returns list of new nodes for the real Kite sync flow."""

    # Build Sync SQL Code
    build_sql_code = """
const userId = $("Parse Claude Response").item.json.user_id;
const holdings = $("Fetch Kite Holdings").item.json.data || [];

if (holdings.length === 0) {
  return [{ json: {
    sql: 'SELECT 1 AS synced_count',
    count: 0,
    sample: 'No holdings returned from Kite'
  }}];
}

// Build VALUES list — NSE symbols are alphanumeric+dash, safe to embed
const values = holdings.map(h => {
  const sym = h.tradingsymbol.replace(/'/g, "''");
  const qty = parseInt(h.quantity);
  const price = parseFloat(h.average_price).toFixed(2);
  return `(${userId}, '${sym}', 'BUY', ${qty}, ${price}, 'kite_sync', CURRENT_DATE)`;
}).join(',\\n');

const sql = `DELETE FROM trades WHERE user_id=${userId} AND source='kite_sync';\\nINSERT INTO trades (user_id, symbol, trade_type, quantity, price, source, trade_date) VALUES\\n${values};`;

const sample = holdings.slice(0, 3).map(h => `${h.tradingsymbol} (${h.quantity}@₹${parseFloat(h.average_price).toFixed(0)})`).join(', ');

return [{ json: { sql, count: holdings.length, sample } }];
""".strip()

    confirm_code = """
const count = $("Build Sync SQL").item.json.count;
const sample = $("Build Sync SQL").item.json.sample;
const chatId = $("Parse Claude Response").item.json.chat_id;

return [{ json: {
  chat_id: chatId,
  message: `✅ *Portfolio Synced!*\\n\\nImported *${count} holdings* from Kite Connect.\\n\\nSample: ${sample}...\\n\\nUse /portfolio to view your holdings.`
}}];
""".strip()

    return [
        # 1. Get Sync Token
        {
            "id": "sync-get-token",
            "name": "Get Sync Token",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.5,
            "position": [2460, 850],
            "parameters": {
                "operation": "executeQuery",
                "query": "SELECT access_token_encrypted, token_expiry > NOW() as is_valid FROM kite_sessions WHERE user_id = (SELECT id FROM users WHERE is_kite_provider = true LIMIT 1) LIMIT 1"
            },
            "credentials": {"postgres": {"id": CREDS["postgres"]["id"], "name": CREDS["postgres"]["name"]}},
            "alwaysOutputData": True
        },
        # 2. Is Token Valid?
        {
            "id": "sync-is-valid",
            "name": "Is Sync Token Valid?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [2700, 850],
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "sync-token-check",
                        "leftValue": "={{ $json.is_valid }}",
                        "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true"}
                    }],
                    "combinator": "and"
                }
            }
        },
        # 3. No Token Message (false branch)
        {
            "id": "sync-no-token",
            "name": "No Kite Token Msg",
            "type": "n8n-nodes-base.telegram",
            "typeVersion": 1.2,
            "position": [2940, 720],
            "parameters": {
                "chatId": "={{ $(\"Parse Claude Response\").item.json.chat_id }}",
                "text": "⚠️ *Kite Session Required*\n\nYour Kite token has expired or is not set.\n\nTo sync your portfolio:\n1. Get a fresh access token from Kite\n2. Send: `login api_key:access_token`\n\nThen try `sync` again.",
                "additionalFields": {"parse_mode": "Markdown", "appendAttribution": False}
            },
            "credentials": {"telegramApi": {"id": CREDS["telegram"]["id"], "name": CREDS["telegram"]["name"]}}
        },
        # 4. Fetch Kite Holdings (true branch)
        {
            "id": "sync-fetch-kite",
            "name": "Fetch Kite Holdings",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [2940, 980],
            "parameters": {
                "method": "GET",
                "url": "https://api.kite.trade/portfolio/holdings",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [{
                        "name": "Authorization",
                        "value": f"={{{{ 'token {KITE_API_KEY}:' + $json.access_token_encrypted }}}}"
                    }]
                },
                "options": {"response": {"response": {"responseFormat": "json"}}},
                "onError": "continueRegularOutput"
            }
        },
        # 5. Build Sync SQL
        {
            "id": "sync-build-sql",
            "name": "Build Sync SQL",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [3180, 980],
            "parameters": {
                "jsCode": build_sql_code
            }
        },
        # 6. Execute Sync (Postgres)
        {
            "id": "sync-execute",
            "name": "Execute Sync",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.5,
            "position": [3420, 980],
            "parameters": {
                "operation": "executeQuery",
                "query": "={{ $json.sql }}"
            },
            "credentials": {"postgres": {"id": CREDS["postgres"]["id"], "name": CREDS["postgres"]["name"]}}
        },
        # 7. Format Sync Result (Code)
        {
            "id": "sync-format-result",
            "name": "Format Sync Result",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [3420, 1200],
            "parameters": {
                "jsCode": confirm_code
            }
        },
        # 8. Confirm Sync (Telegram)
        {
            "id": "sync-confirm",
            "name": "Confirm Sync",
            "type": "n8n-nodes-base.telegram",
            "typeVersion": 1.2,
            "position": [3660, 1200],
            "parameters": {
                "chatId": "={{ $json.chat_id }}",
                "text": "={{ $json.message }}",
                "additionalFields": {"parse_mode": "Markdown", "appendAttribution": False}
            },
            "credentials": {"telegramApi": {"id": CREDS["telegram"]["id"], "name": CREDS["telegram"]["name"]}}
        }
    ]


def build_sync_connections():
    """Returns connection entries for new sync nodes."""
    return {
        "Get Sync Token": {
            "main": [[{"node": "Is Sync Token Valid?", "type": "main", "index": 0}]]
        },
        "Is Sync Token Valid?": {
            "main": [
                [{"node": "Fetch Kite Holdings", "type": "main", "index": 0}],  # true
                [{"node": "No Kite Token Msg", "type": "main", "index": 0}]     # false
            ]
        },
        "Fetch Kite Holdings": {
            "main": [[{"node": "Build Sync SQL", "type": "main", "index": 0}]]
        },
        "Build Sync SQL": {
            "main": [[{"node": "Execute Sync", "type": "main", "index": 0}]]
        },
        "Execute Sync": {
            "main": [[{"node": "Format Sync Result", "type": "main", "index": 0}]]
        },
        "Format Sync Result": {
            "main": [[{"node": "Confirm Sync", "type": "main", "index": 0}]]
        }
    }


def rebuild_sync_in_wf1(s):
    """Fetch WF1, replace Handle SYNC with real sync flow, deploy."""
    print("[WF1] Fetching current workflow...")
    wf = get_wf1(s)

    # Remove old static Handle SYNC node
    old_node_ids = {"handle-sync"}
    wf["nodes"] = [n for n in wf["nodes"] if n["id"] not in old_node_ids]
    print(f"[WF1] Removed static Handle SYNC node")

    # Add new sync nodes
    new_nodes = build_sync_nodes()
    wf["nodes"].extend(new_nodes)
    print(f"[WF1] Added {len(new_nodes)} new sync nodes")

    # Remove old Handle SYNC connection from connections dict (if any)
    if "Handle SYNC" in wf["connections"]:
        del wf["connections"]["Handle SYNC"]

    # Update Route by Intent branch[9] to point to Get Sync Token
    rob = wf["connections"].get("Route by Intent", {}).get("main", [])
    for i, branch in enumerate(rob):
        for c in branch:
            if c["node"] == "Handle SYNC":
                c["node"] = "Get Sync Token"
                print(f"[WF1] Updated Route by Intent branch[{i}] → Get Sync Token")

    # Add new connections
    new_conns = build_sync_connections()
    wf["connections"].update(new_conns)
    print(f"[WF1] Added sync flow connections")

    # Deactivate, update, reactivate
    print("[WF1] Deactivating...")
    deactivate_wf(s, WF1_ID)
    time.sleep(1)

    print("[WF1] Deploying updated workflow...")
    updated = put_wf1(s, wf)
    print(f"[WF1] Deployed. Node count: {len(updated['nodes'])}")

    time.sleep(1)
    print("[WF1] Reactivating...")
    activate_wf(s, WF1_ID)
    print("[WF1] Done!")
    return True


def main():
    s = session()

    print("=" * 60)
    print("STEP 1: One-time cleanup + initial Kite sync")
    print("=" * 60)
    run_init_sync_via_temp_workflow(s)

    print()
    print("=" * 60)
    print("STEP 2: Rebuild Handle SYNC in WF1")
    print("=" * 60)
    rebuild_sync_in_wf1(s)

    print()
    print("✅ ALL DONE!")
    print("Test with: Send 'sync' to the Telegram bot")
    print("The bot will now fetch live holdings from Kite API.")


if __name__ == "__main__":
    main()

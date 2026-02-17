# Importing Workflows into n8n

## Method 1: Import via UI (Recommended)

1. Open n8n at `https://yourdomain.com`
2. Click **+ Add Workflow** (or existing workflow list)
3. Click the **⋯ menu** (top-right) → **Import from File**
4. Select the JSON file (e.g., `wf1-message-handler.json`)
5. The workflow appears with all nodes connected
6. **Update credential IDs**: Click each node that uses credentials → Select your credential from dropdown
7. Click **Save** → Toggle **Active** when ready

## Method 2: Import via API (for Cursor/automation)

```bash
# From VPS terminal:
curl -X POST https://yourdomain.com/api/v1/workflows \
  -H "Content-Type: application/json" \
  -u "admin:password" \
  -d @/opt/stockpulse/n8n-workflows/wf1-message-handler.json
```

## Import Order (recommended)

1. `wf6-token-manager.json` — Kite login (needed first for API access)
2. `wf1-message-handler.json` — Main brain (core bot functionality)
3. `wf2-alert-checker.json` — Price alerts
4. `wf3-pattern-detector.json` — Technical patterns
5. `wf4a-global-data.json` — Global data collector
6. `wf4b-flow-data.json` — FII/DII data
7. `wf4c-technical-data.json` — Technical analysis
8. `wf4d-options-news.json` — Options + news
9. `wf4-morning-briefing.json` — Morning briefing synthesis
10. `wf5-eod-summary.json` — End of day
11. `wf7-weekly-review.json` — Weekly analysis
12. `wf8-prediction-tracker.json` — Prediction tracking

## After Import: Update Credential References

Each workflow JSON has placeholder credential IDs like `POSTGRES_CREDENTIAL_ID`. After importing, click each node that connects to an external service and select the actual credential you created in n8n's credential store.

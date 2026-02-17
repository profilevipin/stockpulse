# Multi-Agent Cursor Build Guide

## How to Use Multiple Cursor Agents in Parallel

Open multiple Cursor windows (or Claude Code terminal tabs), each connected to the same VPS via SSH. Each agent works on independent pieces.

## Phase 1: Infrastructure (1 Agent, Day 1-2)

**Paste to Cursor:**
```
Connect to my VPS at root@[IP]. I need you to deploy StockPulse infrastructure.

Files are in /opt/stockpulse/. Do this:
1. Run: chmod +x setup.sh && ./setup.sh
2. Verify all 3 Docker containers are running
3. Run schema.sql against PostgreSQL
4. Test: curl http://localhost:5000/health
5. Test: open https://[DOMAIN] in browser
```

## Phase 2: Parallel Build (3 Agents, Day 3-7)

### Agent 1: Message Handler
```
I need you to set up n8n workflows for StockPulse. Open https://[DOMAIN] in n8n.

Import wf1-message-handler.json and wf6-token-manager.json.

Then:
1. Create Telegram credential: Bot token [TOKEN]
2. Create PostgreSQL credential: host=postgres, db=stockpulse, user=stockpulse, pass=[PASS]
3. Create HTTP Header Auth for Claude: header "x-api-key" = [CLAUDE_KEY]
4. Create HTTP Header Auth for Kite: header "Authorization" = "token [API_KEY]:[ACCESS_TOKEN]"
5. Update all credential IDs in the workflow nodes
6. Activate WF1
7. Test: send "hello" to the Telegram bot
```

### Agent 2: Alert System
```
Import wf2-alert-checker.json and wf3-pattern-detector.json into n8n.
Connect the same credentials (Postgres, Telegram, Kite).
The Code nodes contain the alert comparison and pattern detection logic.
Activate both workflows.
Test: set an alert via Telegram, then check if WF2 picks it up.
```

### Agent 3: Briefing Pipeline
```
Import wf4a-global-data.json, wf4b-flow-data.json, wf4c-technical-data.json,
wf4d-options-news.json, and wf4-morning-briefing.json into n8n.

Connect credentials. The NSE data service runs at http://nse-data-service:5000
(Docker network name) or http://localhost:5000 from the host.

Test: manually trigger WF4a, check staging_data table has data.
Then manually trigger WF4 to generate a briefing.
```

## Phase 3: Integration (2 Agents, Day 8-10)

### Agent 1: Predictions & Tracking
```
Import wf5-eod-summary.json, wf7-weekly-review.json, wf8-prediction-tracker.json.
Connect credentials. Test: ask for a prediction via Telegram.
```

### Agent 2: Multi-user & Security
```
Add User 2 to the database (see ADDING-USERS.md).
Test CSV upload: send trade-import-template.csv to the bot as User 2.
Verify User 2 sees only their own portfolio.
Test rate limiting: send 31 messages quickly.
```

## Phase 4: Testing (1 Agent, Day 11-12)
```
Run through every command as both users. Test during market hours.
Check: morning briefing arrives at 8:30 AM, alerts trigger correctly,
EOD summary at 3:45 PM, predictions track properly.
Fix any issues found.
```

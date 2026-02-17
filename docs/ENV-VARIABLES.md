# Environment Variables Guide

| Variable | Where to Get It | Example |
|----------|----------------|---------|
| `DOMAIN` | Your domain registrar | `stockpulse.example.com` |
| `N8N_USER` | Choose any username | `admin` |
| `N8N_PASSWORD` | Generate strong password | `xK9!mP2$vL7` |
| `N8N_ENCRYPTION_KEY` | `openssl rand -hex 16` | `a1b2c3d4e5f6...` |
| `POSTGRES_DB` | Keep default | `stockpulse` |
| `POSTGRES_USER` | Keep default | `stockpulse` |
| `POSTGRES_PASSWORD` | Generate strong password | `dB!p4$$w0rd` |
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram | `123456789:ABC...` |
| `KITE_API_KEY_USER1` | developers.kite.trade | `your_api_key` |
| `KITE_API_SECRET_USER1` | developers.kite.trade | `your_api_secret` |
| `CLAUDE_API_KEY` | console.anthropic.com | `sk-ant-api03-...` |
| `NEWSAPI_KEY` | newsapi.org | `abc123...` |
| `FINNHUB_KEY` | finnhub.io | `xyz789...` |
| `ENCRYPTION_KEY` | `openssl rand -hex 32` | `64 hex characters` |

## n8n Credentials (set in n8n UI, NOT in .env)

In n8n UI → Settings → Credentials, create:

1. **Telegram API**: Type "Telegram", paste bot token
2. **PostgreSQL**: Host=`postgres`, Port=5432, Database=`stockpulse`, User/Pass from .env
3. **HTTP Header Auth (Claude)**: Header name=`x-api-key`, Value=Claude API key
4. **HTTP Header Auth (Kite)**: Header name=`Authorization`, Value=`token APIKEY:ACCESSTOKEN`
5. **HTTP Query Auth (Finnhub)**: Query param name=`token`, Value=Finnhub key

Workflow JSONs reference these by credential ID. After creating them, update the IDs in each workflow.

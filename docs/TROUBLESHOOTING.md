# Troubleshooting Guide

## Common Issues

### Bot doesn't respond to messages
1. Check WF1 is active in n8n
2. Check Telegram webhook: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
3. Check n8n logs: `docker compose logs n8n --tail 50`
4. Verify user is in the `users` table with `is_active = true`

### "Unauthorized" response
- User's `telegram_user_id` is not in the `users` table
- Fix: `INSERT INTO users (telegram_user_id, display_name, ...) VALUES (...)`

### Morning briefing not arriving
1. Check WF4a-d and WF4 are all active
2. Check timing: workflows run IST (UTC+5:30), verify server timezone
3. Check staging_data has today's data: `SELECT * FROM staging_data WHERE data_date = CURRENT_DATE`
4. Check NSE service: `curl http://localhost:5000/health`

### Kite API errors
1. Token expires daily. Check WF6 sent login reminder
2. Test token: `curl -H "X-Kite-Version: 3" -H "Authorization: token APIKEY:TOKEN" https://api.kite.trade/user/profile`
3. If expired, login at Zerodha and provide new request_token to bot

### NSE data service down
```bash
docker compose logs nse-data-service --tail 20
docker compose restart nse-data-service
curl http://localhost:5000/health
```

### Database connection issues
```bash
docker compose logs postgres --tail 20
docker exec -it stockpulse-db psql -U stockpulse -d stockpulse -c "SELECT 1"
```

### Alerts not triggering
1. Check WF2 is active
2. Check market hours (9:15-15:30 IST, Mon-Fri)
3. Check alert status: `SELECT * FROM alerts WHERE status = 'active'`
4. Check cooldown: `SELECT * FROM alerts WHERE cooldown_until > NOW()`

### High Claude API costs
- Check n8n execution history for excessive Claude calls
- Morning briefing ~2 calls/day, parser ~1 per message
- Expected: 60-80 calls/day for 2 users = ₹600-1200/month

## Useful Commands

```bash
# Check all services
docker compose ps

# View logs
docker compose logs -f          # All services, follow
docker compose logs n8n --tail 100
docker compose logs postgres --tail 50

# Database access
docker exec -it stockpulse-db psql -U stockpulse -d stockpulse

# Restart everything
docker compose restart

# Full rebuild
docker compose down && docker compose up -d --build
```

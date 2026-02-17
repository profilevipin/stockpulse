# StockPulse Setup Guide

## Prerequisites (You Create These)
1. **VPS**: DigitalOcean 2GB RAM Ubuntu 24.04 ($12/mo)
2. **Domain**: Point A record to VPS IP
3. **Telegram Bot**: Message @BotFather → `/newbot` → copy token (30 seconds)
4. **Kite Connect**: https://developers.kite.trade → Create app → "Connect" plan (₹2,000/mo)
5. **Claude API**: https://console.anthropic.com → Get API key
6. **NewsAPI**: https://newsapi.org → Free signup → Get key
7. **Finnhub**: https://finnhub.io → Free signup → Get key

## Step-by-Step

### 1. SSH into your VPS
```bash
ssh root@your-vps-ip
```

### 2. Clone/upload files
```bash
mkdir -p /opt/stockpulse
cd /opt/stockpulse
# Upload all project files here
```

### 3. Configure environment
```bash
cp .env.example .env
nano .env  # Fill in ALL values
```

### 4. Run setup
```bash
chmod +x setup.sh
./setup.sh
```

### 5. Verify
```bash
docker compose ps  # All 3 services should be "running"
curl http://localhost:5000/health  # NSE service OK
```

### 6. Open n8n
Navigate to `https://yourdomain.com` → Login with N8N_USER/N8N_PASSWORD

### 7. Import workflows
See `docs/IMPORTING-WORKFLOWS.md`

### 8. Configure credentials in n8n
See `docs/ENV-VARIABLES.md`

### 9. Add users
See `docs/ADDING-USERS.md`

### 10. Activate workflows
In n8n, toggle each workflow to Active (start with WF1 and WF6).

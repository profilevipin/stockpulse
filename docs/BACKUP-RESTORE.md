# Backup & Restore Guide

## Automatic Daily Backup

A backup script runs at 4:00 AM daily via cron.

### Setup
```bash
# Make executable
chmod +x /opt/stockpulse/backup.sh

# Add to crontab
crontab -e
# Add this line:
0 4 * * * /opt/stockpulse/backup.sh >> /opt/stockpulse/backups/backup.log 2>&1
```

### What Gets Backed Up
- All PostgreSQL tables (users, trades, alerts, predictions, snapshots, context)
- Compressed with gzip (~50-200KB per backup)
- Stored in `/opt/stockpulse/backups/`
- Last 30 days retained, older auto-deleted

### Verify Backups
```bash
ls -lh /opt/stockpulse/backups/
cat /opt/stockpulse/backups/backup.log | tail -5
```

## Manual Backup
```bash
docker exec stockpulse-db pg_dump -U stockpulse stockpulse > backup-manual.sql
```

## Restore from Backup
```bash
# Stop n8n first (to prevent writes during restore)
docker compose stop n8n

# Restore
gunzip -c /opt/stockpulse/backups/stockpulse-20260217.sql.gz | \
  docker exec -i stockpulse-db psql -U stockpulse -d stockpulse

# Restart
docker compose start n8n
```

## Disaster Recovery (Full Server Loss)
1. Provision new VPS
2. Clone repo / copy stockpulse folder
3. Copy `.env` file (keep this safe separately!)
4. Run `setup.sh`
5. Restore latest backup
6. Re-activate workflows in n8n
7. Re-set Telegram webhook

Keep a copy of your `.env` file in a secure location (password manager, encrypted cloud storage). It contains all your API keys.

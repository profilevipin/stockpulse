#!/bin/bash
# StockPulse — Daily PostgreSQL Backup
# Add to crontab: 0 4 * * * /opt/stockpulse/backup.sh >> /opt/stockpulse/backups/backup.log 2>&1

BACKUP_DIR=/opt/stockpulse/backups
KEEP_DAYS=30

mkdir -p $BACKUP_DIR

echo "[$(date)] Starting backup..."

# Dump PostgreSQL
docker exec stockpulse-db pg_dump -U stockpulse stockpulse | gzip > $BACKUP_DIR/stockpulse-$(date +%Y%m%d).sql.gz

if [ $? -eq 0 ]; then
    SIZE=$(du -h $BACKUP_DIR/stockpulse-$(date +%Y%m%d).sql.gz | cut -f1)
    echo "[$(date)] Backup successful: stockpulse-$(date +%Y%m%d).sql.gz ($SIZE)"
else
    echo "[$(date)] ERROR: Backup failed!"
    exit 1
fi

# Cleanup old backups
DELETED=$(find $BACKUP_DIR -name "*.sql.gz" -mtime +$KEEP_DAYS -delete -print | wc -l)
echo "[$(date)] Cleaned up $DELETED old backups (older than $KEEP_DAYS days)"

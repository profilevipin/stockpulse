#!/bin/bash
# Deploy StockPulse to droplet. Run from repo root on your Mac.
# You will be prompted for the droplet password.

set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
HOST="stockpulse"
DEST="/opt/stockpulse"

echo "Deploying from $REPO_ROOT to $HOST:$DEST"
ssh $HOST "mkdir -p $DEST"
rsync -avz --exclude='.git' --exclude='.env' --exclude='backups' -e ssh "$REPO_ROOT/" $HOST:$DEST/
echo "Done. Next on droplet: cd $DEST && cp .env.example .env && edit .env, then ./setup.sh"
echo "See docs/SETUP-GUIDE.md and docs/ENV-VARIABLES.md"

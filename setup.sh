#!/bin/bash
# StockPulse v3.2 — One-Command Setup
set -e

echo "🚀 StockPulse Setup Starting..."

# Check .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Copy .env.example to .env and fill in values."
    exit 1
fi

source .env

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

# Install Docker Compose plugin if not present
if ! docker compose version &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

# Install Caddy if not present
if ! command -v caddy &> /dev/null; then
    echo "📦 Installing Caddy..."
    sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt update && sudo apt install -y caddy
fi

# Start Docker services
echo "🐳 Starting Docker containers..."
docker compose up -d --build

# Wait for Postgres to be ready
echo "⏳ Waiting for PostgreSQL..."
sleep 10

# Run schema
echo "🗄️ Creating database schema..."
docker exec -i stockpulse-db psql -U $POSTGRES_USER -d $POSTGRES_DB < schema.sql

# Configure Caddy
echo "🔒 Configuring HTTPS..."
export DOMAIN=$DOMAIN
sudo cp Caddyfile /etc/caddy/Caddyfile
sudo sed -i "s/\$DOMAIN/$DOMAIN/g" /etc/caddy/Caddyfile
sudo systemctl restart caddy

# Verify services
echo ""
echo "✅ Checking services..."
echo -n "  n8n:      "; docker inspect --format='{{.State.Status}}' stockpulse-n8n 2>/dev/null || echo "not running"
echo -n "  postgres: "; docker inspect --format='{{.State.Status}}' stockpulse-db 2>/dev/null || echo "not running"
echo -n "  nse-data: "; docker inspect --format='{{.State.Status}}' stockpulse-nse 2>/dev/null || echo "not running"

echo ""
echo "🎉 StockPulse is running!"
echo "   n8n UI:  https://$DOMAIN"
echo "   Login:   $N8N_USER / $N8N_PASSWORD"
echo ""
echo "📋 Next steps:"
echo "   1. Open https://$DOMAIN in your browser"
echo "   2. Import workflow JSONs from n8n-workflows/ folder"
echo "   3. Add API credentials in n8n Credentials section"
echo "   4. Add users to the database (see docs/ADDING-USERS.md)"
echo "   5. Activate workflows"

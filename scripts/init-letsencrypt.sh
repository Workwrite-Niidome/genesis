#!/bin/bash
# Initial Let's Encrypt certificate acquisition for GENESIS
# Usage: ./scripts/init-letsencrypt.sh

set -e

if [ -z "$DOMAIN" ] || [ -z "$ACME_EMAIL" ]; then
  if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
  fi
fi

if [ -z "$DOMAIN" ]; then
  echo "Error: DOMAIN not set. Set it in .env or as environment variable."
  exit 1
fi

if [ -z "$ACME_EMAIL" ]; then
  echo "Error: ACME_EMAIL not set. Set it in .env or as environment variable."
  exit 1
fi

CERTBOT_DIR="./certbot"
DATA_PATH="$CERTBOT_DIR/conf"
WWW_PATH="$CERTBOT_DIR/www"

echo "### Creating directories..."
mkdir -p "$DATA_PATH"
mkdir -p "$WWW_PATH"

# Check if certificate already exists
if [ -d "$DATA_PATH/live/$DOMAIN" ]; then
  echo "Certificate already exists for $DOMAIN."
  read -p "Replace existing certificate? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit 0
  fi
fi

echo "### Downloading recommended TLS parameters..."
mkdir -p "$DATA_PATH"
curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$DATA_PATH/options-ssl-nginx.conf"
curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$DATA_PATH/ssl-dhparams.pem"

echo "### Creating dummy certificate for $DOMAIN..."
LIVE_PATH="$DATA_PATH/live/$DOMAIN"
mkdir -p "$LIVE_PATH"
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout "$LIVE_PATH/privkey.pem" \
  -out "$LIVE_PATH/fullchain.pem" \
  -subj "/CN=localhost"

echo "### Starting nginx with dummy certificate..."
docker compose -f docker-compose.prod.yml up -d nginx

echo "### Removing dummy certificate..."
rm -rf "$LIVE_PATH"

echo "### Requesting real certificate for $DOMAIN..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "$ACME_EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

echo "### Reloading nginx..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "### Done! SSL certificate obtained for $DOMAIN"

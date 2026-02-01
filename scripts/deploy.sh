#!/bin/bash
# GENESIS production deployment script
# Usage: ./scripts/deploy.sh

set -e

COMPOSE_FILE="docker-compose.prod.yml"

echo "=== GENESIS Deploy ==="
echo "$(date '+%Y-%m-%d %H:%M:%S')"

# Pull latest code
echo "### Pulling latest code..."
git pull origin main

# Build frontend first (for nginx to copy dist/)
echo "### Building frontend..."
cd frontend
npm ci
npm run build
cd ..

# Build and restart services
echo "### Building Docker images..."
docker compose -f "$COMPOSE_FILE" build

# Run database migrations
echo "### Running database migrations..."
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head

# Restart services with zero-downtime approach
echo "### Restarting services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# Clean up old images
echo "### Cleaning up..."
docker image prune -f

echo "### Waiting for services to be healthy..."
sleep 5

# Health check
echo "### Health check..."
if docker compose -f "$COMPOSE_FILE" ps | grep -q "unhealthy\|Exit"; then
  echo "WARNING: Some services may not be healthy!"
  docker compose -f "$COMPOSE_FILE" ps
  exit 1
fi

echo "=== Deploy complete! ==="
docker compose -f "$COMPOSE_FILE" ps

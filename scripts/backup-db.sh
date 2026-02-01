#!/bin/bash
# GENESIS database backup script
# Usage: ./scripts/backup-db.sh [backup_dir]

set -e

COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/genesis_${TIMESTAMP}.sql.gz"

# Load env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

DB_USER="${POSTGRES_USER:-genesis}"
DB_NAME="${POSTGRES_DB:-genesis}"

echo "=== GENESIS Database Backup ==="
echo "$(date '+%Y-%m-%d %H:%M:%S')"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Dump and compress
echo "### Dumping database $DB_NAME..."
docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl \
  | gzip > "$BACKUP_FILE"

# Get file size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "### Backup saved: $BACKUP_FILE ($SIZE)"

# Keep only last 7 backups
echo "### Pruning old backups (keeping last 7)..."
ls -t "$BACKUP_DIR"/genesis_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -v

echo "=== Backup complete! ==="

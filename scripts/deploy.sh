#!/bin/bash
# GENESIS v3 — Production Deployment Script
# Usage:
#   ./scripts/deploy.sh              # defaults to production
#   ./scripts/deploy.sh staging      # deploy to staging
#   ./scripts/deploy.sh production   # deploy to production

set -euo pipefail

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
ENVIRONMENT="${1:-production}"
COMPOSE_FILE="docker-compose.prod.yml"

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    error "Invalid environment: $ENVIRONMENT"
    echo "Usage: $0 [staging|production]"
    exit 1
fi

# ---------------------------------------------------------------------------
# Resolve project root
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}   GENESIS v3 — ${ENVIRONMENT^^} Deployment${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "  Timestamp : $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Directory : $PROJECT_ROOT"
echo "  Compose   : $COMPOSE_FILE"
echo ""

# Check .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    error ".env file not found. Copy .env.example and configure it:"
    echo "  cp .env.example .env && nano .env"
    exit 1
fi

# Check Docker is available
if ! command -v docker &>/dev/null; then
    error "Docker is not installed or not in PATH."
    exit 1
fi

# Check docker compose is available
if ! docker compose version &>/dev/null; then
    error "Docker Compose v2 is not available."
    exit 1
fi

# Warn about default secret key
if grep -q "change-this-to-a-random-secret-key" "$PROJECT_ROOT/.env" 2>/dev/null; then
    error "SECRET_KEY is still the default value! Change it in .env before deploying."
    exit 1
fi

# Warn about default admin password
if grep -q "change-this-password" "$PROJECT_ROOT/.env" 2>/dev/null; then
    warn "ADMIN_PASSWORD is still the default value. Consider changing it."
fi

success "Pre-flight checks passed"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Pull latest code (if git repo)
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 1/5: Pull latest code ---${NC}"

if [ -d "$PROJECT_ROOT/.git" ]; then
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    info "Current branch: $CURRENT_BRANCH"

    if [[ "$ENVIRONMENT" == "production" && "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
        warn "Deploying to production from branch '$CURRENT_BRANCH' (not main/master)"
        read -rp "Continue? [y/N] " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            echo "Aborted."
            exit 1
        fi
    fi

    info "Pulling latest changes..."
    git pull origin "$CURRENT_BRANCH"
    COMMIT_HASH=$(git rev-parse --short HEAD)
    success "Updated to commit $COMMIT_HASH"
else
    warn "Not a git repository — skipping pull"
fi

echo ""

# ---------------------------------------------------------------------------
# Step 2: Build Docker images
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 2/5: Build Docker images ---${NC}"

info "Building all services..."
docker compose -f "$COMPOSE_FILE" build --parallel

success "Docker images built"
echo ""

# ---------------------------------------------------------------------------
# Step 3: Run database migrations
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 3/5: Database migrations ---${NC}"

info "Starting database service..."
docker compose -f "$COMPOSE_FILE" up -d db

# Wait for database to be healthy
info "Waiting for database to be healthy..."
RETRIES=30
until docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "${POSTGRES_USER:-genesis}" &>/dev/null || [ "$RETRIES" -eq 0 ]; do
    ((RETRIES--))
    sleep 2
done

if [ "$RETRIES" -eq 0 ]; then
    error "Database did not become healthy in time."
    exit 1
fi

info "Running Alembic migrations..."
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head

success "Database migrations applied"
echo ""

# ---------------------------------------------------------------------------
# Step 4: Deploy services
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 4/5: Deploy services ---${NC}"

info "Starting all services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

success "All services started"
echo ""

# ---------------------------------------------------------------------------
# Step 5: Verify deployment
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 5/5: Verify deployment ---${NC}"

info "Waiting for services to initialize (15s)..."
sleep 15

# Check service health
UNHEALTHY=0

check_service() {
    local service="$1"
    local status
    status=$(docker compose -f "$COMPOSE_FILE" ps --format json "$service" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    data = data[0] if data else {}
print(data.get('Health', data.get('State', 'unknown')))
" 2>/dev/null || echo "unknown")

    if [[ "$status" == *"healthy"* ]] || [[ "$status" == "running" ]]; then
        success "$service: $status"
    else
        warn "$service: $status"
        ((UNHEALTHY++)) || true
    fi
}

for svc in db redis backend celery-worker celery-beat nginx; do
    check_service "$svc"
done

echo ""

# Clean up old images
info "Cleaning up unused Docker images..."
docker image prune -f --filter "until=24h" 2>/dev/null || true

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
if [ "$UNHEALTHY" -eq 0 ]; then
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}   Deployment successful!${NC}"
    echo -e "${GREEN}============================================${NC}"
else
    echo -e "${YELLOW}============================================${NC}"
    echo -e "${YELLOW}   Deployment complete with warnings${NC}"
    echo -e "${YELLOW}   $UNHEALTHY service(s) not yet healthy${NC}"
    echo -e "${YELLOW}============================================${NC}"
fi

echo ""
echo "  Environment : $ENVIRONMENT"
echo "  Timestamp   : $(date '+%Y-%m-%d %H:%M:%S %Z')"
if [ -d "$PROJECT_ROOT/.git" ]; then
    echo "  Commit      : $(git rev-parse --short HEAD) ($(git log -1 --format='%s' 2>/dev/null))"
fi
echo ""
echo "  Service status:"
docker compose -f "$COMPOSE_FILE" ps
echo ""

exit "$UNHEALTHY"

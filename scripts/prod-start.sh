#!/bin/bash
# =============================================================================
# GENESIS v3 — Production Start Script
# =============================================================================
# Starts the full backend stack and optionally the Cloudflare tunnel.
#
# Usage:
#   chmod +x scripts/prod-start.sh
#   ./scripts/prod-start.sh             # start backend only
#   ./scripts/prod-start.sh --tunnel    # start backend + cloudflare tunnel
# =============================================================================

set -euo pipefail

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

START_TUNNEL=false
if [[ "${1:-}" == "--tunnel" ]]; then
    START_TUNNEL=true
fi

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}   GENESIS v3 — Production Start${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "  Timestamp : $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Directory : $PROJECT_ROOT"
echo "  Tunnel    : $START_TUNNEL"
echo ""

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    error ".env file not found. Copy .env.example and configure it:"
    echo "  cp .env.example .env && nano .env"
    exit 1
fi

if ! command -v docker &>/dev/null; then
    error "Docker is not installed or not in PATH."
    exit 1
fi

if ! docker compose version &>/dev/null; then
    error "Docker Compose v2 is not available."
    exit 1
fi

success "Pre-flight checks passed"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Start all backend services
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 1/4: Start Docker services ---${NC}"

info "Starting all services with production compose..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

success "Docker services started"
echo ""

# ---------------------------------------------------------------------------
# Step 2: Wait for database to be healthy
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 2/4: Wait for database ---${NC}"

info "Waiting for database to become healthy..."
RETRIES=30
until docker compose -f docker-compose.prod.yml exec -T db pg_isready -U "${POSTGRES_USER:-genesis}" &>/dev/null || [ "$RETRIES" -eq 0 ]; do
    ((RETRIES--))
    sleep 2
done

if [ "$RETRIES" -eq 0 ]; then
    error "Database did not become healthy in time."
    docker compose -f docker-compose.prod.yml logs db --tail 20
    exit 1
fi

success "Database is healthy"
echo ""

# ---------------------------------------------------------------------------
# Step 3: Run database migrations
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 3/4: Run migrations ---${NC}"

info "Running Alembic migrations..."
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

success "Migrations applied"
echo ""

# ---------------------------------------------------------------------------
# Step 4: Start Cloudflare Tunnel (optional)
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 4/4: Cloudflare Tunnel ---${NC}"

if [ "$START_TUNNEL" = true ]; then
    if command -v cloudflared &>/dev/null; then
        # Check if tunnel is already running as a service
        if systemctl is-active --quiet cloudflared 2>/dev/null; then
            success "Cloudflare tunnel is already running as a system service"
        else
            info "Starting Cloudflare tunnel..."
            cloudflared tunnel run genesis-backend &
            TUNNEL_PID=$!
            info "Cloudflare tunnel started (PID: $TUNNEL_PID)"
            success "Tunnel running: api.genesis-pj.net -> localhost:8000"
        fi
    else
        warn "cloudflared is not installed. Run scripts/setup-tunnel.sh first."
    fi
else
    info "Skipping tunnel start (use --tunnel flag to start)"
    info "If cloudflared is installed as a service, it runs independently."
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   GENESIS v3 Production — Running${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

docker compose -f docker-compose.prod.yml ps

echo ""
echo "  Useful commands:"
echo "    docker compose -f docker-compose.prod.yml logs -f backend    # backend logs"
echo "    docker compose -f docker-compose.prod.yml logs -f            # all logs"
echo "    docker compose -f docker-compose.prod.yml restart backend    # restart backend"
echo "    docker compose -f docker-compose.prod.yml down               # stop all"
echo ""
echo "  Health check:"
echo "    curl http://localhost:8000/docs"
echo "    curl https://api.genesis-pj.net/docs"
echo ""

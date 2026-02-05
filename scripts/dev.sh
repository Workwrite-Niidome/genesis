#!/bin/bash
# GENESIS v3 — Local Development Runner
# Usage: ./scripts/dev.sh
#
# Starts all services required for local development:
#   - Redis, PostgreSQL, Ollama (checks / starts)
#   - FastAPI backend (uvicorn)
#   - Celery worker + beat
#   - Vite frontend dev server
#
# Press Ctrl+C to stop everything gracefully.

set -e

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
# Resolve project root
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source <(grep -v '^\s*#' "$PROJECT_ROOT/.env" | grep -v '^\s*$')
    set +a
else
    warn ".env not found — using default values. Run ./scripts/setup.sh first."
fi

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
VENV_DIR="$PROJECT_ROOT/backend/venv"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
OLLAMA_HOST_URL="${OLLAMA_HOST:-http://localhost:11434}"

# PIDs we need to clean up
PIDS=()

# ---------------------------------------------------------------------------
# Cleanup on exit
# ---------------------------------------------------------------------------
cleanup() {
    echo ""
    info "Shutting down GENESIS dev services ..."

    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done

    # Give processes a moment to exit, then force-kill stragglers
    sleep 1
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done

    success "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# ---------------------------------------------------------------------------
# Pre-flight: virtual environment
# ---------------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    error "Python virtual environment not found at $VENV_DIR"
    error "Run ./scripts/setup.sh first."
    exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}     GENESIS v3 — Development Server${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ---------------------------------------------------------------------------
# 1. Check / start Redis
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Checking infrastructure ---${NC}"

if redis-cli ping &>/dev/null; then
    success "Redis is running"
else
    info "Redis is not running — attempting to start ..."
    if command -v redis-server &>/dev/null; then
        redis-server --daemonize yes --loglevel warning
        sleep 1
        if redis-cli ping &>/dev/null; then
            success "Redis started"
        else
            error "Failed to start Redis"
            exit 1
        fi
    elif command -v docker &>/dev/null; then
        info "Starting Redis via Docker ..."
        docker run -d --name genesis-redis -p 6379:6379 redis:7-alpine &>/dev/null || \
            docker start genesis-redis &>/dev/null || true
        sleep 2
        if redis-cli ping &>/dev/null; then
            success "Redis started (Docker)"
        else
            error "Failed to start Redis — install Redis or start it manually"
            exit 1
        fi
    else
        error "Redis not running and no way to start it. Install Redis or Docker."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# 2. Check PostgreSQL
# ---------------------------------------------------------------------------
DB_USER="${POSTGRES_USER:-genesis}"
DB_PASS="${POSTGRES_PASSWORD:-genesis}"
DB_NAME="${POSTGRES_DB:-genesis}"
DB_HOST="localhost"
DB_PORT="5432"

if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
    success "PostgreSQL is running (database '$DB_NAME' accessible)"
else
    error "Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT"
    error "Make sure PostgreSQL is running. You can use Docker:"
    echo -e "  ${YELLOW}docker compose -f docker-compose.dev.yml up -d db${NC}"
    exit 1
fi

# ---------------------------------------------------------------------------
# 3. Check / start Ollama
# ---------------------------------------------------------------------------
if curl -sf "${OLLAMA_HOST_URL}/api/tags" &>/dev/null; then
    success "Ollama is running at $OLLAMA_HOST_URL"
else
    if command -v ollama &>/dev/null; then
        info "Ollama is not running — starting in background ..."
        ollama serve &>/dev/null &
        OLLAMA_PID=$!
        PIDS+=("$OLLAMA_PID")
        # Wait for Ollama to be ready
        for i in $(seq 1 10); do
            if curl -sf "${OLLAMA_HOST_URL}/api/tags" &>/dev/null; then
                break
            fi
            sleep 1
        done
        if curl -sf "${OLLAMA_HOST_URL}/api/tags" &>/dev/null; then
            success "Ollama started (PID $OLLAMA_PID)"
        else
            warn "Ollama started but not yet responding — it may need more time"
        fi
    else
        warn "Ollama not installed — local LLM features will be unavailable"
    fi
fi

echo ""

# ---------------------------------------------------------------------------
# 4. Start FastAPI backend (uvicorn with reload)
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Starting application services ---${NC}"

info "Starting FastAPI backend ..."
(
    cd "$BACKEND_DIR"
    uvicorn app.main:app \
        --host "$BACKEND_HOST" \
        --port "$BACKEND_PORT" \
        --reload \
        --log-level info
) &
BACKEND_PID=$!
PIDS+=("$BACKEND_PID")
success "Backend starting (PID $BACKEND_PID) on port $BACKEND_PORT"

# ---------------------------------------------------------------------------
# 5. Start Celery worker
# ---------------------------------------------------------------------------
info "Starting Celery worker ..."
(
    cd "$BACKEND_DIR"
    celery -A app.core.celery_app worker \
        --loglevel=info \
        --concurrency=1 \
        --pool=solo
) &
CELERY_WORKER_PID=$!
PIDS+=("$CELERY_WORKER_PID")
success "Celery worker starting (PID $CELERY_WORKER_PID)"

# ---------------------------------------------------------------------------
# 6. Start Celery beat
# ---------------------------------------------------------------------------
info "Starting Celery beat scheduler ..."
(
    cd "$BACKEND_DIR"
    celery -A app.core.celery_app beat \
        --loglevel=info
) &
CELERY_BEAT_PID=$!
PIDS+=("$CELERY_BEAT_PID")
success "Celery beat starting (PID $CELERY_BEAT_PID)"

# ---------------------------------------------------------------------------
# 7. Start frontend dev server
# ---------------------------------------------------------------------------
info "Starting Vite frontend dev server ..."
(
    cd "$FRONTEND_DIR"
    npm run dev
) &
FRONTEND_PID=$!
PIDS+=("$FRONTEND_PID")
success "Frontend starting (PID $FRONTEND_PID) on port $FRONTEND_PORT"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}      All services are starting up!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  ${CYAN}Backend API${NC}  : http://localhost:${BACKEND_PORT}"
echo -e "  ${CYAN}API Docs${NC}     : http://localhost:${BACKEND_PORT}/docs"
echo -e "  ${CYAN}Frontend${NC}     : http://localhost:${FRONTEND_PORT}"
echo -e "  ${CYAN}Ollama${NC}       : ${OLLAMA_HOST_URL}"
echo -e "  ${CYAN}PostgreSQL${NC}   : localhost:${DB_PORT}"
echo -e "  ${CYAN}Redis${NC}        : localhost:6379"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services."
echo ""

# ---------------------------------------------------------------------------
# Wait for Ctrl+C
# ---------------------------------------------------------------------------
wait

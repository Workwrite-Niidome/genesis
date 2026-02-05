#!/bin/bash
# GENESIS v3 — Service Health Check
# Usage: ./scripts/healthcheck.sh
#
# Checks whether each service required by GENESIS is running and responsive.
# Returns exit code 0 if all critical services are healthy, 1 otherwise.

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

PASS="${GREEN}PASS${NC}"
FAIL="${RED}FAIL${NC}"
WARN="${YELLOW}WARN${NC}"

# ---------------------------------------------------------------------------
# Resolve project root and load .env
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source <(grep -v '^\s*#' "$PROJECT_ROOT/.env" | grep -v '^\s*$')
    set +a
fi

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DB_USER="${POSTGRES_USER:-genesis}"
DB_PASS="${POSTGRES_PASSWORD:-genesis}"
DB_NAME="${POSTGRES_DB:-genesis}"
DB_HOST="localhost"
DB_PORT="5432"

REDIS_HOST="localhost"
REDIS_PORT="6379"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

OLLAMA_HOST_URL="${OLLAMA_HOST:-http://localhost:11434}"
# Normalise: if the URL contains host.docker.internal, use localhost instead
OLLAMA_HOST_URL="${OLLAMA_HOST_URL//host.docker.internal/localhost}"

FAILURES=0

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}     GENESIS v3 — Health Check${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ---------------------------------------------------------------------------
# Helper: print result row
# ---------------------------------------------------------------------------
check_result() {
    local label="$1"
    local status="$2"  # pass | fail | warn
    local detail="${3:-}"

    case "$status" in
        pass) printf "  %-22s [${PASS}]  %s\n" "$label" "$detail" ;;
        fail) printf "  %-22s [${FAIL}]  %s\n" "$label" "$detail"; ((FAILURES++)) ;;
        warn) printf "  %-22s [${WARN}]  %s\n" "$label" "$detail" ;;
    esac
}

# ---------------------------------------------------------------------------
# 1. PostgreSQL
# ---------------------------------------------------------------------------
if command -v psql &>/dev/null; then
    if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &>/dev/null; then
        PG_VER=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SHOW server_version" 2>/dev/null)
        check_result "PostgreSQL" "pass" "v${PG_VER} — ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    else
        check_result "PostgreSQL" "fail" "Cannot connect to ${DB_HOST}:${DB_PORT}"
    fi
else
    # Try connection via docker
    if docker exec genesis-db pg_isready -U "$DB_USER" &>/dev/null 2>&1; then
        check_result "PostgreSQL" "pass" "via Docker container"
    else
        check_result "PostgreSQL" "fail" "psql not installed and Docker container not running"
    fi
fi

# ---------------------------------------------------------------------------
# 2. Redis
# ---------------------------------------------------------------------------
if command -v redis-cli &>/dev/null; then
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; then
        REDIS_VER=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info server 2>/dev/null | grep redis_version | cut -d: -f2 | tr -d '\r')
        check_result "Redis" "pass" "v${REDIS_VER} — ${REDIS_HOST}:${REDIS_PORT}"
    else
        check_result "Redis" "fail" "Cannot connect to ${REDIS_HOST}:${REDIS_PORT}"
    fi
else
    # Fallback: try a raw TCP connection
    if (echo PING | timeout 2 bash -c "cat > /dev/tcp/$REDIS_HOST/$REDIS_PORT" 2>/dev/null); then
        check_result "Redis" "pass" "${REDIS_HOST}:${REDIS_PORT} (tcp reachable)"
    else
        check_result "Redis" "fail" "redis-cli not found and port ${REDIS_PORT} not reachable"
    fi
fi

# ---------------------------------------------------------------------------
# 3. Ollama
# ---------------------------------------------------------------------------
if curl -sf --max-time 3 "${OLLAMA_HOST_URL}/api/tags" &>/dev/null; then
    MODEL_COUNT=$(curl -sf --max-time 3 "${OLLAMA_HOST_URL}/api/tags" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "?")
    check_result "Ollama" "pass" "${OLLAMA_HOST_URL} — ${MODEL_COUNT} model(s) available"
else
    check_result "Ollama" "warn" "Not responding at ${OLLAMA_HOST_URL}"
fi

# ---------------------------------------------------------------------------
# 4. Backend API
# ---------------------------------------------------------------------------
BACKEND_URL="http://localhost:${BACKEND_PORT}"

if curl -sf --max-time 5 "${BACKEND_URL}/docs" &>/dev/null; then
    # Try to get a health or root endpoint
    HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" --max-time 5 "${BACKEND_URL}/docs" 2>/dev/null || echo "000")
    check_result "Backend API" "pass" "${BACKEND_URL} — HTTP ${HTTP_CODE}"
elif curl -sf --max-time 5 "${BACKEND_URL}/" &>/dev/null; then
    HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" --max-time 5 "${BACKEND_URL}/" 2>/dev/null || echo "000")
    check_result "Backend API" "pass" "${BACKEND_URL} — HTTP ${HTTP_CODE}"
else
    check_result "Backend API" "fail" "Not responding at ${BACKEND_URL}"
fi

# ---------------------------------------------------------------------------
# 5. Frontend
# ---------------------------------------------------------------------------
FRONTEND_URL="http://localhost:${FRONTEND_PORT}"

if curl -sf --max-time 5 "${FRONTEND_URL}/" &>/dev/null; then
    check_result "Frontend" "pass" "${FRONTEND_URL}"
else
    check_result "Frontend" "fail" "Not responding at ${FRONTEND_URL}"
fi

# ---------------------------------------------------------------------------
# 6. Celery worker
# ---------------------------------------------------------------------------
# Check if any celery worker process is running
if pgrep -f "celery.*worker" &>/dev/null; then
    WORKER_PIDS=$(pgrep -f "celery.*worker" | head -3 | tr '\n' ' ')
    check_result "Celery Worker" "pass" "PID(s): ${WORKER_PIDS}"
else
    # Alternative: try celery inspect (requires running worker + broker)
    VENV_DIR="$PROJECT_ROOT/backend/venv"
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "$VENV_DIR/bin/activate"
        if (cd "$PROJECT_ROOT/backend" && timeout 5 celery -A app.core.celery_app inspect ping 2>/dev/null | grep -q "pong"); then
            check_result "Celery Worker" "pass" "Responding to ping"
        else
            check_result "Celery Worker" "fail" "No worker process detected"
        fi
        deactivate 2>/dev/null || true
    else
        check_result "Celery Worker" "fail" "No worker process detected"
    fi
fi

# ---------------------------------------------------------------------------
# 7. Celery beat
# ---------------------------------------------------------------------------
if pgrep -f "celery.*beat" &>/dev/null; then
    BEAT_PID=$(pgrep -f "celery.*beat" | head -1)
    check_result "Celery Beat" "pass" "PID: ${BEAT_PID}"
else
    check_result "Celery Beat" "fail" "No beat scheduler process detected"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""

if [ "$FAILURES" -eq 0 ]; then
    echo -e "  ${GREEN}All critical services are healthy.${NC}"
else
    echo -e "  ${RED}${FAILURES} service(s) not healthy.${NC}"
fi

echo ""
echo -e "${CYAN}============================================${NC}"
echo ""

exit "$FAILURES"

#!/bin/bash
# GENESIS v3 — Full Initial Setup Script
# Usage: ./scripts/setup.sh
#
# This script prepares a fresh development environment by:
#   1. Checking all prerequisites
#   2. Creating .env from .env.example
#   3. Setting up Python venv and installing backend dependencies
#   4. Installing frontend (Node) dependencies
#   5. Pulling the Ollama model
#   6. Creating the PostgreSQL database
#   7. Running Alembic migrations

set -e

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# Resolve project root (parent of scripts/)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}       GENESIS v3 — Initial Setup${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# ---------------------------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 1/7: Checking prerequisites ---${NC}"

MISSING=0

# Python 3.11+
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        success "Python $PY_VERSION"
    else
        error "Python 3.11+ required (found $PY_VERSION)"
        MISSING=1
    fi
else
    error "Python 3 not found — install Python 3.11+"
    MISSING=1
fi

# Node.js 18+
if command -v node &>/dev/null; then
    NODE_VERSION=$(node -v | sed 's/^v//')
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        success "Node.js $NODE_VERSION"
    else
        error "Node.js 18+ required (found $NODE_VERSION)"
        MISSING=1
    fi
else
    error "Node.js not found — install Node.js 18+"
    MISSING=1
fi

# npm
if command -v npm &>/dev/null; then
    success "npm $(npm -v)"
else
    error "npm not found"
    MISSING=1
fi

# Docker
if command -v docker &>/dev/null; then
    success "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
else
    warn "Docker not found — only needed for docker-compose workflows"
fi

# Redis
if command -v redis-cli &>/dev/null; then
    success "redis-cli found"
else
    warn "redis-cli not found — make sure Redis is reachable at localhost:6379"
fi

# PostgreSQL client (psql)
if command -v psql &>/dev/null; then
    success "psql $(psql --version | awk '{print $3}')"
else
    warn "psql not found — make sure PostgreSQL is reachable at localhost:5432"
fi

# Ollama
if command -v ollama &>/dev/null; then
    success "Ollama found"
else
    warn "Ollama not found — install from https://ollama.ai if you need local LLM"
fi

if [ "$MISSING" -ne 0 ]; then
    echo ""
    error "Missing required prerequisites. Please install them and re-run this script."
    exit 1
fi

echo ""

# ---------------------------------------------------------------------------
# 2. Create .env from .env.example
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 2/7: Environment file ---${NC}"

if [ -f "$PROJECT_ROOT/.env" ]; then
    success ".env already exists — skipping creation"
else
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        # For local dev, rewrite Docker-internal hostnames to localhost
        sed \
            -e 's|@db:|@localhost:|g' \
            -e 's|://redis:|://localhost:|g' \
            -e 's|host.docker.internal|localhost|g' \
            "$PROJECT_ROOT/.env.example" > "$PROJECT_ROOT/.env"
        success "Created .env from .env.example (hostnames adjusted for local dev)"
        warn "Please review and edit .env — especially ANTHROPIC_API_KEY and SECRET_KEY"
        echo ""
        echo -e "  ${YELLOW}nano $PROJECT_ROOT/.env${NC}"
        echo ""
        read -rp "Press Enter after you have reviewed .env (or Ctrl+C to abort)..."
    else
        error ".env.example not found — cannot create .env"
        exit 1
    fi
fi

echo ""

# ---------------------------------------------------------------------------
# 3. Python virtual environment + backend dependencies
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 3/7: Python virtual environment & backend deps ---${NC}"

VENV_DIR="$PROJECT_ROOT/backend/venv"

if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment at backend/venv ..."
    python3 -m venv "$VENV_DIR"
    success "Virtual environment created"
else
    success "Virtual environment already exists"
fi

info "Installing backend dependencies ..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$PROJECT_ROOT/backend/requirements.txt" --quiet
success "Backend dependencies installed"
deactivate

echo ""

# ---------------------------------------------------------------------------
# 4. Frontend dependencies
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 4/7: Frontend dependencies ---${NC}"

if [ -f "$PROJECT_ROOT/frontend/package.json" ]; then
    info "Running npm install in frontend/ ..."
    (cd "$PROJECT_ROOT/frontend" && npm install --no-audit --no-fund)
    success "Frontend dependencies installed"
else
    error "frontend/package.json not found"
    exit 1
fi

echo ""

# ---------------------------------------------------------------------------
# 5. Pull Ollama model
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 5/7: Ollama model ---${NC}"

if command -v ollama &>/dev/null; then
    MODEL="llama3.1:8b"
    info "Pulling Ollama model: $MODEL (this may take a while) ..."
    if ollama pull "$MODEL"; then
        success "Ollama model $MODEL ready"
    else
        warn "Could not pull Ollama model — is the Ollama daemon running?"
        warn "Start it with: ollama serve"
    fi
else
    warn "Ollama not installed — skipping model pull"
fi

echo ""

# ---------------------------------------------------------------------------
# 6. Create PostgreSQL database
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 6/7: PostgreSQL database ---${NC}"

# Source .env for DB credentials
if [ -f "$PROJECT_ROOT/.env" ]; then
    DB_USER=$(grep -E '^POSTGRES_USER=' "$PROJECT_ROOT/.env" | cut -d= -f2)
    DB_PASS=$(grep -E '^POSTGRES_PASSWORD=' "$PROJECT_ROOT/.env" | cut -d= -f2)
    DB_NAME=$(grep -E '^POSTGRES_DB=' "$PROJECT_ROOT/.env" | cut -d= -f2)
fi

DB_USER="${DB_USER:-genesis}"
DB_PASS="${DB_PASS:-genesis}"
DB_NAME="${DB_NAME:-genesis}"
DB_HOST="localhost"
DB_PORT="5432"

if command -v psql &>/dev/null; then
    # Check if PostgreSQL is reachable
    if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c '\q' 2>/dev/null; then
        # Check if database exists
        DB_EXISTS=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc \
            "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null)
        if [ "$DB_EXISTS" = "1" ]; then
            success "Database '$DB_NAME' already exists"
        else
            info "Creating database '$DB_NAME' ..."
            PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
                -c "CREATE DATABASE $DB_NAME;" 2>/dev/null
            success "Database '$DB_NAME' created"
        fi
    else
        warn "Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT"
        warn "Make sure PostgreSQL is running and user '$DB_USER' exists"
        warn "You can start it via Docker:  docker compose -f docker-compose.dev.yml up -d db"
    fi
else
    warn "psql not available — skipping database creation"
    warn "Ensure the database '$DB_NAME' exists before running migrations"
fi

echo ""

# ---------------------------------------------------------------------------
# 7. Run Alembic migrations
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 7/7: Database migrations ---${NC}"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [ -f "$PROJECT_ROOT/backend/alembic.ini" ]; then
    # Override alembic DB URL to point at localhost for local dev
    ALEMBIC_DB_URL="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    info "Running Alembic migrations ..."
    if (cd "$PROJECT_ROOT/backend" && alembic upgrade head -x "sqlalchemy.url=$ALEMBIC_DB_URL" 2>/dev/null) || \
       (cd "$PROJECT_ROOT/backend" && SQLALCHEMY_URL="$ALEMBIC_DB_URL" alembic upgrade head 2>/dev/null); then
        success "Migrations applied"
    else
        warn "Alembic migrations could not run — you may need to run them manually:"
        warn "  cd backend && alembic upgrade head"
    fi
else
    warn "backend/alembic.ini not found — skipping migrations"
fi

deactivate

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}       GENESIS v3 — Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  ${CYAN}Next steps:${NC}"
echo ""
echo -e "  1. Review your .env file:"
echo -e "     ${YELLOW}nano .env${NC}"
echo ""
echo -e "  2. Start all dev services:"
echo -e "     ${YELLOW}./scripts/dev.sh${NC}"
echo ""
echo -e "  3. Or use Docker Compose:"
echo -e "     ${YELLOW}docker compose -f docker-compose.dev.yml up${NC}"
echo ""
echo -e "  Service URLs (local dev):"
echo -e "     Backend API : ${CYAN}http://localhost:8000${NC}"
echo -e "     API Docs    : ${CYAN}http://localhost:8000/docs${NC}"
echo -e "     Frontend    : ${CYAN}http://localhost:5173${NC}"
echo -e "     Ollama      : ${CYAN}http://localhost:11434${NC}"
echo ""

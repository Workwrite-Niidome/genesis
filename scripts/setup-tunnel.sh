#!/bin/bash
# =============================================================================
# GENESIS v3 — Cloudflare Tunnel Setup Script
# =============================================================================
# This script sets up a Cloudflare Tunnel to expose the backend API server
# (running on localhost:8000) at api.genesis-pj.net.
#
# Prerequisites:
#   - A Cloudflare account with genesis-pj.net added as a zone
#   - Docker and Docker Compose running the backend services
#
# Usage:
#   chmod +x scripts/setup-tunnel.sh
#   ./scripts/setup-tunnel.sh
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

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}   GENESIS v3 — Cloudflare Tunnel Setup${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Install cloudflared
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 1/5: Install cloudflared ---${NC}"

if command -v cloudflared &>/dev/null; then
    INSTALLED_VERSION=$(cloudflared --version 2>&1 | head -n1)
    success "cloudflared is already installed: $INSTALLED_VERSION"
else
    info "Installing cloudflared..."

    if [[ "$(uname)" == "Linux" ]]; then
        # Detect architecture
        ARCH=$(uname -m)
        case "$ARCH" in
            x86_64)  CF_ARCH="amd64" ;;
            aarch64) CF_ARCH="arm64" ;;
            armv7l)  CF_ARCH="arm"   ;;
            *)       error "Unsupported architecture: $ARCH"; exit 1 ;;
        esac

        # Download and install
        curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}.deb" \
            -o /tmp/cloudflared.deb
        sudo dpkg -i /tmp/cloudflared.deb
        rm /tmp/cloudflared.deb
    elif [[ "$(uname)" == "Darwin" ]]; then
        brew install cloudflare/cloudflare/cloudflared
    else
        error "Unsupported OS. Please install cloudflared manually:"
        echo "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        exit 1
    fi

    success "cloudflared installed successfully"
fi

echo ""

# ---------------------------------------------------------------------------
# Step 2: Authenticate with Cloudflare
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 2/5: Authenticate with Cloudflare ---${NC}"

if [ -f "$HOME/.cloudflared/cert.pem" ]; then
    success "Already authenticated (cert.pem exists)"
else
    info "Opening browser for Cloudflare authentication..."
    info "Select the zone: genesis-pj.net"
    echo ""
    cloudflared tunnel login
    success "Authentication complete"
fi

echo ""

# ---------------------------------------------------------------------------
# Step 3: Create the tunnel
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 3/5: Create tunnel ---${NC}"

TUNNEL_NAME="genesis-backend"

# Check if tunnel already exists
if cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
    TUNNEL_ID=$(cloudflared tunnel list 2>/dev/null | grep "$TUNNEL_NAME" | awk '{print $1}')
    success "Tunnel '$TUNNEL_NAME' already exists (ID: $TUNNEL_ID)"
else
    info "Creating tunnel '$TUNNEL_NAME'..."
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_ID=$(cloudflared tunnel list 2>/dev/null | grep "$TUNNEL_NAME" | awk '{print $1}')
    success "Tunnel created (ID: $TUNNEL_ID)"
fi

echo ""

# ---------------------------------------------------------------------------
# Step 4: Generate cloudflared config
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 4/5: Generate cloudflared config ---${NC}"

CREDENTIALS_FILE="$HOME/.cloudflared/${TUNNEL_ID}.json"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    error "Credentials file not found at $CREDENTIALS_FILE"
    error "This should have been created when the tunnel was created."
    exit 1
fi

CONFIG_FILE="$HOME/.cloudflared/config.yml"

info "Writing config to $CONFIG_FILE"

cat > "$CONFIG_FILE" << EOF
tunnel: ${TUNNEL_ID}
credentials-file: ${CREDENTIALS_FILE}

ingress:
  # API backend (REST + WebSocket)
  - hostname: api.genesis-pj.net
    service: http://localhost:8000
    originRequest:
      noTLSVerify: false
      connectTimeout: 30s
      keepAliveTimeout: 90s

  # WebSocket dedicated subdomain (optional, same backend)
  - hostname: ws.genesis-pj.net
    service: http://localhost:8000
    originRequest:
      noTLSVerify: false
      connectTimeout: 30s
      keepAliveTimeout: 90s

  # Catch-all: return 404 for unmatched hostnames
  - service: http_status:404
EOF

success "Config written to $CONFIG_FILE"

# Also copy a template to the project
cp "$CONFIG_FILE" "$PROJECT_ROOT/cloudflared-config.yml.example"
info "Template copied to $PROJECT_ROOT/cloudflared-config.yml.example"

echo ""

# ---------------------------------------------------------------------------
# Step 5: Set up DNS routes
# ---------------------------------------------------------------------------
echo -e "${CYAN}--- Step 5/5: Set up DNS routes ---${NC}"

info "Creating DNS route: api.genesis-pj.net -> tunnel"
cloudflared tunnel route dns "$TUNNEL_NAME" api.genesis-pj.net || warn "DNS route for api.genesis-pj.net may already exist"

info "Creating DNS route: ws.genesis-pj.net -> tunnel"
cloudflared tunnel route dns "$TUNNEL_NAME" ws.genesis-pj.net || warn "DNS route for ws.genesis-pj.net may already exist"

success "DNS routes configured"

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Cloudflare Tunnel Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  Tunnel Name : $TUNNEL_NAME"
echo "  Tunnel ID   : $TUNNEL_ID"
echo "  Config      : $CONFIG_FILE"
echo "  Credentials : $CREDENTIALS_FILE"
echo ""
echo "  DNS Routes:"
echo "    api.genesis-pj.net -> localhost:8000"
echo "    ws.genesis-pj.net  -> localhost:8000"
echo ""
echo "  To start the tunnel manually:"
echo "    cloudflared tunnel run $TUNNEL_NAME"
echo ""
echo "  To install as a system service:"
echo "    sudo cloudflared service install"
echo "    sudo systemctl enable cloudflared"
echo "    sudo systemctl start cloudflared"
echo ""
echo "  To verify:"
echo "    curl https://api.genesis-pj.net/docs"
echo ""

#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$HOME/workspace"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=5001

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[0;33m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
fail() { echo -e "  ${RED}✗${RESET}  $*"; exit 1; }
step() { echo -e "\n${BOLD}==> $*${RESET}"; }

echo -e "\n${BOLD}Command Center — one-command setup${RESET}"
echo "────────────────────────────────────────────────────────"

# ── 1. Python 3.10+ ────────────────────────────────────────────────────────────
step "Checking Python version..."
if ! command -v python3 &>/dev/null; then
  fail "python3 not found. Install Python 3.10 or later and re-run."
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJ=$(echo "$PY_VER" | cut -d. -f1)
PY_MIN=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJ" -lt 3 ] || { [ "$PY_MAJ" -eq 3 ] && [ "$PY_MIN" -lt 10 ]; }; then
  fail "Python $PY_VER found but 3.10+ is required. Upgrade Python and re-run."
fi
ok "Python $PY_VER"

# ── 2. Ollama (soft check) ─────────────────────────────────────────────────────
step "Checking Ollama..."
if command -v ollama &>/dev/null; then
  ok "Ollama found at $(command -v ollama)"
else
  warn "Ollama not found. Local AI features will not work until you install it."
  warn "Install guide: https://ollama.com/download"
  warn "You can still use Command Center with an Anthropic API key."
fi

# ── 3. Python dependencies ─────────────────────────────────────────────────────
step "Installing Python packages..."
pip3 install flask flask-cors requests schedule python-dotenv --break-system-packages -q
ok "flask, flask-cors, requests, schedule, python-dotenv installed"

# ── 4. ~/workspace/ ────────────────────────────────────────────────────────────
step "Scaffolding ~/workspace/..."
mkdir -p "$WORKSPACE"
ok "Directory $WORKSPACE ready"

# ── 5. data.json ───────────────────────────────────────────────────────────────
if [ ! -f "$WORKSPACE/data.json" ]; then
  if [ -f "$SCRIPT_DIR/config.example.json" ]; then
    cp "$SCRIPT_DIR/config.example.json" "$WORKSPACE/data.json"
    ok "Copied config.example.json → $WORKSPACE/data.json"
  else
    fail "config.example.json not found in repo root. Cannot seed data.json."
  fi
else
  ok "$WORKSPACE/data.json already present, skipping"
fi

# ── 6. .env ────────────────────────────────────────────────────────────────────
if [ ! -f "$WORKSPACE/.env" ]; then
  if [ -f "$SCRIPT_DIR/.env.template" ]; then
    cp "$SCRIPT_DIR/.env.template" "$WORKSPACE/.env"
    ok "Copied .env.template → $WORKSPACE/.env"
  else
    warn "No .env.template found — creating a minimal $WORKSPACE/.env"
    cat > "$WORKSPACE/.env" <<'ENVEOF'
CC_API_BASE=http://localhost:5001/api
AGENT_PROVIDER=ollama
OLLAMA_MODEL=qwen3:14b
ANTHROPIC_API_KEY=
ENVEOF
  fi
else
  ok "$WORKSPACE/.env already present, skipping"
fi

# ── 7. Kill existing process on port 5001 ─────────────────────────────────────
step "Freeing port $PORT..."
if fuser "$PORT/tcp" &>/dev/null 2>&1; then
  fuser -k "$PORT/tcp" 2>/dev/null || true
  sleep 1
  ok "Killed existing process on :$PORT"
else
  ok "Port $PORT is free"
fi

# ── 8. Start API server ────────────────────────────────────────────────────────
step "Starting API server..."
python3 "$SCRIPT_DIR/core/api/app.py" > "$WORKSPACE/api.log" 2>&1 &
API_PID=$!
echo "$API_PID" > "$WORKSPACE/api.pid"
ok "Server started (PID $API_PID) — log: $WORKSPACE/api.log"

# ── 9. Health check ───────────────────────────────────────────────────────────
step "Waiting for server to be ready..."
HTTP_CODE="000"
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/api/status" 2>/dev/null || :)
  [ "$HTTP_CODE" = "200" ] && break
done
if [ "$HTTP_CODE" = "200" ]; then
  ok "API is healthy (HTTP $HTTP_CODE)"
else
  warn "API returned HTTP $HTTP_CODE — check $WORKSPACE/api.log for errors"
  warn "Try: curl http://localhost:$PORT/api/status"
fi

# ── 10. Print URLs ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}────────────────────────────────────────────────────────${RESET}"
echo -e "${BOLD}  Command Center is running${RESET}"
echo "────────────────────────────────────────────────────────"
echo -e "  ${GREEN}Dashboard${RESET}   http://localhost:$PORT"
echo -e "  ${GREEN}Onboarding${RESET}  http://localhost:$PORT/onboarding"
echo -e "  ${GREEN}API status${RESET}  http://localhost:$PORT/api/status"
echo -e "  ${GREEN}API log${RESET}     $WORKSPACE/api.log"
echo "────────────────────────────────────────────────────────"
echo ""

# ── 11. Open onboarding in browser ────────────────────────────────────────────
xdg-open "http://localhost:$PORT/onboarding" 2>/dev/null \
  || open "http://localhost:$PORT/onboarding" 2>/dev/null \
  || echo -e "  Open ${GREEN}http://localhost:$PORT/onboarding${RESET} to complete setup."

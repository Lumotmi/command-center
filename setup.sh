#!/usr/bin/env bash
set -e

WORKSPACE="$HOME/workspace"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Setting up Command Center..."

# 1. Ensure ~/workspace exists
if [ ! -d "$WORKSPACE" ]; then
  mkdir -p "$WORKSPACE"
  echo "    Created $WORKSPACE"
else
  echo "    $WORKSPACE already exists"
fi

# 2. Seed data.json from config.example.json
if [ ! -f "$WORKSPACE/data.json" ]; then
  cp "$SCRIPT_DIR/config.example.json" "$WORKSPACE/data.json"
  echo "    Copied config.example.json → $WORKSPACE/data.json"
else
  echo "    $WORKSPACE/data.json already present, skipping"
fi

# 3. Seed .env from .env.template
if [ ! -f "$WORKSPACE/.env" ] && [ -f "$SCRIPT_DIR/.env.template" ]; then
  cp "$SCRIPT_DIR/.env.template" "$WORKSPACE/.env"
  echo "    Copied .env.template → $WORKSPACE/.env"
elif [ ! -f "$WORKSPACE/.env" ]; then
  echo "    WARNING: no .env.template found — create $WORKSPACE/.env manually"
fi

# 4. Install Python dependencies
echo "==> Installing Python packages..."
pip3 install requests schedule python-dotenv flask --break-system-packages

# 5. Start API server in background
echo "==> Starting API server..."
fuser -k 5001/tcp 2>/dev/null || true
sleep 1
python3 "$SCRIPT_DIR/core/api/app.py" > "$WORKSPACE/api.log" 2>&1 &
API_PID=$!
echo "    API server started (PID $API_PID, log: $WORKSPACE/api.log)"
echo $API_PID > "$WORKSPACE/api.pid"
sleep 3

# 6. Open onboarding wizard in browser
echo "==> Opening onboarding wizard..."
xdg-open http://localhost:5001/onboarding 2>/dev/null \
  || open http://localhost:5001/onboarding 2>/dev/null \
  || echo "    Open http://localhost:5001/onboarding in your browser to complete setup."

echo ""
echo "==> Setup complete!"
echo "    Onboarding: http://localhost:5001/onboarding"
echo "    Dashboard:  http://localhost:5001"
echo "    API log:    $WORKSPACE/api.log"

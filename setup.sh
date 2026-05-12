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

echo ""
echo "==> Done! Next steps:"
echo "    1. Edit $WORKSPACE/.env and add your API key (ANTHROPIC_API_KEY or OLLAMA_BASE_URL)"
echo "    2. Start the API server:   python3 $SCRIPT_DIR/core/api/app.py"
echo "    3. Open a dashboard:       $SCRIPT_DIR/dashboard/command-center.html"
echo "    4. Talk to the agent:      POST http://localhost:5000/agent"

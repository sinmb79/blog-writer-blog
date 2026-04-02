#!/usr/bin/env bash
set -euo pipefail

echo "============================================"
echo "  Blog Writer Blog — n8n Setup"
echo "  Collect, write, review, and publish."
echo "============================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKFLOW_DIR="$SCRIPT_DIR/n8n-workflows"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

check_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "  ❌ Missing required command: $1"
    echo "     Install: $2"
    exit 1
  fi
  echo "  ✅ $1 found"
}

wait_for_n8n() {
  for _ in $(seq 1 30); do
    if curl -s --max-time 2 http://localhost:5678/healthz >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

open_browser() {
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open http://localhost:5678 >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then
    open http://localhost:5678 >/dev/null 2>&1 &
  elif command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /c start "" http://localhost:5678 >/dev/null 2>&1
  else
    echo "  ℹ️ Open http://localhost:5678 manually in your browser."
  fi
}

import_workflow() {
  local file="$1"
  local name="$2"
  if [ -f "$file" ]; then
    if n8n import:workflow --input="$file" >/dev/null 2>&1; then
      echo "  ✅ $name"
    else
      echo "  ⚠️  $name (import failed)"
    fi
  else
    echo "  ⚠️  $name (missing file: $file)"
  fi
}

echo "[1/4] Checking prerequisites..."
check_command "node" "https://nodejs.org"
check_command "npm" "Bundled with Node.js"
check_command "python" "https://www.python.org/downloads/"
check_command "curl" "Install curl from your package manager"
echo ""

echo "[2/4] Installing n8n..."
if command -v n8n >/dev/null 2>&1; then
  echo "  ✅ n8n already installed ($(n8n --version))"
else
  echo "  📦 Installing n8n globally with npm..."
  npm install -g n8n
  echo "  ✅ n8n installation complete"
fi
echo ""

echo "[3/4] Starting n8n..."
if curl -s --max-time 2 http://localhost:5678/healthz >/dev/null 2>&1; then
  echo "  ✅ n8n already running on http://localhost:5678"
else
  echo "  🚀 Starting n8n in the background..."
  nohup n8n start >"$LOG_DIR/n8n.log" 2>&1 &
  N8N_PID=$!
  echo "  ⏳ Waiting for n8n to become healthy..."
  if wait_for_n8n; then
    echo "  ✅ n8n started (PID: $N8N_PID)"
  else
    echo "  ❌ n8n did not become healthy. Check $LOG_DIR/n8n.log"
    exit 1
  fi
fi
echo ""

echo "[4/4] Importing workflows..."
import_workflow "$WORKFLOW_DIR/blog-daily-pipeline.json" "Daily Pipeline"
import_workflow "$WORKFLOW_DIR/blog-write-queue.json" "Write Queue"
import_workflow "$WORKFLOW_DIR/blog-publish-queue.json" "Publish Queue"
import_workflow "$WORKFLOW_DIR/blog-weekly-report.json" "Weekly Report"
import_workflow "$WORKFLOW_DIR/blog-monthly-reminder.json" "Monthly Reminder"
echo ""

echo "============================================"
echo "  Blog Writer Blog is ready"
echo ""
echo "  n8n: http://localhost:5678"
echo "  Logs: $LOG_DIR/n8n.log"
echo ""
echo "  Open n8n and you should see 5 imported workflows."
echo "============================================"

open_browser

#!/usr/bin/env bash
# 一鍵啟動：開 CDP Chrome + Flask server。
# 按 Ctrl+C 會自動把兩個都關掉。
#
# 用法：
#   bash scripts/start.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR="${CHROME_CDP_PROFILE:-/tmp/chrome-cdp-profile}"
CDP_PORT="${CHROME_CDP_PORT:-9222}"
SERVER_PORT="${SERVER_PORT:-8080}"

CHROME_PID=""
SERVER_PID=""
LAUNCHED_CHROME=0

cleanup() {
  trap - EXIT INT TERM
  echo ""
  echo "停止中..."
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  if [ "$LAUNCHED_CHROME" = "1" ] && [ -n "$CHROME_PID" ] && kill -0 "$CHROME_PID" 2>/dev/null; then
    kill "$CHROME_PID" 2>/dev/null || true
  fi
  echo "已停止。"
}
trap cleanup EXIT INT TERM

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# ── Step 1: Chrome CDP ──────────────────────────────────────────────
if port_in_use "$CDP_PORT"; then
  echo "✓ Chrome CDP 已在 port $CDP_PORT — 重用現有的"
else
  if [ ! -x "$CHROME" ]; then
    echo "✗ 找不到 Chrome：$CHROME"
    echo "  請先安裝：https://www.google.com/chrome/"
    exit 1
  fi
  mkdir -p "$PROFILE_DIR"
  echo "→ 啟動 Chrome (CDP port=$CDP_PORT)..."
  "$CHROME" \
    --remote-debugging-port="$CDP_PORT" \
    --user-data-dir="$PROFILE_DIR" \
    --no-first-run \
    --no-default-browser-check \
    https://www.tcool.cc/ >/dev/null 2>&1 &
  CHROME_PID=$!
  LAUNCHED_CHROME=1

  for _ in $(seq 1 20); do
    port_in_use "$CDP_PORT" && break
    sleep 0.5
  done
  if ! port_in_use "$CDP_PORT"; then
    echo "✗ Chrome 啟動失敗（10 秒內沒監聽 port $CDP_PORT）"
    exit 1
  fi
  echo "✓ Chrome 就緒"
fi

# ── Step 2: Flask server ────────────────────────────────────────────
if port_in_use "$SERVER_PORT"; then
  echo "✗ Port $SERVER_PORT 已被佔用 — 先 pkill -f 'python3 server.py' 再試"
  exit 1
fi

echo ""
echo "→ 啟動 server..."
echo "──────────────────────────────────────────"
echo "  打開瀏覽器：http://localhost:$SERVER_PORT"
echo "  結束：在這個視窗按 Ctrl+C"
echo "──────────────────────────────────────────"
echo ""

python3 server.py &
SERVER_PID=$!

# Wait for the server to be listening, then auto-open the browser
for _ in $(seq 1 20); do
  port_in_use "$SERVER_PORT" && break
  sleep 0.5
done
if port_in_use "$SERVER_PORT" && command -v open >/dev/null 2>&1; then
  open "http://localhost:$SERVER_PORT"
fi

wait "$SERVER_PID"

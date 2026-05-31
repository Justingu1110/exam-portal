#!/usr/bin/env bash
# 啟動一個獨立 profile 的 Chrome，開遠端除錯 port 9222，
# 給 server.py 透過 CDP 連進去抓 tcool.cc 的 PDF（繞 Cloudflare）。
#
# 用法：
#   bash scripts/launch-chrome-cdp.sh
#
# 跟你日常用的 Chrome 互不干擾（用 /tmp/chrome-cdp-profile 當 profile 路徑）。
# 視窗開著就好，server.py 啟動後就能合併 PDF。

set -e

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR="${CHROME_CDP_PROFILE:-/tmp/chrome-cdp-profile}"
PORT="${CHROME_CDP_PORT:-9222}"

if [ ! -x "$CHROME" ]; then
  echo "找不到 Chrome：$CHROME"
  echo "請先安裝 Google Chrome：https://www.google.com/chrome/"
  exit 1
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT 已有東西在聽 — 假設 Chrome CDP 已開好，直接退出。"
  exit 0
fi

mkdir -p "$PROFILE_DIR"
echo "啟動 Chrome（CDP port=$PORT, profile=$PROFILE_DIR）…"
exec "$CHROME" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  https://www.tcool.cc/

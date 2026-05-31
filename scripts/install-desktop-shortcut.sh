#!/usr/bin/env bash
# 在你的 macOS 桌面建立一個 exam-portal.command 捷徑。
# 雙擊就會啟動 Chrome + server 並自動開啟瀏覽器。
#
# 用法（在 exam-portal 專案資料夾裡）：
#   bash scripts/install-desktop-shortcut.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DESKTOP="$HOME/Desktop"
if [ ! -d "$DESKTOP" ]; then
  # macOS 中文系統可能叫「桌面」
  DESKTOP="$HOME/桌面"
fi
if [ ! -d "$DESKTOP" ]; then
  echo "✗ 找不到桌面資料夾（$HOME/Desktop 或 $HOME/桌面）"
  exit 1
fi

TARGET="$DESKTOP/exam-portal.command"

cat > "$TARGET" <<EOF
#!/usr/bin/env bash
# 雙擊啟動 exam-portal — 結束時在這個視窗按 Control + C

cd "$ROOT" || {
  echo "找不到 $ROOT — 專案資料夾被移動或刪除了？"
  read -n 1 -s -r -p "按任意鍵關閉"
  exit 1
}

bash scripts/start.sh

echo ""
echo "──────────────────────────────────────────"
read -n 1 -s -r -p "已停止。按任意鍵關閉視窗。"
EOF

chmod +x "$TARGET"
echo "✓ 已建立桌面捷徑：$TARGET"
echo "  雙擊即可啟動。"
echo ""
echo "  第一次雙擊若被 macOS 擋（「無法開啟，因為來自不明開發者」）："
echo "  → 右鍵點檔案 → 開啟 → 開啟。之後雙擊就 OK。"

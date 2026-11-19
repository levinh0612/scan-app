#!/usr/bin/env bash
# make-mac-app.sh — tạo 2 icon macOS: "ScanApp" (người dùng: mở app) và "ScanApp Cài đặt" (Terminal: QR + link + log).
# Dùng:  ./make-mac-app.sh            → tạo ~/Desktop/ScanApp.app
#        ./make-mac-app.sh /Applications   → tạo ở thư mục khác
set -euo pipefail
cd "$(dirname "$0")"
[ "$(uname -s)" = "Darwin" ] || { echo "Script này chỉ dành cho macOS."; exit 1; }
ROOT="$PWD"
DEST="${1:-$HOME/Desktop}"
PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"
[ -f assets/scanapp.png ] || "$PY" assets/make_icon.py

# .icns từ PNG 1024 (dùng chung cho cả 2 app)
ICNS="$(mktemp -d)/ScanApp.icns"; SET="$(mktemp -d)/scanapp.iconset"; mkdir -p "$SET"
for s in 16 32 128 256 512; do
  sips -z $s $s assets/scanapp.png --out "$SET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) assets/scanapp.png --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o "$ICNS"

# mk_app <tên> <id> — tạo bộ khung .app; chương trình chạy do hàm gọi tự ghi vào Contents/MacOS/ScanApp
mk_app() {
  local app="$DEST/$1.app"
  rm -rf "$app"; mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
  cp "$ICNS" "$app/Contents/Resources/ScanApp.icns"
  cat > "$app/Contents/Info.plist" <<P
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>$1</string>
  <key>CFBundleDisplayName</key><string>$1</string>
  <key>CFBundleIdentifier</key><string>vn.scanapp.$2</string>
  <key>CFBundleExecutable</key><string>ScanApp</string>
  <key>CFBundleIconFile</key><string>ScanApp</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSArchitecturePriority</key><array><string>arm64</string><string>x86_64</string></array>
</dict></plist>
P
  echo "$app"
}

# --- 1. ScanApp: cho người dùng. Chưa chạy thì bật server (qua Terminal, thu nhỏ), rồi mở trình duyệt. ---
# Lưu ý macOS: app mở từ Finder KHÔNG được đọc ~/Documents (quyền riêng tư) → launcher chỉ gọi curl/osascript, việc đụng thư mục dự án giao cho Terminal.
APP="$(mk_app ScanApp main)"
cat > "$APP/Contents/MacOS/ScanApp" <<L
#!/bin/bash
alive() {
  for p in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010; do
    curl -sf -m 2 "http://localhost:\$p/api/health" >/dev/null 2>&1 && { URL="http://localhost:\$p/"; return 0; }
    curl -skf -m 2 "https://localhost:\$p/api/health" >/dev/null 2>&1 && { URL="https://localhost:\$p/"; return 0; }
  done; return 1
}
if ! alive; then
  osascript -e 'display notification "Đang khởi động, chờ khoảng 10–30 giây rồi trình duyệt sẽ tự mở…" with title "ScanApp"' >/dev/null 2>&1
  osascript <<O >/dev/null 2>&1
tell application "Terminal"
  set w to do script "cd '$ROOT' && ./run.sh --auto; exit"
  try
    set miniaturized of (first window whose selected tab is w) to true
  end try
end tell
O
  for _ in \$(seq 1 90); do sleep 2; alive && break; done
fi
if alive; then open "\$URL"; else osascript -e 'display alert "ScanApp chưa chạy được" message "Mở ScanApp Cài đặt để xem lỗi."'; fi
L
chmod +x "$APP/Contents/MacOS/ScanApp"; touch "$APP"

# --- 2. ScanApp Cài đặt: cho người cài/sửa lỗi. Cửa sổ Terminal hiện QR + link + log. ---
APP2="$(mk_app "ScanApp Cài đặt" setup)"
cat > "$APP2/Contents/MacOS/ScanApp" <<L
#!/bin/bash
ROOT="$ROOT"
export PATH="/opt/homebrew/bin:/usr/local/bin:\$PATH"
osascript <<O
tell application "Terminal"
  activate
  do script "cd '\$ROOT' && ./run.sh"
end tell
O
L
chmod +x "$APP2/Contents/MacOS/ScanApp"; touch "$APP2"

echo "Đã tạo trong $DEST:"
echo "  - ScanApp            : bấm đúp = mở app trên trình duyệt (tự bật server ngầm nếu chưa chạy). QR cho điện thoại ở đầu trang."
echo "  - ScanApp Cài đặt    : cửa sổ Terminal hiện QR + link + log (cho người cài/sửa lỗi)."
echo "Kéo ScanApp vào Dock nếu muốn. Lần đầu nếu macOS hỏi quyền điều khiển Terminal → chọn OK."

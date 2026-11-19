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
</dict></plist>
P
  echo "$app"
}

# --- 1. ScanApp: cho người dùng. Chạy ngầm nếu chưa chạy, rồi mở trình duyệt. Không hiện cửa sổ lệnh. ---
APP="$(mk_app ScanApp main)"
cat > "$APP/Contents/MacOS/ScanApp" <<L
#!/bin/bash
ROOT="$ROOT"
cd "\$ROOT" || { osascript -e 'display alert "Không tìm thấy thư mục ScanApp" message "Chạy lại ./make-mac-app.sh"'; exit 1; }
alive() { P=8000; [ -f .run/port ] && P="\$(cat .run/port)"; curl -sf "http://localhost:\$P/api/health" >/dev/null 2>&1 && { URL="http://localhost:\$P/"; return 0; }; curl -skf "https://localhost:\$P/api/health" >/dev/null 2>&1 && { URL="https://localhost:\$P/"; return 0; }; return 1; }
if ! alive; then
  mkdir -p logs; nohup ./run.sh --auto >> logs/launcher.log 2>&1 &
  for _ in \$(seq 1 90); do sleep 2; alive && break; done
fi
if alive; then open "\$URL"; else osascript -e 'display alert "ScanApp chưa chạy được" message "Mở ScanApp Cài đặt để xem lỗi (hoặc logs/launcher.log)."'; fi
L
chmod +x "$APP/Contents/MacOS/ScanApp"; touch "$APP"

# --- 2. ScanApp Cài đặt: cho người cài/sửa lỗi. Cửa sổ Terminal hiện QR + link + log. ---
APP2="$(mk_app "ScanApp Cài đặt" setup)"
cat > "$APP2/Contents/MacOS/ScanApp" <<L
#!/bin/bash
ROOT="$ROOT"
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
